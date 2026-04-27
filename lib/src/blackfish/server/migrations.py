"""Bootstrap the Blackfish application directory.

`bootstrap` brings `app_dir` to a runnable state — creating directories,
applying DB migrations, normalizing config — and is invoked from both
`blackfish init` and `blackfish start` so upgrade-time work runs wherever
the user enters the system.

Note on terminology: `app_dir` here refers to the *application* directory
(e.g. `~/.blackfish`), which is distinct from a profile's `home_dir` (a
per-profile, often remote, location used to deploy services). This module
only touches the application directory.
"""

from __future__ import annotations

import configparser
import importlib.metadata
import os
from pathlib import Path

from blackfish.server.logger import logger


CURRENT_VERSION = importlib.metadata.version("blackfish-ai")
VERSION_FILE = ".blackfish_app_version"


def read_app_version(app_dir: str | os.PathLike[str]) -> str | None:
    """Return the Blackfish version recorded in `app_dir`, or None if unrecorded."""
    path = Path(app_dir) / VERSION_FILE
    if not path.is_file():
        return None
    contents = path.read_text().strip()
    return contents or None


def write_app_version(app_dir: str | os.PathLike[str], version: str) -> None:
    """Stamp `app_dir` with the given Blackfish version."""
    path = Path(app_dir) / VERSION_FILE
    path.write_text(f"{version}\n")


def ensure_app_dir(app_dir: str | os.PathLike[str]) -> None:
    """Create the application directory and its `models/` and `images/`
    subdirectories if missing.

    Raises FileNotFoundError if the parent of `app_dir` does not exist —
    matches the behavior of the previous `create_local_home_dir` and
    surfaces typo'd `--app-dir` values loudly instead of silently
    materializing a tree under a missing parent.
    """
    app_path = Path(app_dir)
    if app_path.exists() and not app_path.is_dir():
        raise NotADirectoryError(str(app_path))
    if not app_path.exists():
        os.mkdir(app_path)
    (app_path / "models").mkdir(exist_ok=True)
    (app_path / "images").mkdir(exist_ok=True)


def ensure_db(app_dir: str | os.PathLike[str]) -> None:
    """Apply Alembic migrations to `{app_dir}/app.sqlite`. Idempotent."""
    from advanced_alchemy.alembic.commands import AlembicCommands
    from advanced_alchemy.config import (
        AlembicAsyncConfig,
        SQLAlchemyAsyncConfig,
    )
    from advanced_alchemy.base import UUIDAuditBase

    import blackfish.server as server

    server_dir = os.path.dirname(server.__file__)
    migrations_dir = os.path.join(server_dir, "db", "migrations")

    db_config = SQLAlchemyAsyncConfig(
        connection_string=f"sqlite+aiosqlite:///{app_dir}/app.sqlite",
        metadata=UUIDAuditBase.metadata,
        create_all=False,
        alembic_config=AlembicAsyncConfig(
            version_table_name="ddl_version",
            script_config=os.path.join(migrations_dir, "alembic.ini"),
            script_location=migrations_dir,
        ),
    )

    logger.info("Upgrading database...")
    AlembicCommands(sqlalchemy_config=db_config).upgrade()


def normalize_profiles_cfg(app_dir: str | os.PathLike[str]) -> None:
    """Rewrite legacy `type =` keys to `schema =` in `app_dir/profiles.cfg`.

    Only writes when at least one section changes, so `mtime` is preserved
    across no-op bootstraps.
    """
    cfg_path = Path(app_dir) / "profiles.cfg"
    if not cfg_path.is_file():
        return

    parser = configparser.ConfigParser()
    parser.read(cfg_path)

    changed = False
    for section in parser.sections():
        if "type" in parser[section] and "schema" not in parser[section]:
            parser[section]["schema"] = parser[section]["type"]
            del parser[section]["type"]
            changed = True

    if changed:
        with open(cfg_path, "w") as f:
            parser.write(f)


def bootstrap(app_dir: str | os.PathLike[str]) -> None:
    """Apply all install/upgrade-time reconciliation steps to `app_dir`."""
    ensure_app_dir(app_dir)
    ensure_db(app_dir)
    normalize_profiles_cfg(app_dir)
    write_app_version(app_dir, CURRENT_VERSION)
