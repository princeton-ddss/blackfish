"""HTTP wrappers for CLI → backend calls.

Centralizes the two things every CLI request needs: the base URL
(`http://{HOST}:{PORT}`) and the bearer token from
``BLACKFISH_AUTH_TOKEN``. The token is read fresh from the environment
on each call rather than from the config singleton — the singleton nulls
``AUTH_TOKEN`` when ``BLACKFISH_DEBUG=1``, but the CLI's local debug flag
shouldn't gate whether it presents credentials to a remote server.

Only ``get``/``post``/``put``/``delete`` are wrapped, with the kwargs
the CLI actually uses (``params``, ``json``). Add more as needed —
don't reach for generic ``**kwargs``.
"""

from __future__ import annotations

import os
from typing import Any

import requests

from blackfish.server.config import config


def _url(path: str) -> str:
    return f"http://{config.HOST}:{config.PORT}{path}"


def _headers() -> dict[str, str]:
    token = os.getenv("BLACKFISH_AUTH_TOKEN")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


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
