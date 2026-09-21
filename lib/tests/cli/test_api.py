"""Unit tests for the cli.api HTTP wrappers."""

from unittest.mock import patch

import logging

import pytest
import requests

from blackfish.cli import api
from blackfish.cli.__main__ import _RedactQueryTokens
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


def test_auth_hint_is_short_enough_for_a_spinner(_empty_home) -> None:
    """yaspin truncates `spinner.text` to the terminal width rather than
    wrapping, so the hint has to fit on one line — the remedy goes to
    `auth_help`."""
    res = requests.Response()
    res.status_code = 401
    hint = api.auth_hint(res)
    assert hint is not None
    assert len(hint) < 70


def test_auth_help_names_the_token_path(_empty_home) -> None:
    """A bare `status=401` gives the user nothing to act on."""
    help_text = api.auth_help()
    assert str(_empty_home) in help_text
    assert "BLACKFISH_HOME_DIR" in help_text
    assert "BLACKFISH_AUTH_TOKEN" in help_text


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


class TestAccessLogRedaction:
    """The login link puts the token in a query string, which uvicorn's access
    logger would otherwise write to stdout verbatim."""

    def _record(self, msg: str, args: tuple) -> logging.LogRecord:
        return logging.LogRecord(
            name="uvicorn.access",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg=msg,
            args=args,
            exc_info=None,
        )

    def test_redacts_token_in_args(self) -> None:
        f = _RedactQueryTokens()
        record = self._record('%s - "%s %s"', ("::1", "GET", "/login?token=secret123"))
        f.filter(record)
        assert "secret123" not in record.getMessage()
        assert "token=<redacted>" in record.getMessage()

    def test_redacts_token_in_msg(self) -> None:
        f = _RedactQueryTokens()
        record = self._record("GET /login?token=secret123 HTTP/1.1", ())
        f.filter(record)
        assert "secret123" not in record.getMessage()

    def test_leaves_other_query_params_alone(self) -> None:
        f = _RedactQueryTokens()
        record = self._record("%s", ("/login?success=false",))
        f.filter(record)
        assert "success=false" in record.getMessage()

    def test_filter_always_passes_the_record(self) -> None:
        """Redaction must not drop log lines."""
        f = _RedactQueryTokens()
        assert f.filter(self._record("%s", ("/api/info",))) is True
