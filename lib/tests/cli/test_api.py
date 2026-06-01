"""Unit tests for the cli.api HTTP wrappers."""

from unittest.mock import patch

import pytest

from blackfish.cli import api


def test_headers_with_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BLACKFISH_AUTH_TOKEN", "abc123")
    assert api._headers() == {"Authorization": "Bearer abc123"}


def test_headers_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BLACKFISH_AUTH_TOKEN", raising=False)
    assert api._headers() == {}


def test_headers_empty_token_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """An empty BLACKFISH_AUTH_TOKEN should not produce an `Authorization` header.

    `requests` would happily send `Bearer ` (with no token), which the server
    would reject — but it's cleaner to omit the header entirely.
    """
    monkeypatch.setenv("BLACKFISH_AUTH_TOKEN", "")
    assert api._headers() == {}


def test_url_uses_config_host_and_port() -> None:
    """`_url` should prefix paths with the active config's host/port."""
    with (
        patch.object(api.config, "HOST", "example.test"),
        patch.object(api.config, "PORT", 9999),
    ):
        assert api._url("/api/services") == "http://example.test:9999/api/services"
