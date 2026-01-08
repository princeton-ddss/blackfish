# type: ignore
"""Create batch jobs

Revision ID: 4dfd6eed368a
Revises: 4e499534bca6
Create Date: 2025-06-17 14:03:41.136347+00:00

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
revision = "4dfd6eed368a"
down_revision = "4e499534bca6"
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

    op.create_table(
        "jobs",
        sa.Column("id", sa.GUID(length=16), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("pipeline", sa.String(), nullable=False),
        sa.Column("repo_id", sa.String(), nullable=False),
        sa.Column("profile", sa.String(), nullable=False),
        sa.Column("user", sa.String(), nullable=True),
        sa.Column("host", sa.String(), nullable=True),
        sa.Column("home_dir", sa.String(), nullable=True),
        sa.Column("cache_dir", sa.String(), nullable=True),
        sa.Column("job_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("ntotal", sa.String(), nullable=True),
        sa.Column("nsuccess", sa.String(), nullable=True),
        sa.Column("nfail", sa.String(), nullable=True),
        sa.Column("scheduler", sa.String(), nullable=True),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("mount", sa.String(), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTimeUTC(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTimeUTC(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_service")),
    )

    with op.batch_alter_table("service", schema=None) as batch_op:
        batch_op.alter_column(
            "grace_period", existing_type=sa.INTEGER(), nullable=False
        )


def schema_downgrades() -> None:
    """schema downgrade migrations go here."""
    op.drop_table("jobs")

    with op.batch_alter_table("service", schema=None) as batch_op:
        batch_op.alter_column("grace_period", existing_type=sa.INTEGER(), nullable=True)


def data_upgrades() -> None:
    """Add any optional data upgrade migrations here!"""


def data_downgrades() -> None:
    """Add any optional data downgrade migrations here!"""
