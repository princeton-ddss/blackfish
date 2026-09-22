"""`blackfish details` reports whether a service requires an API key.

The hint is fetched from its own endpoint rather than read off the service
payload: keeping it off that payload is what stops `details` round-tripping it
back into `Service(**body)`, where a read-only attribute has no setter.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
import requests

from blackfish.cli.__main__ import _fetch_api_key_hint


def _response(ok: bool, body: dict) -> Mock:
    res = Mock()
    res.ok = ok
    res.json.return_value = body
    return res


class TestFetchApiKeyHint:
    def test_returns_the_hint_for_a_keyed_service(self):
        res = _response(True, {"configured": True, "hint": "...cdef"})

        with patch("blackfish.cli.__main__.api.get", return_value=res):
            assert _fetch_api_key_hint("svc-1") == "...cdef"

    def test_returns_none_when_no_key_is_set(self):
        res = _response(True, {"configured": False, "hint": None})

        with patch("blackfish.cli.__main__.api.get", return_value=res):
            assert _fetch_api_key_hint("svc-1") is None

    def test_returns_none_on_an_error_response(self):
        """A missing hint must not stop `details` printing everything else."""
        res = _response(False, {})

        with patch("blackfish.cli.__main__.api.get", return_value=res):
            assert _fetch_api_key_hint("svc-1") is None

    @pytest.mark.parametrize(
        "exc",
        [requests.exceptions.ConnectionError, requests.exceptions.Timeout],
    )
    def test_returns_none_when_the_api_is_unreachable(self, exc):
        with patch("blackfish.cli.__main__.api.get", side_effect=exc()):
            assert _fetch_api_key_hint("svc-1") is None
