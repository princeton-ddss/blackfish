"""Smoke tests for the global SQLite PRAGMA listener.

Verifies that importing ``blackfish.server.db`` causes every new SQLite
connection — sync ``sqlite3`` or async ``aiosqlite`` — to come up with the
PRAGMAs the app relies on for concurrency and FK enforcement.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

import blackfish.server.db  # noqa: F401  # registers the listener

EXPECTED = {
    "journal_mode": "wal",
    "busy_timeout": 5000,
    "foreign_keys": 1,
    "synchronous": 1,  # NORMAL
}


def test_pragmas_set_on_sync_sqlite(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'app.sqlite'}")
    with engine.connect() as conn:
        for pragma, expected in EXPECTED.items():
            value = conn.execute(text(f"PRAGMA {pragma}")).scalar()
            assert value == expected, f"{pragma}: got {value!r}, want {expected!r}"


@pytest.mark.anyio
async def test_pragmas_set_on_aiosqlite(tmp_path: Path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'app.sqlite'}")
    async with engine.connect() as conn:
        for pragma, expected in EXPECTED.items():
            result = await conn.execute(text(f"PRAGMA {pragma}"))
            value = result.scalar()
            assert value == expected, f"{pragma}: got {value!r}, want {expected!r}"
    await engine.dispose()
