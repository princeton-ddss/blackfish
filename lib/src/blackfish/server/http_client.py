"""Shared httpx.AsyncClient for server-internal HTTP calls.

Used by async code paths (service ping, proxy streaming, internal POSTs)
so a sync `requests` call doesn't block the event loop.
"""

import httpx

_DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=5.0)
_DEFAULT_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=20)

# Health checks should fail fast so the service refresh loop never stalls.
HEALTH_CHECK_TIMEOUT = httpx.Timeout(connect=5.0, read=5.0, write=5.0, pool=5.0)

# Streaming responses (e.g. LLM generations) may pause arbitrarily long
# between chunks, so the read timeout is disabled for the streaming proxy.
STREAM_TIMEOUT = httpx.Timeout(connect=5.0, read=None, write=30.0, pool=5.0)

http_client = httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT, limits=_DEFAULT_LIMITS)


async def close_http_client() -> None:
    await http_client.aclose()
