# type: ignore
"""TigerFlow batch jobs schema

Replace batch job schema for TigerFlow-based execution.

- Add: task, revision, input_dir, output_dir, params, resources, pid, max_workers
- Rename: ntotal->staged, nsuccess->finished, nfail->errored
- Remove: pipeline, job_id, scheduler, provider, mount
- Keep: cache_dir (exists in both old and new schema)

Revision ID: a1b2c3d4e5f6
Revises: 27b628a63d4e
Create Date: 2026-02-10

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
revision = "a1b2c3d4e5f6"
down_revision = "27b628a63d4e"
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
        # Add new columns for TigerFlow
        batch_op.add_column(sa.Column("task", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("revision", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("input_dir", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("output_dir", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("params", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("resources", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("pid", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column("max_workers", sa.Integer(), nullable=False, server_default="1")
        )
        batch_op.add_column(sa.Column("tigerflow_version", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column("tigerflow_ml_version", sa.String(), nullable=True)
        )

        # Rename progress columns
        batch_op.alter_column("ntotal", new_column_name="staged")
        batch_op.alter_column("nsuccess", new_column_name="finished")
        batch_op.alter_column("nfail", new_column_name="errored")

        # Remove old columns
        batch_op.drop_column("pipeline")
        batch_op.drop_column("job_id")
        batch_op.drop_column("scheduler")
        batch_op.drop_column("provider")
        batch_op.drop_column("mount")


def schema_downgrades() -> None:
    """schema downgrade migrations go here."""

    with op.batch_alter_table("jobs", schema=None) as batch_op:
        # Restore old columns
        batch_op.add_column(sa.Column("pipeline", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("job_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("scheduler", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("provider", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("mount", sa.String(), nullable=True))

        # Rename progress columns back
        batch_op.alter_column("staged", new_column_name="ntotal")
        batch_op.alter_column("finished", new_column_name="nsuccess")
        batch_op.alter_column("errored", new_column_name="nfail")

        # Remove new columns
        batch_op.drop_column("task")
        batch_op.drop_column("revision")
        batch_op.drop_column("input_dir")
        batch_op.drop_column("output_dir")
        batch_op.drop_column("params")
        batch_op.drop_column("resources")
        batch_op.drop_column("pid")
        batch_op.drop_column("max_workers")
        batch_op.drop_column("tigerflow_version")
        batch_op.drop_column("tigerflow_ml_version")


def data_upgrades() -> None:
    """Add any optional data upgrade migrations here!"""


def data_downgrades() -> None:
    """Add any optional data downgrade migrations here!"""
