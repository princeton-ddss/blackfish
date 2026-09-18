"""HTTP wrappers for CLI → backend calls.

Centralizes the two things every CLI request needs: the base URL
(`http://{HOST}:{PORT}`) and the bearer token. The token is read fresh on
each call rather than from the config singleton — the singleton nulls
``AUTH_TOKEN`` when ``BLACKFISH_DEBUG=1``, but the CLI's local debug flag
shouldn't gate whether it presents credentials to a remote server.

``BLACKFISH_AUTH_TOKEN`` wins when set, so a user can point the CLI at a
server they didn't start. Otherwise the token comes from the file the
server wrote at startup, which is what keeps ``blackfish start`` in one
shell and CLI commands in another working with nothing exported.

Only ``get``/``post``/``put``/``delete`` are wrapped, with the kwargs
the CLI actually uses (``params``, ``json``). Add more as needed —
don't reach for generic ``**kwargs``.
"""

from __future__ import annotations

import os
from typing import Any

import requests

from blackfish.server.auth import read_token_file, token_file_path
from blackfish.server.config import config


def _url(path: str) -> str:
    return f"http://{config.HOST}:{config.PORT}{path}"


def _headers() -> dict[str, str]:
    token = os.getenv("BLACKFISH_AUTH_TOKEN") or read_token_file(config.HOME_DIR)
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def auth_hint(res: requests.Response) -> str | None:
    """Return an explanation for an auth failure, or `None` for other statuses.

    A bare `status=401` gives the user nothing to act on. The usual cause is a
    `BLACKFISH_HOME_DIR` that differs from the one the server used, so name the
    path the CLI actually looked at.
    """
    if res.status_code in (401, 403):
        return (
            "Not authorized. The server requires authentication; expected a token"
            f" at {token_file_path(config.HOME_DIR)}. Check that BLACKFISH_HOME_DIR"
            " matches the server's, or set BLACKFISH_AUTH_TOKEN to the token"
            " printed at startup."
        )
    return None


def get(
    path: str,
    *,
    params: dict[str, Any] | None = None,
) -> requests.Response:
    return requests.get(_url(path), headers=_headers(), params=params)


def post(
    path: str,
    *,
    json: Any = None,
    params: dict[str, Any] | None = None,
) -> requests.Response:
    return requests.post(_url(path), headers=_headers(), json=json, params=params)


def put(
    path: str,
    *,
    json: Any = None,
    params: dict[str, Any] | None = None,
) -> requests.Response:
    return requests.put(_url(path), headers=_headers(), json=json, params=params)


def delete(
    path: str,
    *,
    params: dict[str, Any] | None = None,
) -> requests.Response:
    return requests.delete(_url(path), headers=_headers(), params=params)
