# type: ignore
"""dedup model rows and add uniq(repo, profile, revision)

Concurrent ``GET /api/models?refresh=true`` calls both read the DB, both
compute the same "missing" diff against the filesystem scan, and both INSERT
the same rows with different UUIDs. The window is wide enough to hit on Open
OnDemand (login-node FS latency stretches the HF Hub fetches to seconds).

Duplicate rows share the same on-disk ``model_dir``, so the cleanup can drop
all but one per ``(repo, profile, revision)`` without touching the filesystem.
Keep the oldest ``created_at`` because that's the row referenced by any
external URL that was captured before the race.

Once cleaned, install a UNIQUE constraint so future concurrent inserts get an
IntegrityError on the loser (handled in ``get_models``) instead of quietly
adding a duplicate.

Revision ID: d7e8f9a0b1c2
Revises: 565bd6201d2a
Create Date: 2026-08-13 00:00:00.000000+00:00

"""

from __future__ import annotations

import warnings

import sqlalchemy as sa
from alembic import op
from advanced_alchemy.types import (
    EncryptedString,
    EncryptedText,
    GUID,
    ORA_JSONB,
    DateTimeUTC,
)
from sqlalchemy import Text  # noqa: F401

__all__ = [
    "downgrade",
    "upgrade",
    "schema_upgrades",
    "schema_downgrades",
    "data_upgrades",
    "data_downgrades",
]

sa.GUID = GUID
sa.DateTimeUTC = DateTimeUTC
sa.ORA_JSONB = ORA_JSONB
sa.EncryptedString = EncryptedString
sa.EncryptedText = EncryptedText

# revision identifiers, used by Alembic.
revision = "d7e8f9a0b1c2"
down_revision = "565bd6201d2a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        with op.get_context().autocommit_block():
            data_upgrades()
            schema_upgrades()


def downgrade() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        with op.get_context().autocommit_block():
            schema_downgrades()
            data_downgrades()


def schema_upgrades() -> None:
    """Add UNIQUE(repo, profile, revision) on the model table."""
    with op.batch_alter_table("model") as batch_op:
        batch_op.create_unique_constraint(
            "uq_model_repo_profile_revision",
            ["repo", "profile", "revision"],
        )


def schema_downgrades() -> None:
    """Drop the uniqueness constraint added in the upgrade."""
    with op.batch_alter_table("model") as batch_op:
        batch_op.drop_constraint("uq_model_repo_profile_revision", type_="unique")


def data_upgrades() -> None:
    """Delete duplicate model rows, keeping the oldest per key.

    Duplicates share ``model_dir``, so this only removes DB rows — no files are
    touched. Ordering by ``created_at`` (with ``id`` as a stable tiebreaker for
    rows created in the same microsecond) keeps the row a caller with an
    already-issued ID would expect to find.
    """
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            DELETE FROM model
            WHERE id NOT IN (
                SELECT id FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY repo, profile, revision
                               ORDER BY created_at ASC, id ASC
                           ) AS rn
                    FROM model
                ) ranked
                WHERE rn = 1
            )
            """
        )
    )


def data_downgrades() -> None:
    """No-op: the deleted duplicates were spurious and cannot be reconstructed."""
