"""Factory and timeout configuration for the shared httpx.AsyncClient.

The server holds one client on `app.state`; the programmatic client holds
one on the `BlackfishClient` instance. Both are built via `create_http_client`
so async code paths never make a blocking `requests` call.
"""

import httpx

_DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=5.0)
_DEFAULT_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=20)

# Health checks should fail fast so the service refresh loop never stalls.
HEALTH_CHECK_TIMEOUT = httpx.Timeout(connect=5.0, read=5.0, write=5.0, pool=5.0)

# Streaming responses (e.g. LLM generations) may pause arbitrarily long
# between chunks, so the read timeout is disabled for the streaming proxy.
STREAM_TIMEOUT = httpx.Timeout(connect=5.0, read=None, write=30.0, pool=5.0)

# Non-streaming proxied inference (e.g. CPU transcription) can take longer than
# the default 30s read timeout to return a single response. The service UI is
# meant for short clips, so 60s is a generous-but-bounded ceiling; a read
# timeout here surfaces as a 504 with an actionable message.
PROXY_TIMEOUT = httpx.Timeout(connect=5.0, read=60.0, write=30.0, pool=5.0)


def create_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT, limits=_DEFAULT_LIMITS)
