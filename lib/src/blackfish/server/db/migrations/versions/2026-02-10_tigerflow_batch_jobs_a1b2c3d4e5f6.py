# type: ignore
"""TigerFlow batch jobs schema

Replaces the v0.5 `jobs` table (which tracked speech_recognition jobs) with a
fresh table for TigerFlow-based batch jobs. The two schemas represent
semantically different entities, so we drop and recreate rather than juggling
columns: v0.5 rows have no meaningful interpretation as v1.0 TigerFlow jobs,
and preserving row continuity would leave zombie records with NULL in fields
that v1.0 treats as required (task, input_dir, output_dir).

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

    # Drop the v0.5 table (speech_recognition job shape) and create a fresh
    # one with the v1.0 TigerFlow batch job shape. Any existing v0.5 rows are
    # discarded by design — they were tied to ephemeral services and have no
    # meaningful representation under the new schema. Required columns
    # (task, input_dir, output_dir, etc.) are declared NOT NULL to match the
    # BatchJob ORM in lib/src/blackfish/server/jobs/base.py.
    op.drop_table("jobs")
    op.create_table(
        "jobs",
        sa.Column("id", sa.GUID(length=16), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("task", sa.String(), nullable=False),
        sa.Column("repo_id", sa.String(), nullable=False),
        sa.Column("revision", sa.String(), nullable=True),
        sa.Column("input_dir", sa.String(), nullable=False),
        sa.Column("output_dir", sa.String(), nullable=False),
        sa.Column("cache_dir", sa.String(), nullable=True),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("resources", sa.JSON(), nullable=True),
        sa.Column("max_workers", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("profile", sa.String(), nullable=False),
        sa.Column("user", sa.String(), nullable=True),
        sa.Column("host", sa.String(), nullable=True),
        sa.Column("home_dir", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("pid", sa.String(), nullable=True),
        sa.Column("staged", sa.Integer(), nullable=True),
        sa.Column("finished", sa.Integer(), nullable=True),
        sa.Column("errored", sa.Integer(), nullable=True),
        sa.Column("tigerflow_version", sa.String(), nullable=True),
        sa.Column("tigerflow_ml_version", sa.String(), nullable=True),
        sa.Column("sa_orm_sentinel", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTimeUTC(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTimeUTC(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )


def schema_downgrades() -> None:
    """schema downgrade migrations go here."""

    # Symmetric with schema_upgrades: drop the v1.0 table and recreate the
    # v0.5 shape (as originally defined in 4dfd6eed368a_create_batch_jobs).
    # Any v1.0 rows are discarded by design.
    op.drop_table("jobs")
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


def data_upgrades() -> None:
    """Add any optional data upgrade migrations here!"""


def data_downgrades() -> None:
    """Add any optional data downgrade migrations here!"""
