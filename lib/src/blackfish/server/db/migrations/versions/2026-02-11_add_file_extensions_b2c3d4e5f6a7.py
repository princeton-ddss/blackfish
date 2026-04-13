# type: ignore
"""Add file extension columns to batch jobs

Add input_ext and output_ext columns for TigerFlow pipeline configuration.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-11

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
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
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

    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("input_ext", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("output_ext", sa.String(), nullable=True))


def schema_downgrades() -> None:
    """schema downgrade migrations go here."""

    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.drop_column("input_ext")
        batch_op.drop_column("output_ext")


def data_upgrades() -> None:
    """Add any optional data upgrade migrations here!"""


def data_downgrades() -> None:
    """Add any optional data downgrade migrations here!"""
