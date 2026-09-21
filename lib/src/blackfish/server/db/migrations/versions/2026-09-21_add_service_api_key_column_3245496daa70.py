# type: ignore
"""add service api_key column

Records the upstream API key a service was launched with, so the proxy can
replay it when forwarding inference requests. NULL for services created before
this migration, and for services launched without a key.

Revision ID: 3245496daa70
Revises: 87981ca2ed42
Create Date: 2026-09-21 14:42:55.304937+00:00

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
revision = "3245496daa70"
down_revision = "87981ca2ed42"
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

    # Nullable with no server_default: a service legitimately has no key, and
    # NULL means "unauthenticated" rather than "not yet recorded".
    with op.batch_alter_table("service", schema=None) as batch_op:
        batch_op.add_column(sa.Column("api_key", sa.String(), nullable=True))


def schema_downgrades() -> None:
    """schema downgrade migrations go here."""

    with op.batch_alter_table("service", schema=None) as batch_op:
        batch_op.drop_column("api_key")


def data_upgrades() -> None:
    """Add any optional data upgrade migrations here!"""


def data_downgrades() -> None:
    """Add any optional data downgrade migrations here!"""
