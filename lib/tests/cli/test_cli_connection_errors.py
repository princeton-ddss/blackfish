"""Connection-error handling for CLI commands without dedicated test files.

Covers the `rm`, `prune`, `details`, and `ls` commands, which each make a
single API request. Parametrized over both `ConnectionError` and `Timeout`,
since a refused connection and a hung server are handled the same way.
"""

from unittest.mock import patch

import pytest
import requests
from click.testing import CliRunner

from blackfish.cli.__main__ import ls, rm, prune, details

TRANSPORT_ERRORS = [
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
]


@pytest.mark.parametrize("exc", TRANSPORT_ERRORS)
def test_ls_connection_error(exc):
    """`ls` reports a friendly error when the API is unreachable."""
    runner = CliRunner()
    with patch("blackfish.cli.__main__.requests.get", side_effect=exc("boom")):
        result = runner.invoke(ls, [])

    assert result.exit_code == 0
    assert "Failed to connect" in result.output


@pytest.mark.parametrize("exc", TRANSPORT_ERRORS)
def test_rm_connection_error(exc):
    """`rm` reports a friendly error when the API is unreachable."""
    runner = CliRunner()
    with patch("blackfish.cli.__main__.requests.delete", side_effect=exc("boom")):
        result = runner.invoke(rm, [])

    assert result.exit_code == 0
    assert "Failed to connect" in result.output


@pytest.mark.parametrize("exc", TRANSPORT_ERRORS)
def test_prune_connection_error(exc):
    """`prune` reports a friendly error when the API is unreachable."""
    runner = CliRunner()
    with patch("blackfish.cli.__main__.requests.delete", side_effect=exc("boom")):
        result = runner.invoke(prune, input="y\n")

    assert result.exit_code == 0
    assert "Failed to connect" in result.output


@pytest.mark.parametrize("exc", TRANSPORT_ERRORS)
def test_details_connection_error(exc):
    """`details` reports a friendly error when the API is unreachable."""
    runner = CliRunner()
    with patch("blackfish.cli.__main__.requests.get", side_effect=exc("boom")):
        result = runner.invoke(details, ["abc123"])

    assert result.exit_code == 0
    assert "Failed to connect" in result.output
