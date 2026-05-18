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
    @patch("blackfish.cli.profile._setup_profile")
    def test_add_local_profile_success(
        self, mock_setup, mock_input, cli_runner, temp_home_dir
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
            assert "Created profile 'test-local'" in result.output

            # Check that profile was actually written
            with open(profiles_path, "r") as f:
                content = f.read()
                assert "[test-local]" in content
                assert "schema = local" in content

    @patch("blackfish.cli.profile.input")
    @patch("blackfish.cli.profile._setup_profile")
    def test_add_slurm_profile_success(
        self, mock_setup, mock_input, cli_runner, temp_home_dir
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
            "",  # python_path (use default)
        ]

        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            # Create empty profiles config
            with open(profiles_path, "w") as f:
                f.write("")

            result = cli_runner.invoke(main, ["profile", "add"])

            assert result.exit_code == 0
            assert "Created profile 'test-slurm'" in result.output

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
    @patch("blackfish.cli.profile._setup_profile")
    def test_add_profile_invalid_schema(
        self, mock_setup, mock_input, cli_runner, temp_home_dir
    ):
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

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            # Create empty profiles config
            with open(profiles_path, "w") as f:
                f.write("")

            result = cli_runner.invoke(main, ["profile", "add"])

            assert result.exit_code == 0
            assert "Profile schema should be one of" in result.output
            assert "Created profile 'test-profile'" in result.output


class TestProfileUpdate:
    """Test profile update command."""

    @patch("blackfish.cli.profile.input")
    @patch("blackfish.cli.profile.asyncio.run")
    def test_update_local_profile_success(
        self,
        mock_asyncio_run,
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


class TestDefaultResolution:
    """Tests for explicit `default = true` flag and resolution fallback."""

    def test_resolver_prefers_flag(self, temp_home_dir):
        from blackfish.server.models.profile import get_default_profile_name

        config = (
            "[alpha]\nschema = local\nhome_dir = /h\ncache_dir = /c\n\n"
            "[beta]\nschema = local\nhome_dir = /h\ncache_dir = /c\n"
            "default = true\n"
        )
        with open(os.path.join(temp_home_dir, "profiles.cfg"), "w") as f:
            f.write(config)

        assert get_default_profile_name(temp_home_dir) == "beta"

    def test_resolver_falls_back_to_name(self, temp_home_dir):
        from blackfish.server.models.profile import get_default_profile_name

        config = (
            "[alpha]\nschema = local\nhome_dir = /h\ncache_dir = /c\n\n"
            "[default]\nschema = local\nhome_dir = /h\ncache_dir = /c\n"
        )
        with open(os.path.join(temp_home_dir, "profiles.cfg"), "w") as f:
            f.write(config)

        assert get_default_profile_name(temp_home_dir) == "default"

    def test_resolver_falls_back_to_first_section(self, temp_home_dir):
        from blackfish.server.models.profile import get_default_profile_name

        config = (
            "[alpha]\nschema = local\nhome_dir = /h\ncache_dir = /c\n\n"
            "[beta]\nschema = local\nhome_dir = /h\ncache_dir = /c\n"
        )
        with open(os.path.join(temp_home_dir, "profiles.cfg"), "w") as f:
            f.write(config)

        assert get_default_profile_name(temp_home_dir) == "alpha"

    def test_resolver_returns_none_when_empty(self, temp_home_dir):
        from blackfish.server.models.profile import get_default_profile_name

        with open(os.path.join(temp_home_dir, "profiles.cfg"), "w") as f:
            f.write("")

        assert get_default_profile_name(temp_home_dir) is None

    def test_deserialize_reads_default_flag(self, temp_home_dir):
        from blackfish.server.models.profile import deserialize_profiles

        config = (
            "[alpha]\nschema = local\nhome_dir = /h\ncache_dir = /c\n"
            "default = true\n\n"
            "[beta]\nschema = local\nhome_dir = /h\ncache_dir = /c\n"
            "default = false\n"
        )
        with open(os.path.join(temp_home_dir, "profiles.cfg"), "w") as f:
            f.write(config)

        profiles = {p.name: p for p in deserialize_profiles(temp_home_dir)}
        assert profiles["alpha"].default is True
        assert profiles["beta"].default is False


class TestResolveProfileOrExit:
    """`resolve_profile_or_exit` is the shared fallback for `--profile` options."""

    def test_returns_explicit_profile_unchanged(self, temp_home_dir):
        from blackfish.cli.profile import resolve_profile_or_exit

        # An explicit name is returned without touching the config.
        assert resolve_profile_or_exit(temp_home_dir, "myprof") == "myprof"

    def test_resolves_default_when_unset(self, temp_home_dir):
        from blackfish.cli.profile import resolve_profile_or_exit

        config = (
            "[alpha]\nschema = local\nhome_dir = /h\ncache_dir = /c\ndefault = true\n"
        )
        with open(os.path.join(temp_home_dir, "profiles.cfg"), "w") as f:
            f.write(config)

        assert resolve_profile_or_exit(temp_home_dir, None) == "alpha"

    def test_exits_when_no_profiles_configured(self, temp_home_dir):
        from blackfish.cli.profile import resolve_profile_or_exit

        with open(os.path.join(temp_home_dir, "profiles.cfg"), "w") as f:
            f.write("")

        with pytest.raises(SystemExit) as exc_info:
            resolve_profile_or_exit(temp_home_dir, None)
        assert exc_info.value.code == 1


class TestProfileUpdatePreservesDefault:
    """`blackfish profile update` should preserve the `default` flag."""

    @patch("blackfish.cli.profile.input")
    @patch("blackfish.cli.profile.asyncio.run")
    def test_update_preserves_default_flag(
        self, mock_asyncio_run, mock_input, cli_runner, temp_home_dir
    ):
        # Existing config: 'default' section flagged default=true.
        config = (
            "[default]\n"
            "schema = local\n"
            "home_dir = /tmp/test/home\n"
            "cache_dir = /tmp/test/cache\n"
            "default = true\n"
        )
        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")
        with open(profiles_path, "w") as f:
            f.write(config)

        # Accept defaults for both prompts (home, cache).
        mock_input.side_effect = ["", ""]

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            result = cli_runner.invoke(main, ["profile", "update", "--name", "default"])
            assert result.exit_code == 0

            import configparser

            parsed = configparser.ConfigParser()
            parsed.read(profiles_path)
            assert parsed["default"]["default"] == "true"


class TestProfileRename:
    """Tests for `blackfish profile rename <old> <new>`."""

    def test_rename_success(self, cli_runner):
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.ok = True

        with patch(
            "blackfish.cli.profile.requests.put", return_value=mock_response
        ) as mock_put:
            result = cli_runner.invoke(main, ["profile", "rename", "old", "new"])

        assert result.exit_code == 0
        assert "Renamed profile 'old' to 'new'" in result.output
        # The command targets the rename endpoint with the new name in the body.
        url = mock_put.call_args[0][0]
        assert url.endswith("/api/profiles/old/rename")
        assert mock_put.call_args.kwargs["json"] == {"new_name": "new"}

    def test_rename_error_response(self, cli_runner):
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 409
        mock_response.json.return_value = {"detail": "Profile 'new' already exists."}

        with patch("blackfish.cli.profile.requests.put", return_value=mock_response):
            result = cli_runner.invoke(main, ["profile", "rename", "old", "new"])

        assert result.exit_code == 1
        assert "Profile 'new' already exists." in result.output

    def test_rename_connection_error(self, cli_runner):
        import requests

        with patch(
            "blackfish.cli.profile.requests.put",
            side_effect=requests.exceptions.ConnectionError("refused"),
        ):
            result = cli_runner.invoke(main, ["profile", "rename", "old", "new"])

        assert result.exit_code == 1
        assert "Failed to connect" in result.output


class TestProfileDefaultCommand:
    """Tests for `blackfish profile default <name>`."""

    def test_set_default_assigns_exclusive_flag(
        self, cli_runner, temp_home_dir, mock_profiles_config
    ):
        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            with open(profiles_path, "w") as f:
                f.write(mock_profiles_config)

            result = cli_runner.invoke(main, ["profile", "default", "slurm-test"])
            assert result.exit_code == 0

            import configparser

            parsed = configparser.ConfigParser()
            parsed.read(profiles_path)
            assert parsed["slurm-test"]["default"] == "true"
            assert parsed["default"]["default"] == "false"

    def test_set_default_not_found(
        self, cli_runner, temp_home_dir, mock_profiles_config
    ):
        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            with open(profiles_path, "w") as f:
                f.write(mock_profiles_config)

            result = cli_runner.invoke(main, ["profile", "default", "nope"])
            assert result.exit_code == 1
            assert "Profile nope not found" in result.output

    def test_delete_refuses_default(
        self, cli_runner, temp_home_dir, mock_profiles_config
    ):
        # `default` profile is the resolved default (by legacy name); refuse rm.
        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            with open(profiles_path, "w") as f:
                f.write(mock_profiles_config)

            result = cli_runner.invoke(main, ["profile", "rm", "--name", "default"])
            assert result.exit_code == 1
            assert "is the default profile" in result.output

            with open(profiles_path, "r") as f:
                assert "[default]" in f.read()

    @patch("blackfish.cli.profile.input")
    def test_delete_force_removes_default(
        self, mock_input, cli_runner, temp_home_dir, mock_profiles_config
    ):
        mock_input.return_value = "y"
        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            with open(profiles_path, "w") as f:
                f.write(mock_profiles_config)

            result = cli_runner.invoke(
                main, ["profile", "rm", "--name", "default", "--force"]
            )
            assert result.exit_code == 0
            with open(profiles_path, "r") as f:
                assert "[default]" not in f.read()
            # No remaining profile is flagged default -> user is warned.
            assert "No default profile is set" in result.output


class TestProfileUpgrade:
    """Test profile upgrade command."""

    @pytest.fixture
    def mock_slurm_profiles_config(self):
        """Mock slurm profiles.cfg content for upgrade/repair testing."""
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
python_path = python3
"""

    @patch("blackfish.cli.profile.TigerFlowClient")
    @patch("blackfish.cli.profile.SSHRunner")
    def test_upgrade_slurm_profile_success(
        self,
        mock_ssh_runner_cls,
        mock_tf_client_cls,
        cli_runner,
        temp_home_dir,
        mock_slurm_profiles_config,
    ):
        """Test successful upgrade of a Slurm profile."""
        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        mock_tf_client = mock_tf_client_cls.return_value
        mock_tf_client.upgrade = lambda **kwargs: None  # sync mock

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            with open(profiles_path, "w") as f:
                f.write(mock_slurm_profiles_config)

            # Mock asyncio.run to execute the async function
            with patch("blackfish.cli.profile.asyncio.run") as mock_asyncio_run:
                result = cli_runner.invoke(
                    main, ["profile", "upgrade", "--name", "slurm-test"]
                )

                assert result.exit_code == 0
                # Spinner shows checkmark on success
                assert "✔" in result.output or result.exit_code == 0
                mock_asyncio_run.assert_called_once()

    def test_upgrade_profile_not_found(
        self, cli_runner, temp_home_dir, mock_slurm_profiles_config
    ):
        """Test upgrading a profile that doesn't exist."""
        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            with open(profiles_path, "w") as f:
                f.write(mock_slurm_profiles_config)

            result = cli_runner.invoke(
                main, ["profile", "upgrade", "--name", "nonexistent"]
            )

            assert result.exit_code == 1
            assert "Profile nonexistent not found" in result.output

    def test_upgrade_local_profile_not_allowed(
        self, cli_runner, temp_home_dir, mock_slurm_profiles_config
    ):
        """Test that upgrading a local profile is not allowed."""
        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            with open(profiles_path, "w") as f:
                f.write(mock_slurm_profiles_config)

            result = cli_runner.invoke(
                main, ["profile", "upgrade", "--name", "default"]
            )

            assert result.exit_code == 1
            assert "only supported on Slurm profiles" in result.output

    @patch("blackfish.cli.profile.TigerFlowClient")
    @patch("blackfish.cli.profile.SSHRunner")
    def test_upgrade_with_custom_specs(
        self,
        mock_ssh_runner_cls,
        mock_tf_client_cls,
        cli_runner,
        temp_home_dir,
        mock_slurm_profiles_config,
    ):
        """Test upgrade with custom package specs."""
        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            with open(profiles_path, "w") as f:
                f.write(mock_slurm_profiles_config)

            with patch("blackfish.cli.profile.asyncio.run") as mock_asyncio_run:
                result = cli_runner.invoke(
                    main,
                    [
                        "profile",
                        "upgrade",
                        "--name",
                        "slurm-test",
                        "--tigerflow-spec",
                        "git+https://github.com/org/tigerflow@branch",
                        "--tigerflow-ml-spec",
                        "git+https://github.com/org/tigerflow-ml@branch",
                    ],
                )

                assert result.exit_code == 0
                mock_asyncio_run.assert_called_once()


class TestProfileRepair:
    """Test profile repair command."""

    @pytest.fixture
    def mock_slurm_profiles_config(self):
        """Mock slurm profiles.cfg content for upgrade/repair testing."""
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
python_path = python3
"""

    def test_repair_slurm_profile_success(
        self,
        cli_runner,
        temp_home_dir,
        mock_slurm_profiles_config,
    ):
        """Test successful repair of a Slurm profile."""
        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            with open(profiles_path, "w") as f:
                f.write(mock_slurm_profiles_config)

            with patch("blackfish.cli.profile._repair_profile") as mock_repair:
                mock_repair.return_value = True
                result = cli_runner.invoke(
                    main, ["profile", "repair", "--name", "slurm-test", "--force"]
                )

                assert result.exit_code == 0
                mock_repair.assert_called_once()

    def test_repair_profile_not_found(
        self, cli_runner, temp_home_dir, mock_slurm_profiles_config
    ):
        """Test repairing a profile that doesn't exist."""
        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            with open(profiles_path, "w") as f:
                f.write(mock_slurm_profiles_config)

            result = cli_runner.invoke(
                main, ["profile", "repair", "--name", "nonexistent"]
            )

            assert result.exit_code == 1
            assert "Profile nonexistent not found" in result.output

    def test_repair_local_profile_not_allowed(
        self, cli_runner, temp_home_dir, mock_slurm_profiles_config
    ):
        """Test that repairing a local profile is not allowed."""
        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            with open(profiles_path, "w") as f:
                f.write(mock_slurm_profiles_config)

            result = cli_runner.invoke(main, ["profile", "repair", "--name", "default"])

            assert result.exit_code == 1
            assert "only supported on Slurm profiles" in result.output

    def test_repair_with_custom_specs(
        self,
        cli_runner,
        temp_home_dir,
        mock_slurm_profiles_config,
    ):
        """Test repair with custom package specs."""
        profiles_path = os.path.join(temp_home_dir, "profiles.cfg")

        with patch("blackfish.cli.__main__.config") as mock_config:
            mock_config.HOME_DIR = temp_home_dir

            with open(profiles_path, "w") as f:
                f.write(mock_slurm_profiles_config)

            with patch("blackfish.cli.profile._repair_profile") as mock_repair:
                mock_repair.return_value = True
                result = cli_runner.invoke(
                    main,
                    [
                        "profile",
                        "repair",
                        "--name",
                        "slurm-test",
                        "--force",
                        "--tigerflow-spec",
                        "git+https://github.com/org/tigerflow@branch",
                        "--tigerflow-ml-spec",
                        "git+https://github.com/org/tigerflow-ml@branch",
                    ],
                )

                assert result.exit_code == 0
                mock_repair.assert_called_once()
                # Verify custom specs were passed
                call_kwargs = mock_repair.call_args.kwargs
                assert (
                    call_kwargs["tigerflow_spec"]
                    == "git+https://github.com/org/tigerflow@branch"
                )
                assert (
                    call_kwargs["tigerflow_ml_spec"]
                    == "git+https://github.com/org/tigerflow-ml@branch"
                )
