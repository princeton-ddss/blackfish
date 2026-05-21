"""Tests for the shared httpx.AsyncClient factory."""

from __future__ import annotations

import httpx
import pytest

from blackfish.server import http_client as hc


def test_factory_returns_configured_client() -> None:
    client = hc.create_http_client()
    assert isinstance(client, httpx.AsyncClient)
    assert client.timeout.connect == 5.0
    assert client.timeout.read == 30.0


def test_factory_returns_distinct_instances() -> None:
    assert hc.create_http_client() is not hc.create_http_client()


def test_health_check_timeout_fails_fast() -> None:
    assert hc.HEALTH_CHECK_TIMEOUT.read == 5.0


def test_stream_timeout_disables_read_deadline() -> None:
    # Streaming generations may pause arbitrarily long between chunks.
    assert hc.STREAM_TIMEOUT.read is None


@pytest.mark.anyio
async def test_client_can_be_closed() -> None:
    client = hc.create_http_client()
    await client.aclose()
    assert client.is_closed
