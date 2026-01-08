import pytest
import tempfile
import os
from unittest.mock import patch
from click.testing import CliRunner
from blackfish.cli.__main__ import main


@pytest.fixture
def temp_home_dir():
    """Create a temporary directory for testing profile operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def cli_runner():
    """CLI runner fixture."""
    return CliRunner()


@pytest.fixture
def mock_profiles_config():
    """Mock profiles.cfg content for testing."""
    return """[default]
schema = local
home_dir = /tmp/test/home
cache_dir = /tmp/test/cache

[slurm-test]
schema = slurm
host = test.cluster.edu
user = testuser
home_dir = /home/testuser/.blackfish
cache_dir = /scratch/testuser/cache
"""


@pytest.fixture
def mock_empty_profiles_config():
    """Mock empty profiles.cfg content."""
    return ""


class TestProfileList:
    """Test profile ls command."""

    def test_list_profiles_success(
        self, cli_runner, temp_home_dir, mock_profiles_config
    ):
        """Test successful listing of profiles."""
        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            # Write mock profiles config
            with open(profiles_path, "w") as f:
                f.write(mock_profiles_config)

            result = cli_runner.invoke(main, ["profile", "ls"])

            assert result.exit_code == 0
            assert "[default]" in result.output
            assert "schema: local" in result.output
            assert "[slurm-test]" in result.output
            assert "schema: slurm" in result.output
            assert "host: test.cluster.edu" in result.output
            assert "user: testuser" in result.output

    def test_list_profiles_empty(self, cli_runner, temp_home_dir):
        """Test listing profiles when no profiles exist."""
        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            # Create empty profiles config
            with open(profiles_path, "w") as f:
                f.write("")

            result = cli_runner.invoke(main, ["profile", "ls"])

            assert result.exit_code == 0
            # Should complete successfully even with empty profiles


class TestProfileShow:
    """Test profile show command."""

    def test_show_profile_success(
        self, cli_runner, temp_home_dir, mock_profiles_config
    ):
        """Test successful showing of a specific profile."""
        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            # Write mock profiles config
            with open(profiles_path, "w") as f:
                f.write(mock_profiles_config)

            result = cli_runner.invoke(
                main, ["profile", "show", "--name", "slurm-test"]
            )

            assert result.exit_code == 0
            assert "[slurm-test]" in result.output
            assert "schema: slurm" in result.output
            assert "host: test.cluster.edu" in result.output
            assert "user: testuser" in result.output

    def test_show_profile_default(
        self, cli_runner, temp_home_dir, mock_profiles_config
    ):
        """Test showing default profile when no name specified."""
        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            # Write mock profiles config
            with open(profiles_path, "w") as f:
                f.write(mock_profiles_config)

            result = cli_runner.invoke(main, ["profile", "show"])

            assert result.exit_code == 0
            assert "[default]" in result.output
            assert "schema: local" in result.output

    def test_show_profile_not_found(
        self, cli_runner, temp_home_dir, mock_profiles_config
    ):
        """Test showing a profile that doesn't exist."""
        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            # Write mock profiles config
            with open(profiles_path, "w") as f:
                f.write(mock_profiles_config)

            result = cli_runner.invoke(
                main, ["profile", "show", "--name", "nonexistent"]
            )

            assert result.exit_code == 1
            assert "Profile nonexistent not found" in result.output


class TestProfileAdd:
    """Test profile add command."""

    @patch("blackfish.cli.profile.input")
    @patch("blackfish.cli.profile.create_local_home_dir")
    @patch("blackfish.cli.profile.check_local_cache_exists")
    def test_add_local_profile_success(
        self, mock_check_cache, mock_create_home, mock_input, cli_runner, temp_home_dir
    ):
        """Test successful creation of a local profile."""
        # Mock user inputs
        mock_input.side_effect = [
            "test-local",  # profile name
            "local",  # profile schema
            "/tmp/home",  # home directory
            "/tmp/cache",  # cache directory
        ]

        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            # Create empty profiles config
            with open(profiles_path, "w") as f:
                f.write("")

            result = cli_runner.invoke(main, ["profile", "add"])

            assert result.exit_code == 0
            assert "Created profile test-local" in result.output

            # Check that profile was actually written
            with open(profiles_path, "r") as f:
                content = f.read()
                assert "[test-local]" in content
                assert "schema = local" in content

    @patch("blackfish.cli.profile.input")
    @patch("blackfish.cli.profile.create_remote_home_dir")
    @patch("blackfish.cli.profile.check_remote_cache_exists")
    def test_add_slurm_profile_success(
        self, mock_check_cache, mock_create_home, mock_input, cli_runner, temp_home_dir
    ):
        """Test successful creation of a slurm profile."""
        # Mock user inputs
        mock_input.side_effect = [
            "test-slurm",  # profile name
            "slurm",  # profile schema
            "test.edu",  # host
            "testuser",  # user
            "/home/testuser/.blackfish",  # home directory
            "/scratch/cache",  # cache directory
        ]

        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            # Create empty profiles config
            with open(profiles_path, "w") as f:
                f.write("")

            result = cli_runner.invoke(main, ["profile", "add"])

            assert result.exit_code == 0
            assert "Created profile test-slurm" in result.output

            # Check that profile was actually written
            with open(profiles_path, "r") as f:
                content = f.read()
                assert "[test-slurm]" in content
                assert "schema = slurm" in content
                assert "host = test.edu" in content

    @patch("blackfish.cli.profile.input")
    def test_add_profile_already_exists(
        self, mock_input, cli_runner, temp_home_dir, mock_profiles_config
    ):
        """Test adding a profile that already exists."""
        # Mock user inputs
        mock_input.side_effect = [
            "default",  # profile name (already exists)
        ]

        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            # Write existing profiles config
            with open(profiles_path, "w") as f:
                f.write(mock_profiles_config)

            result = cli_runner.invoke(main, ["profile", "add"])

            assert result.exit_code == 1
            assert "Profile named default already exists" in result.output

    @patch("blackfish.cli.profile.input")
    def test_add_profile_invalid_schema(self, mock_input, cli_runner, temp_home_dir):
        """Test adding a profile with invalid schema."""
        # Mock user inputs
        mock_input.side_effect = [
            "test-profile",  # profile name
            "invalid",  # invalid schema
            "local",  # valid schema (retry)
            "/tmp/home",  # home directory
            "/tmp/cache",  # cache directory
        ]

        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with (
            patch("blackfish.cli.__main__.config") as mock_config,
            patch("blackfish.cli.profile.create_local_home_dir"),
            patch("blackfish.cli.profile.check_local_cache_exists"),
        ):
            mock_config.HOME_DIR = temp_home_dir

            # Create empty profiles config
            with open(profiles_path, "w") as f:
                f.write("")

            result = cli_runner.invoke(main, ["profile", "add"])

            assert result.exit_code == 0
            assert "Profile schema should be one of" in result.output
            assert "Created profile test-profile" in result.output


class TestProfileUpdate:
    """Test profile update command."""

    @patch("blackfish.cli.profile.input")
    @patch("blackfish.cli.profile.create_local_home_dir")
    @patch("blackfish.cli.profile.check_local_cache_exists")
    def test_update_local_profile_success(
        self,
        mock_check_cache,
        mock_create_home,
        mock_input,
        cli_runner,
        temp_home_dir,
        mock_profiles_config,
    ):
        """Test successful update of a local profile."""
        # Mock user inputs for updating the default profile
        mock_input.side_effect = [
            "/new/home",  # new home directory
            "/new/cache",  # new cache directory
        ]

        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            # Write existing profiles config
            with open(profiles_path, "w") as f:
                f.write(mock_profiles_config)

            result = cli_runner.invoke(main, ["profile", "update", "--name", "default"])

            assert result.exit_code == 0
            assert "Updated profile default" in result.output

    def test_update_profile_not_found(
        self, cli_runner, temp_home_dir, mock_profiles_config
    ):
        """Test updating a profile that doesn't exist."""
        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            # Write existing profiles config
            with open(profiles_path, "w") as f:
                f.write(mock_profiles_config)

            result = cli_runner.invoke(
                main, ["profile", "update", "--name", "nonexistent"]
            )

            assert result.exit_code == 1
            assert "Profile nonexistent not found" in result.output


class TestProfileDelete:
    """Test profile rm command."""

    @patch("blackfish.cli.profile.input")
    def test_delete_profile_success(
        self, mock_input, cli_runner, temp_home_dir, mock_profiles_config
    ):
        """Test successful deletion of a profile."""
        # Mock user confirmation
        mock_input.return_value = "y"

        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            # Write existing profiles config
            with open(profiles_path, "w") as f:
                f.write(mock_profiles_config)

            result = cli_runner.invoke(main, ["profile", "rm", "--name", "slurm-test"])

            assert result.exit_code == 0
            assert "Profile slurm-test deleted" in result.output

            # Verify profile was actually removed
            with open(profiles_path, "r") as f:
                content = f.read()
                assert "[slurm-test]" not in content
                assert "[default]" in content  # should still exist

    @patch("blackfish.cli.profile.input")
    def test_delete_profile_cancelled(
        self, mock_input, cli_runner, temp_home_dir, mock_profiles_config
    ):
        """Test cancelling profile deletion."""
        # Mock user cancellation
        mock_input.return_value = "n"

        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            # Write existing profiles config
            with open(profiles_path, "w") as f:
                f.write(mock_profiles_config)

            result = cli_runner.invoke(main, ["profile", "rm", "--name", "slurm-test"])

            assert result.exit_code == 0
            # Should not show deletion message
            assert "Profile slurm-test deleted" not in result.output

            # Verify profile still exists
            with open(profiles_path, "r") as f:
                content = f.read()
                assert "[slurm-test]" in content

    def test_delete_profile_not_found(
        self, cli_runner, temp_home_dir, mock_profiles_config
    ):
        """Test deleting a profile that doesn't exist."""
        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            # Write existing profiles config
            with open(profiles_path, "w") as f:
                f.write(mock_profiles_config)

            result = cli_runner.invoke(main, ["profile", "rm", "--name", "nonexistent"])

            assert result.exit_code == 1
            assert "Profile nonexistent not found" in result.output


class TestBackwardCompatibility:
    """Test backward compatibility with old 'type' field."""

    def test_read_legacy_type_field(self, cli_runner, temp_home_dir):
        """Test that profiles with 'type' field still work."""
        legacy_config = """[legacy-profile]
type = local
home_dir = /tmp/legacy/home
cache_dir = /tmp/legacy/cache

[legacy-slurm]
type = slurm
host = legacy.cluster.edu
user = legacyuser
home_dir = /home/legacyuser/.blackfish
cache_dir = /scratch/legacyuser/cache
"""

        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            # Write legacy profiles config
            with open(profiles_path, "w") as f:
                f.write(legacy_config)

            result = cli_runner.invoke(
                main, ["profile", "show", "--name", "legacy-profile"]
            )

            assert result.exit_code == 0
            assert "[legacy-profile]" in result.output
            assert (
                "schema: local" in result.output
            )  # Should display as "schema" even from "type"

    def test_mixed_type_and_schema_fields(self, cli_runner, temp_home_dir):
        """Test that profiles with both 'type' and 'schema' fields work (schema takes precedence)."""
        mixed_config = """[mixed-profile]
type = slurm
schema = local
home_dir = /tmp/mixed/home
cache_dir = /tmp/mixed/cache
"""

        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            # Write mixed profiles config
            with open(profiles_path, "w") as f:
                f.write(mixed_config)

            result = cli_runner.invoke(
                main, ["profile", "show", "--name", "mixed-profile"]
            )

            assert result.exit_code == 0
            assert "[mixed-profile]" in result.output
            assert (
                "schema: local" in result.output
            )  # Should use 'schema' field, not 'type'
