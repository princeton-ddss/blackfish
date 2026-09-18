"""Unit tests for the cli.api HTTP wrappers."""

from unittest.mock import patch

import pytest
import requests

from blackfish.cli import api
from blackfish.server.auth import write_token_file


@pytest.fixture(autouse=True)
def _empty_home(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """Point HOME_DIR at an empty directory.

    `_headers` now falls back to the token file, so these tests would otherwise
    pick up whatever token the developer's real ~/.blackfish happens to hold.
    """
    monkeypatch.setattr(api.config, "HOME_DIR", str(tmp_path))
    return tmp_path


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


def test_headers_fall_back_to_token_file(
    _empty_home, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The CLI picks up the running server's token with nothing exported.

    This is the whole point of the token file: `blackfish start` in one shell,
    CLI commands in another.
    """
    monkeypatch.delenv("BLACKFISH_AUTH_TOKEN", raising=False)
    write_token_file(_empty_home, "fromfile")
    assert api._headers() == {"Authorization": "Bearer fromfile"}


def test_env_token_beats_token_file(
    _empty_home, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An explicit token wins, so the CLI can target a server it didn't start."""
    write_token_file(_empty_home, "fromfile")
    monkeypatch.setenv("BLACKFISH_AUTH_TOKEN", "fromenv")
    assert api._headers() == {"Authorization": "Bearer fromenv"}


def test_empty_env_token_falls_back_to_file(
    _empty_home, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An empty env var is not an intent to authenticate as nobody."""
    write_token_file(_empty_home, "fromfile")
    monkeypatch.setenv("BLACKFISH_AUTH_TOKEN", "")
    assert api._headers() == {"Authorization": "Bearer fromfile"}


def test_auth_hint_names_the_token_path(_empty_home) -> None:
    """A bare `status=401` gives the user nothing to act on."""
    res = requests.Response()
    res.status_code = 401
    hint = api.auth_hint(res)
    assert hint is not None
    assert str(_empty_home) in hint


def test_auth_hint_is_none_for_other_statuses() -> None:
    res = requests.Response()
    res.status_code = 500
    assert api.auth_hint(res) is None


def test_url_uses_config_host_and_port() -> None:
    """`_url` should prefix paths with the active config's host/port."""
    with (
        patch.object(api.config, "HOST", "example.test"),
        patch.object(api.config, "PORT", 9999),
    ):
        assert api._url("/api/services") == "http://example.test:9999/api/services"
