"""Regression coverage for errors surfaced by the service proxy."""

import json

import httpx
import pytest
from litestar.testing import AsyncTestClient

pytestmark = pytest.mark.anyio


async def test_non_streaming_read_timeout_returns_504(
    client: AsyncTestClient, monkeypatch: pytest.MonkeyPatch
):
    payload = {"audio_path": "/audio/clip.wav"}
    requests = []

    def timeout(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        raise httpx.ReadTimeout("Upstream inference stalled", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout)) as upstream:
        # Restore the application's client before its shutdown hook closes it.
        with monkeypatch.context() as patcher:
            patcher.setattr(client.app.state, "http_client", upstream)
            response = await client.post(
                "/proxy/8080/transcribe",
                params={"streaming": "false"},
                json=payload,
            )

    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert str(requests[0].url) == "http://localhost:8080/transcribe"
    assert json.loads(requests[0].content) == payload
    assert response.status_code == 504
    detail = response.json()["detail"]
    assert "CPU (no GPU)" in detail
    assert "shorter audio clip" in detail
    assert "GPU-backed service" in detail
