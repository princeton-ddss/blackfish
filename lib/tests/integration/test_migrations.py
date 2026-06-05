"""Verify migrations replay cleanly and that the schema they build
matches the models' current view of the world.

If `test_models_match_head_schema` fails with a non-empty diff, the
two likely causes are:
1. A model field was added without a corresponding migration.
2. A new model module was added without a corresponding import below.
"""

from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine
from sqlalchemy.types import TypeDecorator, TypeEngine

# Importing these registers each model's Table in orm_registry.metadata.
import blackfish.server.models.download  # noqa: F401
import blackfish.server.models.metadata  # noqa: F401
import blackfish.server.models.model  # noqa: F401
import blackfish.server.models.profile  # noqa: F401
import blackfish.server.models.tiers  # noqa: F401
from advanced_alchemy.base import orm_registry
from blackfish.server.bootstrap import ensure_db


def _compare_type(
    ctx: object,  # noqa: ARG001
    inspected_column: object,  # noqa: ARG001
    metadata_column: object,  # noqa: ARG001
    inspected_type: TypeEngine,  # noqa: ARG001
    metadata_type: TypeEngine,
) -> bool | None:
    """Treat TypeDecorator columns as equivalent on round-trip.

    advanced-alchemy ships custom types like GUID and DateTimeUTC that
    are TypeDecorator subclasses. SQLite stores them under their impl
    type's affinity, so reflection reads them back as NUMERIC, DATETIME,
    etc. — never as the decorator. Defer to the model's declared type
    in that case.
    """
    if isinstance(metadata_type, TypeDecorator):
        return False
    return None


def test_migrations_replay_to_head(tmp_path: Path) -> None:
    ensure_db(tmp_path)


def test_models_match_head_schema(tmp_path: Path) -> None:
    ensure_db(tmp_path)
    engine = create_engine(f"sqlite:///{tmp_path / 'app.sqlite'}")
    with engine.connect() as conn:
        ctx = MigrationContext.configure(
            conn,
            opts={
                "compare_type": _compare_type,
                "version_table": "ddl_version",
            },
        )
        diff = compare_metadata(ctx, orm_registry.metadata)
    assert diff == [], f"Schema drift between models and migrations: {diff}"
