# type: ignore
"""normalize model_dir to repo root

The model *update* path historically persisted the raw Hugging Face snapshot
path (``.../models--<ns>--<model>/snapshots/<revision>``) in ``model.model_dir``,
while the *download* path stored the repo root (``.../models--<ns>--<model>``).
Services render their bind mounts from ``model_dir``, so any updated model
launched with a mount one directory level too deep and the inference server
could not find the model.

The code paths are now fixed to always store the repo root, but existing rows do
not self-heal. This data migration rewrites any ``model_dir`` that still points
inside a ``snapshots`` directory back to its repo root.

Revision ID: 565bd6201d2a
Revises: c3d4e5f6a7b8
Create Date: 2026-07-23 15:46:07.550963+00:00

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
revision = "565bd6201d2a"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        with op.get_context().autocommit_block():
            schema_upgrades()
            data_upgrades()


def downgrade() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        with op.get_context().autocommit_block():
            data_downgrades()
            schema_downgrades()


def schema_upgrades() -> None:
    """schema upgrade migrations go here."""
    pass


def schema_downgrades() -> None:
    """schema downgrade migrations go here."""
    pass


def data_upgrades() -> None:
    """Rewrite any snapshot-path ``model_dir`` values to their repo root.

    A corrupt value looks like ``.../models--<ns>--<model>/snapshots/<revision>``;
    the repo root is everything before ``/snapshots``. Correct rows (already at
    the repo root) contain no ``/snapshots`` segment and are left untouched.
    """
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, model_dir FROM model WHERE model_dir LIKE :pattern"),
        {"pattern": "%/snapshots%"},
    ).fetchall()

    for row_id, model_dir in rows:
        repo_root = model_dir.partition("/snapshots")[0]
        if repo_root and repo_root != model_dir:
            bind.execute(
                sa.text("UPDATE model SET model_dir = :model_dir WHERE id = :id"),
                {"model_dir": repo_root, "id": row_id},
            )


def data_downgrades() -> None:
    """No-op: the normalized ``model_dir`` is the correct value.

    Reversing would mean re-introducing the snapshot-path bug, and the original
    (correct) download rows never had a snapshot suffix to restore, so there is
    nothing meaningful to downgrade.
    """
