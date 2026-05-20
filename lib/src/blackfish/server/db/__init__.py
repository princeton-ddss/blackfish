"""SQLite PRAGMA setup for every SQLAlchemy engine in the process.

Importing this module registers a global ``connect`` event listener on
SQLAlchemy's base :class:`~sqlalchemy.engine.Engine` class. On every new
SQLite DBAPI connection (sync ``sqlite3`` or async ``aiosqlite``) the
listener applies:

- ``journal_mode=WAL``    — readers and writers don't block each other
- ``busy_timeout=5000``   — wait up to 5s on lock contention instead of
                            raising ``OperationalError: database is locked``
- ``foreign_keys=ON``     — enforce FK constraints (off by SQLite default)
- ``synchronous=NORMAL``  — faster writes in WAL mode with adequate durability
                            for a workstation use case

The listener must be registered before any engine opens a connection, so
each process entry point imports this module for its side effect.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine


@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
    # The dbapi connection's class lives in `sqlite3`, `aiosqlite.core`, or
    # — when SQLAlchemy wraps an async driver — `sqlalchemy.dialects.sqlite.*`.
    if "sqlite" not in type(dbapi_connection).__module__:
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()
