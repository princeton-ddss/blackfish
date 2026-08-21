# type: ignore
"""add image_ref columns

Records the container image ("repo:tag") a service or batch job launched with,
so restarts reuse it instead of picking up whatever the configured default
points at. NULL for rows created before this migration.

Revision ID: 87981ca2ed42
Revises: d7e8f9a0b1c2
Create Date: 2026-08-21 10:29:16.425386+00:00

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
revision = "87981ca2ed42"
down_revision = "d7e8f9a0b1c2"
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

    # Nullable with no server_default: existing rows legitimately have no
    # recorded image, and NULL means "resolve the configured default".
    with op.batch_alter_table("service", schema=None) as batch_op:
        batch_op.add_column(sa.Column("image_ref", sa.String(), nullable=True))

    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("image_ref", sa.String(), nullable=True))


def schema_downgrades() -> None:
    """schema downgrade migrations go here."""

    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.drop_column("image_ref")

    with op.batch_alter_table("service", schema=None) as batch_op:
        batch_op.drop_column("image_ref")


def data_upgrades() -> None:
    """Add any optional data upgrade migrations here!"""


def data_downgrades() -> None:
    """Add any optional data downgrade migrations here!"""
