# type: ignore
"""Add restart-bookkeeping columns to batch jobs

Batch jobs now run a tigerflow ``local`` pipeline in the tigerflow-ml container
as a single Slurm allocation, and Blackfish resubmits the allocation until the
input directory is fully processed. These columns track the restart loop:

- restarts / max_restarts: absolute resubmit count and its ceiling.
- stalled_restarts / max_stalled_restarts: consecutive no-progress resubmits and
  the ceiling (guards against a permanently-failing file).
- processed_highwater: highest observed ``processed`` count, used to detect
  forward progress across restarts.

Defaults applied for rows created before this migration.

Revision ID: c3d4e5f6a7b8
Revises: 1cca2a04c7bb
Create Date: 2026-07-01

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
revision = "c3d4e5f6a7b8"
down_revision = "1cca2a04c7bb"
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
        batch_op.add_column(
            sa.Column("restarts", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("max_restarts", sa.Integer(), nullable=False, server_default="20")
        )
        batch_op.add_column(
            sa.Column(
                "stalled_restarts", sa.Integer(), nullable=False, server_default="0"
            )
        )
        batch_op.add_column(
            sa.Column(
                "max_stalled_restarts",
                sa.Integer(),
                nullable=False,
                server_default="1",
            )
        )
        batch_op.add_column(
            sa.Column(
                "processed_highwater",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )


def schema_downgrades() -> None:
    """schema downgrade migrations go here."""

    with op.batch_alter_table("jobs", schema=None) as batch_op:
        batch_op.drop_column("processed_highwater")
        batch_op.drop_column("max_stalled_restarts")
        batch_op.drop_column("stalled_restarts")
        batch_op.drop_column("max_restarts")
        batch_op.drop_column("restarts")


def data_upgrades() -> None:
    """Add any optional data upgrade migrations here!"""


def data_downgrades() -> None:
    """Add any optional data downgrade migrations here!"""
