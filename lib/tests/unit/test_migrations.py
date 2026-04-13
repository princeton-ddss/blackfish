"""Tests for database migrations.

These tests exercise individual migration functions against a temp SQLite
database using alembic's programmatic API. They don't boot the full alembic
environment (env.py), so they're fast and self-contained.
"""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
from typing import Any, Iterator

import pytest
import sqlalchemy as sa
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[2] / "src/blackfish/server/db/migrations/versions"
)


def load_migration(filename: str) -> Any:
    """Load a migration module directly from its file path."""
    path = MIGRATIONS_DIR / filename
    spec = importlib.util.spec_from_file_location(f"_test_mig_{filename}", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def engine() -> Iterator[Engine]:
    """Temp SQLite engine, cleaned up after the test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        yield create_engine(f"sqlite:///{db_path}")
    finally:
        Path(db_path).unlink(missing_ok=True)


def _create_v05_jobs_table(conn: sa.Connection) -> None:
    """Create the v0.5 jobs table shape from 4dfd6eed368a_create_batch_jobs."""
    conn.execute(
        text(
            """
            CREATE TABLE jobs (
                id BLOB NOT NULL,
                name VARCHAR NOT NULL,
                pipeline VARCHAR NOT NULL,
                repo_id VARCHAR NOT NULL,
                profile VARCHAR NOT NULL,
                user VARCHAR,
                host VARCHAR,
                home_dir VARCHAR,
                cache_dir VARCHAR,
                job_id VARCHAR,
                status VARCHAR,
                ntotal VARCHAR,
                nsuccess VARCHAR,
                nfail VARCHAR,
                scheduler VARCHAR,
                provider VARCHAR,
                mount VARCHAR,
                sa_orm_sentinel INTEGER,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                CONSTRAINT pk_service PRIMARY KEY (id)
            )
            """
        )
    )


def _get_columns(conn: sa.Connection, table: str) -> dict[str, dict[str, Any]]:
    """Return column metadata from SQLite's PRAGMA table_info."""
    rows = conn.execute(text(f"PRAGMA table_info({table})")).mappings().all()
    return {r["name"]: dict(r) for r in rows}


class TestTigerFlowBatchJobsMigration:
    """Tests for 2026-02-10_tigerflow_batch_jobs (revision a1b2c3d4e5f6).

    This migration replaces the v0.5 speech_recognition `jobs` shape with a
    fresh v1.0 TigerFlow batch job shape. The two schemas represent different
    entities, so it drops and recreates the table — any v0.5 rows are
    discarded by design (they'd be zombies under the new schema: NULL in
    fields v1.0 treats as required).
    """

    FILENAME = "2026-02-10_tigerflow_batch_jobs_a1b2c3d4e5f6.py"

    def test_upgrade_replaces_v05_table_and_drops_rows(self, engine: Engine) -> None:
        """Upgrade drops v0.5 rows and recreates the table with v1.0 shape."""
        with engine.connect() as conn:
            _create_v05_jobs_table(conn)
            # Seed a v0.5-shaped row that would become a zombie under the
            # old rename-in-place approach.
            conn.execute(
                text(
                    """
                    INSERT INTO jobs (
                        id, name, pipeline, repo_id, profile,
                        created_at, updated_at
                    ) VALUES (
                        X'00000000000000000000000000000001',
                        'old-job',
                        'speech_recognition',
                        'openai/whisper-tiny',
                        'default',
                        '2024-01-01 00:00:00',
                        '2024-01-01 00:00:00'
                    )
                    """
                )
            )
            conn.commit()
            assert conn.execute(text("SELECT COUNT(*) FROM jobs")).scalar() == 1

            migration = load_migration(self.FILENAME)
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                migration.schema_upgrades()
            conn.commit()

            # The v0.5 row is gone (drop + recreate discards it by design).
            assert conn.execute(text("SELECT COUNT(*) FROM jobs")).scalar() == 0

            cols = _get_columns(conn, "jobs")

            # v1.0 required columns present and NOT NULL.
            required = [
                "id",
                "name",
                "task",
                "repo_id",
                "input_dir",
                "output_dir",
                "profile",
                "max_workers",
                "created_at",
                "updated_at",
            ]
            for col in required:
                assert col in cols, f"missing required column {col!r}"
                assert cols[col]["notnull"] == 1, (
                    f"{col!r} should be NOT NULL, got {cols[col]}"
                )

            # v1.0 optional columns present.
            optional = [
                "revision",
                "cache_dir",
                "params",
                "resources",
                "user",
                "host",
                "home_dir",
                "status",
                "pid",
                "staged",
                "finished",
                "errored",
                "tigerflow_version",
                "tigerflow_ml_version",
                "sa_orm_sentinel",
            ]
            for col in optional:
                assert col in cols, f"missing optional column {col!r}"

            # Progress counters are Integer now, not String. Fixes a latent
            # shape mismatch where the ORM expects int but v0.5 created
            # these columns as VARCHAR.
            for int_col in ("staged", "finished", "errored"):
                assert "INT" in cols[int_col]["type"].upper(), (
                    f"{int_col!r} should be Integer, got {cols[int_col]['type']!r}"
                )

            # v0.5-only columns are gone.
            dropped = [
                "pipeline",
                "job_id",
                "scheduler",
                "provider",
                "mount",
                "ntotal",
                "nsuccess",
                "nfail",
            ]
            for col in dropped:
                assert col not in cols, f"{col!r} should have been dropped"

    def test_upgrade_on_empty_v05_table_succeeds(self, engine: Engine) -> None:
        """Upgrade should succeed on a fresh install (empty jobs table)."""
        with engine.connect() as conn:
            _create_v05_jobs_table(conn)
            conn.commit()

            migration = load_migration(self.FILENAME)
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                migration.schema_upgrades()
            conn.commit()

            assert conn.execute(text("SELECT COUNT(*) FROM jobs")).scalar() == 0
            cols = _get_columns(conn, "jobs")
            assert "task" in cols
            assert "pipeline" not in cols

    def test_downgrade_restores_v05_shape(self, engine: Engine) -> None:
        """Downgrade drops the v1.0 table and recreates the v0.5 shape."""
        with engine.connect() as conn:
            _create_v05_jobs_table(conn)
            conn.commit()

            migration = load_migration(self.FILENAME)

            # Upgrade first so we're in the v1.0 state.
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                migration.schema_upgrades()
            conn.commit()

            # Seed a v1.0-shaped row that should be discarded on downgrade.
            conn.execute(
                text(
                    """
                    INSERT INTO jobs (
                        id, name, task, repo_id, input_dir, output_dir,
                        profile, max_workers, created_at, updated_at
                    ) VALUES (
                        X'00000000000000000000000000000002',
                        'new-job', 'transcribe', 'openai/whisper-tiny',
                        '/in', '/out', 'default', 1,
                        '2026-02-10 00:00:00', '2026-02-10 00:00:00'
                    )
                    """
                )
            )
            conn.commit()
            assert conn.execute(text("SELECT COUNT(*) FROM jobs")).scalar() == 1

            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                migration.schema_downgrades()
            conn.commit()

            assert conn.execute(text("SELECT COUNT(*) FROM jobs")).scalar() == 0
            cols = _get_columns(conn, "jobs")

            # v0.5 required columns are back and NOT NULL.
            for col in (
                "id",
                "name",
                "pipeline",
                "repo_id",
                "profile",
                "created_at",
                "updated_at",
            ):
                assert col in cols, f"missing v0.5 column {col!r}"
                assert cols[col]["notnull"] == 1

            # v0.5 nullable columns are back.
            for col in (
                "job_id",
                "scheduler",
                "provider",
                "mount",
                "ntotal",
                "nsuccess",
                "nfail",
            ):
                assert col in cols, f"missing v0.5 column {col!r}"

            # v1.0-only columns are gone.
            for col in (
                "task",
                "input_dir",
                "output_dir",
                "max_workers",
                "staged",
                "finished",
                "errored",
                "tigerflow_version",
                "tigerflow_ml_version",
            ):
                assert col not in cols, f"v1.0 column {col!r} should have been dropped"

    def test_upgrade_then_downgrade_is_reversible(self, engine: Engine) -> None:
        """Round-trip upgrade + downgrade leaves the schema at the v0.5 shape."""
        with engine.connect() as conn:
            _create_v05_jobs_table(conn)
            conn.commit()

            before = _get_columns(conn, "jobs")

            migration = load_migration(self.FILENAME)

            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                migration.schema_upgrades()
            conn.commit()

            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                migration.schema_downgrades()
            conn.commit()

            after = _get_columns(conn, "jobs")

            # Column sets match (schema round-trips cleanly).
            assert set(before) == set(after)
            # Nullability matches for every column.
            for name in before:
                assert before[name]["notnull"] == after[name]["notnull"], (
                    f"nullability mismatch on {name!r} after round-trip"
                )
