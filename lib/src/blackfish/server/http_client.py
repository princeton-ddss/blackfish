"""Shared httpx.AsyncClient for server-internal HTTP calls.

Used by async code paths (service ping, proxy streaming, internal POSTs)
so a sync `requests` call doesn't block the event loop.
"""

import httpx

_DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=5.0)
_DEFAULT_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=20)

http_client = httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT, limits=_DEFAULT_LIMITS)


async def close_http_client() -> None:
    await http_client.aclose()
