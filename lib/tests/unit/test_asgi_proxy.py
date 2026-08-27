"""Unit tests for the non-streaming proxy helper (`asyncpost`).

Regression coverage for #453: a downstream 4xx/5xx must surface as an
`HTTPException` with the upstream status, not be returned as a successful
JSON body.
"""

from __future__ import annotations

import httpx
import pytest
from litestar.exceptions import HTTPException

pytestmark = pytest.mark.anyio


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_asyncpost_returns_json_on_success():
    from blackfish.server.asgi import asyncpost

    def handler(request):
        return httpx.Response(200, json={"ok": True})

    async with _client(handler) as client:
        result = await asyncpost(client, "http://svc/x", b"{}", {})

    assert result == {"ok": True}


async def test_asyncpost_forwards_upstream_status_and_message():
    from blackfish.server.asgi import asyncpost

    def handler(request):
        return httpx.Response(422, json={"message": "bad audio format"})

    async with _client(handler) as client:
        with pytest.raises(HTTPException) as exc_info:
            await asyncpost(client, "http://svc/x", b"{}", {})

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "bad audio format"


async def test_asyncpost_falls_back_to_text_when_body_is_not_json():
    from blackfish.server.asgi import asyncpost

    def handler(request):
        return httpx.Response(500, content=b"upstream crashed")

    async with _client(handler) as client:
        with pytest.raises(HTTPException) as exc_info:
            await asyncpost(client, "http://svc/x", b"{}", {})

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "upstream crashed"
