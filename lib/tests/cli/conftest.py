import pytest
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch

from blackfish.server.config import ContainerProvider


@pytest.fixture()
def cli_runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def mock_config():
    """Mock configuration for CLI tests."""
    with patch("blackfish.cli.__main__.config") as mock_config:
        mock_config.HOST = "localhost"
        mock_config.PORT = 8000
        mock_config.HOME_DIR = (
            Path(__file__).parent.parent / "tests",
        )  # "/tmp/blackfish-test"
        # A real provider, so job scripts rendered from this config aren't
        # empty: the templates branch on `provider == "docker"`.
        mock_config.CONTAINER_PROVIDER = ContainerProvider.Docker
        yield mock_config
