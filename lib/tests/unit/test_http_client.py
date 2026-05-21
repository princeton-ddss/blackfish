"""Tests for the shared httpx.AsyncClient module."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from blackfish.server import http_client as hc


def test_client_is_configured() -> None:
    assert isinstance(hc.http_client, httpx.AsyncClient)
    assert hc.http_client.timeout.connect == 5.0
    assert hc.http_client.timeout.read == 30.0


def test_health_check_timeout_fails_fast() -> None:
    assert hc.HEALTH_CHECK_TIMEOUT.read == 5.0


def test_stream_timeout_disables_read_deadline() -> None:
    # Streaming generations may pause arbitrarily long between chunks.
    assert hc.STREAM_TIMEOUT.read is None


@pytest.mark.anyio
async def test_close_http_client_closes_client() -> None:
    with patch.object(hc.http_client, "aclose", new=AsyncMock()) as mock_aclose:
        await hc.close_http_client()
    mock_aclose.assert_awaited_once()
