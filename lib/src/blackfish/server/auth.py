"""Auth token storage shared by the server and the CLI.

The server mints a token on each start and writes it here; the CLI reads it
back, so a user running commands in another shell never has to export
anything. Both processes run as the same user on the same host — an
assumption the CLI already makes (it speaks plain HTTP to localhost).

The token rotates per server start, so the file is current-state, not a
durable secret: it is written 0600 and removed on shutdown.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

TOKEN_FILE = "auth_token"


def generate_token() -> str:
    """Return a fresh URL-safe token.

    URL-safe rather than base64: the token is pasted into a `?token=` login
    link and into shell commands, and `+`/`/`/`=` need escaping in both.
    """
    return secrets.token_urlsafe(32)


def token_file_path(home_dir: str | os.PathLike[str]) -> Path:
    """Return the path to the token file inside `home_dir`."""
    return Path(home_dir) / TOKEN_FILE


def write_token_file(home_dir: str | os.PathLike[str], token: str) -> None:
    """Write `token` to the token file, readable only by the current user.

    The mode is set at creation rather than by a following `chmod`, which
    would leave the token briefly world-readable. Written to a temporary file
    and renamed so a concurrent reader never sees a partial token.
    """
    path = token_file_path(home_dir)
    # Per-PID temp name: two concurrent starts sharing a HOME_DIR would
    # otherwise write and rename the same file, and one could end up serving a
    # token the other had already replaced.
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    fd = os.open(tmp, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(f"{token}\n")
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    os.replace(tmp, path)


def read_token_file(home_dir: str | os.PathLike[str]) -> str | None:
    """Return the stored token, or `None` if it can't be read.

    Never raises: this sits on the path of every CLI command, including ones
    aimed at a server that needs no authentication at all.
    """
    try:
        token = token_file_path(home_dir).read_text().strip()
    except (OSError, UnicodeDecodeError):
        return None
    return token or None


def remove_token_file(home_dir: str | os.PathLike[str]) -> None:
    """Delete the token file if present. Best-effort and idempotent."""
    try:
        token_file_path(home_dir).unlink(missing_ok=True)
    except OSError:
        pass
