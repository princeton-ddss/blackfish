import pytest
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch


@pytest.fixture()
def cli_runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def mock_config():
    """Mock configuration for CLI tests."""
    with patch("app.cli.__main__.config") as mock_config:
        mock_config.HOST = "localhost"
        mock_config.PORT = 8000
        mock_config.HOME_DIR = (
            Path(__file__).parent.parent / "tests",
        )  # "/tmp/blackfish-test"
        yield mock_config
