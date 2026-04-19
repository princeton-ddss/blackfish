"""Tests for TigerFlow client and command runners."""

import asyncio
import json
from unittest import mock

import pytest

from blackfish.server.jobs.client import (
    LocalRunner,
    SSHRunner,
    TigerFlowClient,
    TigerFlowError,
    TigerFlowVersions,
    MIN_TIGERFLOW_VERSION,
    MIN_TIGERFLOW_ML_VERSION,
    VENV_PATH,
)


pytestmark = pytest.mark.anyio


class TestTigerFlowError:
    """Tests for TigerFlowError exception."""

    def test_user_message_includes_host(self) -> None:
        """Error message should include the host where error occurred."""
        error = TigerFlowError("ssh", "cluster.example.com")
        assert "cluster.example.com" in error.user_message()

    def test_user_message_includes_details_when_provided(self) -> None:
        """Error message should include details after colon."""
        error = TigerFlowError("command", "host", "exit code 1")
        message = error.user_message()
        assert "exit code 1" in message

    def test_user_message_omits_details_when_none(self) -> None:
        """Error message should not have parentheses when no details."""
        error = TigerFlowError("ssh", "host")
        message = error.user_message()
        assert "(" not in message

    @pytest.mark.parametrize(
        "error_type,expected_fragment",
        [
            ("ssh", "SSH connection"),
            ("timeout", "timed out"),
            ("command", "Command failed"),
            ("setup", "set up TigerFlow"),
            ("install", "install TigerFlow"),
            ("version", "too old"),
            ("missing", "not installed"),
            ("run", "start TigerFlow job"),
            ("report", "get TigerFlow job report"),
            ("stop", "stop TigerFlow job"),
            ("unsupported", "features not available"),
        ],
    )
    def test_user_message_describes_error_type(
        self, error_type: str, expected_fragment: str
    ) -> None:
        """Each error type should produce a descriptive message."""
        error = TigerFlowError(error_type, "host")
        assert expected_fragment in error.user_message()

    def test_user_message_handles_unknown_error_type(self) -> None:
        """Unknown error types should get a generic message."""
        error = TigerFlowError("unknown_type", "host")
        assert "TigerFlow operation failed" in error.user_message()


class TestSSHRunner:
    """Tests for SSHRunner command execution."""

    def test_host_property_returns_configured_host(self) -> None:
        """Host property should return the host passed to constructor."""
        runner = SSHRunner("user", "myhost.example.com")
        assert runner.host == "myhost.example.com"

    async def test_run_executes_ssh_command_with_correct_arguments(self) -> None:
        """Run should invoke ssh with user@host and the command."""
        runner = SSHRunner("testuser", "testhost")

        with mock.patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = mock.AsyncMock()
            mock_proc.communicate.return_value = (b"output", b"")
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            await runner.run("echo hello")

            mock_exec.assert_called_once_with(
                "ssh",
                "testuser@testhost",
                "echo hello",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

    async def test_run_returns_stdout_and_stderr_on_success(self) -> None:
        """Run should return command output when successful."""
        runner = SSHRunner("user", "host")

        with mock.patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = mock.AsyncMock()
            mock_proc.communicate.return_value = (b"stdout data", b"stderr data")
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            returncode, stdout, stderr = await runner.run("cmd")

            assert returncode == 0
            assert stdout == b"stdout data"
            assert stderr == b"stderr data"

    async def test_run_returns_nonzero_exit_code_for_command_failure(self) -> None:
        """Run should return non-zero exit code when remote command fails."""
        runner = SSHRunner("user", "host")

        with mock.patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = mock.AsyncMock()
            mock_proc.communicate.return_value = (b"", b"command not found")
            mock_proc.returncode = 127
            mock_exec.return_value = mock_proc

            returncode, stdout, stderr = await runner.run("nonexistent")

            assert returncode == 127
            assert stderr == b"command not found"

    async def test_run_raises_ssh_error_on_exit_code_255(self) -> None:
        """Run should raise TigerFlowError with ssh type when exit code is 255."""
        runner = SSHRunner("user", "unreachable")

        with mock.patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = mock.AsyncMock()
            mock_proc.communicate.return_value = (b"", b"Connection refused")
            mock_proc.returncode = 255
            mock_exec.return_value = mock_proc

            with pytest.raises(TigerFlowError) as exc_info:
                await runner.run("cmd")

            assert exc_info.value.error_type == "ssh"
            assert exc_info.value.host == "unreachable"
            assert "Connection refused" in str(exc_info.value.details)

    async def test_run_raises_timeout_error_when_command_hangs(self) -> None:
        """Run should raise TigerFlowError with timeout type when command exceeds timeout."""
        runner = SSHRunner("user", "slow-host", timeout=0.1)

        with mock.patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = mock.AsyncMock()
            # Simulate a hanging command
            mock_proc.communicate.side_effect = asyncio.TimeoutError()
            mock_proc.kill = mock.Mock()
            mock_proc.wait = mock.AsyncMock()
            mock_exec.return_value = mock_proc

            with mock.patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
                with pytest.raises(TigerFlowError) as exc_info:
                    await runner.run("sleep 1000")

            assert exc_info.value.error_type == "timeout"
            assert exc_info.value.host == "slow-host"
            mock_proc.kill.assert_called_once()

    async def test_run_uses_default_timeout_of_120_seconds(self) -> None:
        """Run should use 120 second timeout by default."""
        runner = SSHRunner("user", "host")
        assert runner.timeout == 120


class TestLocalRunner:
    """Tests for LocalRunner command execution."""

    def test_host_property_returns_localhost(self) -> None:
        """Host property should always return 'localhost'."""
        runner = LocalRunner()
        assert runner.host == "localhost"

    async def test_run_executes_shell_command(self) -> None:
        """Run should execute command in a shell."""
        runner = LocalRunner()
        returncode, stdout, stderr = await runner.run("echo hello")

        assert returncode == 0
        assert b"hello" in stdout

    async def test_run_returns_nonzero_exit_code_for_failure(self) -> None:
        """Run should return non-zero exit code when command fails."""
        runner = LocalRunner()
        returncode, stdout, stderr = await runner.run("exit 42")

        assert returncode == 42


class MockRunner:
    """Mock runner for testing TigerFlowClient without actual command execution."""

    def __init__(self, host: str = "testhost"):
        self._host = host
        self.commands: list[str] = []
        self.responses: list[tuple[int, bytes, bytes]] = []
        self._call_index = 0

    @property
    def host(self) -> str:
        return self._host

    def set_response(self, returncode: int, stdout: bytes, stderr: bytes = b"") -> None:
        """Set a single response for the next command."""
        self.responses = [(returncode, stdout, stderr)]
        self._call_index = 0

    def set_responses(self, responses: list[tuple[int, bytes, bytes]]) -> None:
        """Set multiple responses for sequential commands."""
        self.responses = responses
        self._call_index = 0

    async def run(self, command: str) -> tuple[int, bytes, bytes]:
        """Record command and return configured response."""
        self.commands.append(command)
        if self._call_index < len(self.responses):
            response = self.responses[self._call_index]
            self._call_index += 1
            return response
        return (0, b"", b"")


class TestTigerFlowClient:
    """Tests for TigerFlowClient."""

    def test_host_property_delegates_to_runner(self) -> None:
        """Host property should return the runner's host."""
        runner = MockRunner("my-cluster")
        client = TigerFlowClient(runner, "/home/user")
        assert client.host == "my-cluster"

    def test_venv_path_constructed_from_home_dir(self) -> None:
        """venv path should be under home_dir/.blackfish/.venv."""
        runner = MockRunner()
        client = TigerFlowClient(runner, "/home/user")
        assert client._venv_path == f"/home/user/{VENV_PATH}"

    def test_tigerflow_bin_path_in_venv(self) -> None:
        """TigerFlow binary should be in venv bin directory."""
        runner = MockRunner()
        client = TigerFlowClient(runner, "/home/user")
        assert client._tigerflow_bin == f"/home/user/{VENV_PATH}/bin/tigerflow"

    def test_python_path_defaults_to_python3(self) -> None:
        """python_path should default to 'python3'."""
        runner = MockRunner()
        client = TigerFlowClient(runner, "/home/user")
        assert client.python_path == "python3"

    def test_python_path_can_be_customized(self) -> None:
        """python_path should accept custom values."""
        runner = MockRunner()
        client = TigerFlowClient(
            runner, "/home/user", python_path="/usr/bin/python3.11"
        )
        assert client.python_path == "/usr/bin/python3.11"


class TestTigerFlowClientSetup:
    """Tests for TigerFlowClient.setup()."""

    async def test_setup_creates_directory_and_venv(self) -> None:
        """Setup should create home directory and venv."""
        runner = MockRunner()
        runner.set_responses(
            [
                (1, b"", b""),  # venv path check (empty)
                (0, b"", b""),  # mkdir
                (0, b"", b""),  # venv creation
                (0, b"", b""),  # pip upgrade
                (0, b"", b""),  # pip install
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        await client.setup()

        assert runner.commands[1] == "mkdir -p /home/user"
        assert "-m venv" in runner.commands[2]

    async def test_setup_does_not_create_nested_blackfish_directory(self) -> None:
        """Setup should not create a nested .blackfish subdirectory."""
        runner = MockRunner()
        runner.set_responses(
            [
                (1, b"", b""),  # venv path check (empty)
                (0, b"", b""),  # mkdir
                (0, b"", b""),  # venv creation
                (0, b"", b""),  # pip upgrade
                (0, b"", b""),  # pip install
            ]
        )
        client = TigerFlowClient(runner, "/home/user/.blackfish")

        await client.setup()

        assert runner.commands[1] == "mkdir -p /home/user/.blackfish"
        assert "/home/user/.blackfish/.blackfish" not in runner.commands[1]

    async def test_setup_installs_tigerflow_packages(self) -> None:
        """Setup should install tigerflow and tigerflow-ml."""
        runner = MockRunner()
        runner.set_responses(
            [
                (1, b"", b""),  # venv path check (empty)
                (0, b"", b""),  # mkdir
                (0, b"", b""),  # venv creation
                (0, b"", b""),  # pip upgrade
                (0, b"", b""),  # pip install
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        await client.setup()

        install_cmd = runner.commands[4]
        assert "tigerflow" in install_cmd
        assert "tigerflow-ml" in install_cmd

    async def test_setup_uses_configured_python_path(self) -> None:
        """Setup should use the configured python_path for venv creation."""
        runner = MockRunner()
        runner.set_responses(
            [
                (1, b"", b""),  # venv path check (empty)
                (0, b"", b""),  # mkdir
                (0, b"", b""),  # venv creation
                (0, b"", b""),  # pip upgrade
                (0, b"", b""),  # pip install
            ]
        )
        client = TigerFlowClient(
            runner, "/home/user", python_path="/opt/python3.11/bin/python3"
        )

        await client.setup()

        venv_cmd = runner.commands[2]
        assert "/opt/python3.11/bin/python3 -m venv" in venv_cmd

    async def test_setup_uses_venv_pip_not_system_pip(self) -> None:
        """Setup should use pip from the venv, not system pip."""
        runner = MockRunner()
        runner.set_responses(
            [
                (1, b"", b""),  # venv path check (empty)
                (0, b"", b""),  # mkdir
                (0, b"", b""),  # venv creation
                (0, b"", b""),  # pip upgrade
                (0, b"", b""),  # pip install
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        await client.setup()

        pip_upgrade_cmd = runner.commands[3]
        pip_install_cmd = runner.commands[4]
        expected_pip = f"/home/user/{VENV_PATH}/bin/pip"
        assert expected_pip in pip_upgrade_cmd
        assert expected_pip in pip_install_cmd

    async def test_setup_raises_setup_error_when_venv_path_not_empty(self) -> None:
        """Setup should fail fast with a clear message if venv path is occupied."""
        runner = MockRunner()
        runner.set_response(0, b"conda-meta\nbin\n", b"")  # venv path is non-empty
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.setup()

        assert exc_info.value.error_type == "setup"
        details = str(exc_info.value.details)
        assert client._venv_path in details
        assert "already exists" in details
        # Should bail before attempting mkdir or venv creation
        assert len(runner.commands) == 1

    async def test_setup_proceeds_when_venv_path_empty_directory(self) -> None:
        """Setup should proceed if venv path exists but is an empty directory."""
        runner = MockRunner()
        runner.set_responses(
            [
                (0, b"", b""),  # ls returns 0 with empty stdout (empty dir)
                (0, b"", b""),  # mkdir
                (0, b"", b""),  # venv creation
                (0, b"", b""),  # pip upgrade
                (0, b"", b""),  # pip install
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        await client.setup()

        assert "-m venv" in runner.commands[2]

    async def test_setup_raises_setup_error_when_mkdir_fails(self) -> None:
        """Setup should raise setup error if directory creation fails."""
        runner = MockRunner()
        runner.set_responses(
            [
                (1, b"", b""),  # venv path check (empty)
                (1, b"", b"Permission denied"),  # mkdir fails
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.setup()

        assert exc_info.value.error_type == "setup"

    async def test_setup_raises_setup_error_when_venv_creation_fails(self) -> None:
        """Setup should raise setup error if venv creation fails."""
        runner = MockRunner()
        runner.set_responses(
            [
                (1, b"", b""),  # venv path check (empty)
                (0, b"", b""),  # mkdir succeeds
                (1, b"", b"venv module not found"),  # venv fails
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.setup()

        assert exc_info.value.error_type == "setup"
        assert "venv" in str(exc_info.value.details).lower()

    async def test_setup_raises_setup_error_when_python_path_missing(self) -> None:
        """Setup should raise setup error if configured python_path doesn't exist."""
        runner = MockRunner()
        runner.set_responses(
            [
                (1, b"", b""),  # venv path check (empty)
                (0, b"", b""),  # mkdir succeeds
                (127, b"", b"/opt/python3.11/bin/python3: No such file or directory"),
            ]
        )
        client = TigerFlowClient(
            runner, "/home/user", python_path="/opt/python3.11/bin/python3"
        )

        with pytest.raises(TigerFlowError) as exc_info:
            await client.setup()

        assert exc_info.value.error_type == "setup"
        assert "venv" in str(exc_info.value.details).lower()

    async def test_setup_raises_install_error_when_pip_fails(self) -> None:
        """Setup should raise install error if pip install fails."""
        runner = MockRunner()
        runner.set_responses(
            [
                (1, b"", b""),  # venv path check (empty)
                (0, b"", b""),  # mkdir
                (0, b"", b""),  # venv creation
                (0, b"", b""),  # pip upgrade
                (1, b"", b"Could not find package"),  # pip install fails
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.setup()

        assert exc_info.value.error_type == "install"


class TestTigerFlowClientCheckVersion:
    """Tests for TigerFlowClient.check_version()."""

    async def test_check_version_returns_true_when_version_meets_minimum(self) -> None:
        """check_version should return (True, version) when version is sufficient."""
        runner = MockRunner()
        runner.set_response(0, f"tigerflow {MIN_TIGERFLOW_VERSION}".encode())
        client = TigerFlowClient(runner, "/home/user")

        ok, version = await client.check_version()

        assert ok is True
        assert version == MIN_TIGERFLOW_VERSION

    async def test_check_version_returns_false_when_version_too_old(self) -> None:
        """check_version should return (False, version) when version is below minimum."""
        runner = MockRunner()
        runner.set_response(0, b"tigerflow 0.0.1")
        client = TigerFlowClient(runner, "/home/user")

        ok, version = await client.check_version()

        assert ok is False
        assert version == "0.0.1"

    async def test_check_version_returns_none_when_not_installed(self) -> None:
        """check_version should return (False, None) when tigerflow not found."""
        runner = MockRunner()
        runner.set_response(127, b"", b"command not found")
        client = TigerFlowClient(runner, "/home/user")

        ok, version = await client.check_version()

        assert ok is False
        assert version is None

    async def test_check_version_raises_error_when_output_unparseable(self) -> None:
        """check_version should raise error when version can't be parsed."""
        runner = MockRunner()
        runner.set_response(0, b"unexpected output format")
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.check_version()

        assert exc_info.value.error_type == "version"
        assert "parse" in str(exc_info.value.details).lower()


class TestTigerFlowClientUpgrade:
    """Tests for TigerFlowClient.upgrade()."""

    async def test_upgrade_runs_pip_install_upgrade(self) -> None:
        """upgrade should run pip install --upgrade for tigerflow packages."""
        runner = MockRunner()
        # First: pip list --outdated returns tigerflow as outdated
        # Second: pip install --upgrade
        runner.set_responses(
            [
                (0, b'[{"name": "tigerflow", "version": "0.1.0"}]', b""),
                (0, b"Successfully installed", b""),
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        await client.upgrade()

        assert "--outdated" in runner.commands[0]
        assert "--upgrade" in runner.commands[1]
        assert "tigerflow" in runner.commands[1]

    async def test_upgrade_uses_venv_pip(self) -> None:
        """upgrade should use pip from the venv."""
        runner = MockRunner()
        runner.set_responses(
            [
                (0, b'[{"name": "tigerflow", "version": "0.1.0"}]', b""),
                (0, b"Successfully installed", b""),
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        await client.upgrade()

        expected_pip = f"/home/user/{VENV_PATH}/bin/pip"
        assert expected_pip in runner.commands[0]
        assert expected_pip in runner.commands[1]

    async def test_upgrade_raises_install_error_on_failure(self) -> None:
        """upgrade should raise install error if pip upgrade fails."""
        runner = MockRunner()
        runner.set_responses(
            [
                (
                    0,
                    b'[{"name": "tigerflow", "version": "0.1.0"}]',
                    b"",
                ),  # outdated check
                (1, b"", b"Network error"),  # install fails
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.upgrade()

        assert exc_info.value.error_type == "install"

    async def test_upgrade_skips_if_up_to_date(self) -> None:
        """upgrade should skip pip install if packages are up-to-date."""
        runner = MockRunner()
        # Empty list means nothing is outdated
        runner.set_response(0, b"[]")
        client = TigerFlowClient(runner, "/home/user")

        result = await client.upgrade()

        assert len(runner.commands) == 1  # Only the outdated check
        assert "--outdated" in runner.commands[0]
        assert result == "TigerFlow up-to-date."

    async def test_upgrade_uninstalls_first_for_git_tigerflow_spec(self) -> None:
        """upgrade should uninstall then install when tigerflow_spec is a git URL."""
        runner = MockRunner()
        runner.set_responses(
            [
                (0, b"", b""),  # uninstall
                (0, b"Successfully installed", b""),  # install
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        await client.upgrade(tigerflow_spec="git+https://github.com/org/tigerflow@main")

        assert len(runner.commands) == 2
        assert "uninstall -y tigerflow tigerflow-ml" in runner.commands[0]
        assert "git+https://github.com/org/tigerflow@main" in runner.commands[1]

    async def test_upgrade_uninstalls_first_for_git_tigerflow_ml_spec(self) -> None:
        """upgrade should uninstall then install when tigerflow_ml_spec is a git URL."""
        runner = MockRunner()
        runner.set_responses(
            [
                (0, b"", b""),  # uninstall
                (0, b"Successfully installed", b""),  # install
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        await client.upgrade(
            tigerflow_ml_spec="git+https://github.com/org/tigerflow-ml@main"
        )

        assert len(runner.commands) == 2
        assert "uninstall -y tigerflow tigerflow-ml" in runner.commands[0]
        assert "git+https://github.com/org/tigerflow-ml@main" in runner.commands[1]

    async def test_upgrade_no_uninstall_for_pypi_packages(self) -> None:
        """upgrade should use --upgrade without uninstall for regular PyPI packages."""
        runner = MockRunner()
        runner.set_responses(
            [
                (0, b'[{"name": "tigerflow", "version": "0.1.0"}]', b""),  # outdated
                (0, b"Successfully installed", b""),  # install
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        await client.upgrade()

        assert len(runner.commands) == 2
        assert "--outdated" in runner.commands[0]
        assert "--upgrade" in runner.commands[1]
        assert "uninstall" not in runner.commands[1]


class TestTigerFlowClientCleanup:
    """Tests for TigerFlowClient.cleanup()."""

    async def test_cleanup_removes_venv_and_recreates(self) -> None:
        """cleanup should remove venv and call setup."""
        runner = MockRunner()
        runner.set_responses(
            [
                (0, b"", b""),  # rm -rf
                (1, b"", b""),  # venv path check (empty after rm)
                (0, b"", b""),  # mkdir
                (0, b"", b""),  # venv creation
                (0, b"", b""),  # pip upgrade
                (0, b"", b""),  # pip install
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        await client.cleanup()

        assert "rm -rf" in runner.commands[0]
        assert client._venv_path in runner.commands[0]

    async def test_cleanup_raises_setup_error_when_rm_fails(self) -> None:
        """cleanup should raise setup error if removal fails."""
        runner = MockRunner()
        runner.set_response(1, b"", b"Permission denied")
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.cleanup()

        assert exc_info.value.error_type == "setup"


class TestTigerFlowClientCheckHealth:
    """Tests for TigerFlowClient.check_health()."""

    async def test_check_health_returns_versions_when_healthy(self) -> None:
        """check_health should return installed versions when environment is ready."""
        runner = MockRunner()
        runner.set_responses(
            [
                (0, b"", b""),  # test -d venv
                (
                    0,
                    f"Version: {MIN_TIGERFLOW_VERSION}".encode(),
                    b"",
                ),  # pip show tigerflow
                (
                    0,
                    f"Version: {MIN_TIGERFLOW_ML_VERSION}".encode(),
                    b"",
                ),  # pip show tigerflow-ml
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        versions = await client.check_health()

        assert isinstance(versions, TigerFlowVersions)
        assert versions.tigerflow == MIN_TIGERFLOW_VERSION
        assert versions.tigerflow_ml == MIN_TIGERFLOW_ML_VERSION

    async def test_check_health_raises_missing_when_venv_not_found(self) -> None:
        """check_health should raise missing error when venv doesn't exist."""
        runner = MockRunner()
        runner.set_response(1, b"", b"")  # test -d venv fails
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.check_health()

        assert exc_info.value.error_type == "missing"
        assert "venv" in str(exc_info.value.details).lower()

    async def test_check_health_raises_missing_when_tigerflow_not_installed(
        self,
    ) -> None:
        """check_health should raise missing error when tigerflow not installed."""
        runner = MockRunner()
        runner.set_responses(
            [
                (0, b"", b""),  # test -d venv
                (1, b"", b"Package not found"),  # pip show tigerflow fails
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.check_health()

        assert exc_info.value.error_type == "missing"
        assert "tigerflow" in str(exc_info.value.details).lower()

    async def test_check_health_raises_version_when_tigerflow_outdated(self) -> None:
        """check_health should raise version error when tigerflow version too old."""
        runner = MockRunner()
        runner.set_responses(
            [
                (0, b"", b""),  # test -d venv
                (0, b"Version: 0.0.1", b""),  # pip show tigerflow - outdated
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.check_health()

        assert exc_info.value.error_type == "version"
        assert "tigerflow" in str(exc_info.value.details).lower()

    async def test_check_health_raises_missing_when_tigerflow_ml_not_installed(
        self,
    ) -> None:
        """check_health should raise missing error when tigerflow-ml not installed."""
        runner = MockRunner()
        runner.set_responses(
            [
                (0, b"", b""),  # test -d venv
                (
                    0,
                    f"Version: {MIN_TIGERFLOW_VERSION}".encode(),
                    b"",
                ),  # pip show tigerflow
                (1, b"", b"Package not found"),  # pip show tigerflow-ml fails
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.check_health()

        assert exc_info.value.error_type == "missing"
        assert "tigerflow-ml" in str(exc_info.value.details).lower()

    async def test_check_health_raises_version_when_tigerflow_ml_outdated(self) -> None:
        """check_health should raise version error when tigerflow-ml version too old."""
        runner = MockRunner()
        runner.set_responses(
            [
                (0, b"", b""),  # test -d venv
                (
                    0,
                    f"Version: {MIN_TIGERFLOW_VERSION}".encode(),
                    b"",
                ),  # pip show tigerflow
                (0, b"Version: 0.0.1", b""),  # pip show tigerflow-ml - outdated
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.check_health()

        assert exc_info.value.error_type == "version"
        assert "tigerflow-ml" in str(exc_info.value.details).lower()


class TestTigerFlowClientCheckCapabilities:
    """Tests for TigerFlowClient.check_capabilities()."""

    async def test_check_capabilities_passes_when_all_features_available(self) -> None:
        """check_capabilities should pass when tasks and report commands work."""
        runner = MockRunner()
        runner.set_responses(
            [
                (0, b'[{"name": "transcribe"}]', b""),  # tasks list
                (0, b"Usage: tigerflow report", b""),  # report --help
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        # Should not raise
        await client.check_capabilities()

    async def test_check_capabilities_raises_when_tasks_command_unknown(self) -> None:
        """check_capabilities should raise when tasks command not available."""
        runner = MockRunner()
        runner.set_responses(
            [
                (1, b"", b"Error: unknown command 'tasks'"),  # tasks list fails
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.check_capabilities()

        assert exc_info.value.error_type == "unsupported"
        assert "tasks" in str(exc_info.value.details).lower()

    async def test_check_capabilities_raises_when_report_command_unknown(self) -> None:
        """check_capabilities should raise when report command not available."""
        runner = MockRunner()
        runner.set_responses(
            [
                (0, b'[{"name": "transcribe"}]', b""),  # tasks list succeeds
                (1, b"", b"Error: no such command 'report'"),  # report --help fails
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.check_capabilities()

        assert exc_info.value.error_type == "unsupported"
        assert "report" in str(exc_info.value.details).lower()

    async def test_check_capabilities_ignores_other_errors(self) -> None:
        """check_capabilities should not raise for non-'unknown command' errors."""
        runner = MockRunner()
        runner.set_responses(
            [
                (
                    1,
                    b"",
                    b"Error: connection refused",
                ),  # tasks list fails for other reason
            ]
        )
        client = TigerFlowClient(runner, "/home/user")

        # Should not raise - error is not "unknown command"
        await client.check_capabilities()


class TestTigerFlowClientRun:
    """Tests for TigerFlowClient.run()."""

    async def test_run_writes_config_yaml_to_output_dir(self) -> None:
        """run should write pipeline config as YAML to output_dir/pipeline.yaml."""
        runner = MockRunner()
        runner.set_responses(
            [
                (0, b"", b""),  # mkdir
                (0, b"", b""),  # cat config
                (0, b"", b""),  # tigerflow run
            ]
        )
        client = TigerFlowClient(runner, "/home/user")
        config = {
            "tasks": [{"name": "transcribe", "library": "tigerflow_ml.transcribe"}]
        }

        await client.run(config, "/data/in", "/data/out")

        # Check mkdir was called
        assert "mkdir -p /data/out" in runner.commands[0]
        # Check config was written
        assert "cat > /data/out/pipeline.yaml" in runner.commands[1]
        assert "tasks:" in runner.commands[1]

    async def test_run_builds_command_with_config_and_paths(self) -> None:
        """run should build tigerflow command with config path, input, and output."""
        runner = MockRunner()
        runner.set_responses(
            [
                (0, b"", b""),  # mkdir
                (0, b"", b""),  # cat config
                (0, b"", b""),  # tigerflow run
            ]
        )
        client = TigerFlowClient(runner, "/home/user")
        config = {"tasks": [{"name": "transcribe"}]}

        await client.run(config, "/data/in", "/data/out")

        cmd = runner.commands[2]
        assert "tigerflow" in cmd
        assert "run" in cmd
        assert "/data/out/pipeline.yaml" in cmd
        assert "/data/in" in cmd
        assert "/data/out" in cmd
        assert "--background" in cmd

    async def test_run_includes_idle_timeout(self) -> None:
        """run should include idle-timeout flag with specified value."""
        runner = MockRunner()
        runner.set_responses(
            [
                (0, b"", b""),  # mkdir
                (0, b"", b""),  # cat config
                (0, b"", b""),  # tigerflow run
            ]
        )
        client = TigerFlowClient(runner, "/home/user")
        config = {"tasks": []}

        await client.run(config, "/in", "/out", idle_timeout=30)

        assert "--idle-timeout 30" in runner.commands[2]

    async def test_run_raises_error_when_config_write_fails(self) -> None:
        """run should raise run error when writing config fails."""
        runner = MockRunner()
        runner.set_responses(
            [
                (0, b"", b""),  # mkdir succeeds
                (1, b"", b"Permission denied"),  # cat fails
            ]
        )
        client = TigerFlowClient(runner, "/home/user")
        config = {"tasks": []}

        with pytest.raises(TigerFlowError) as exc_info:
            await client.run(config, "/in", "/out")

        assert exc_info.value.error_type == "run"
        assert "config" in str(exc_info.value.details).lower()

    async def test_run_raises_error_when_tigerflow_fails(self) -> None:
        """run should raise run error when tigerflow command fails."""
        runner = MockRunner()
        runner.set_responses(
            [
                (0, b"", b""),  # mkdir
                (0, b"", b""),  # cat config
                (1, b"", b"Invalid config"),  # tigerflow run fails
            ]
        )
        client = TigerFlowClient(runner, "/home/user")
        config = {"tasks": []}

        with pytest.raises(TigerFlowError) as exc_info:
            await client.run(config, "/in", "/out")

        assert exc_info.value.error_type == "run"


class TestTigerFlowClientReport:
    """Tests for TigerFlowClient.report()."""

    @staticmethod
    def _make_report_json(
        running: bool = True,
        pid: int | None = 12345,
        finished: int = 50,
        in_progress: int = 10,
        staged: int = 40,
        errored: int = 5,
    ) -> dict:
        """Build a valid tigerflow report JSON dict."""
        return {
            "status": {"running": running, "pid": pid},
            "progress": {
                "pipeline": {
                    "finished": finished,
                    "in_progress": in_progress,
                    "staged": staged,
                    "errored": errored,
                },
                "tasks": [
                    {
                        "name": "transcribe",
                        "processed": finished,
                        "staged": staged,
                        "failed": errored,
                    },
                ],
            },
            "metrics": {
                "transcribe": {
                    "count": finished,
                    "avg_ms": 1000.0,
                    "min_ms": 500.0,
                    "max_ms": 1500.0,
                    "durations": [1000.0],
                    "files": [
                        {
                            "file": "audio_001.mp3",
                            "started_at": "2026-04-03T10:00:00+00:00",
                            "finished_at": "2026-04-03T10:00:01+00:00",
                            "duration_ms": 1000.0,
                            "status": "success",
                        },
                    ],
                },
            },
            "errors": {},
        }

    async def test_report_parses_valid_response(self) -> None:
        """report should parse valid tigerflow JSON response."""
        runner = MockRunner()
        report_data = self._make_report_json()
        runner.set_response(0, json.dumps(report_data).encode())
        client = TigerFlowClient(runner, "/home/user")

        report = await client.report("/data/out")

        assert report.status.pid == 12345
        assert report.status.running is True
        assert report.progress.pipeline.finished == 50
        assert report.progress.pipeline.in_progress == 10
        assert report.progress.pipeline.staged == 40
        assert report.progress.pipeline.errored == 5
        assert len(report.progress.tasks) == 1
        assert report.progress.tasks[0].name == "transcribe"
        assert "transcribe" in report.metrics
        assert len(report.metrics["transcribe"].files) == 1

    async def test_report_raises_error_when_format_changes(self) -> None:
        """report should raise error if tigerflow changes its response format."""
        runner = MockRunner()
        runner.set_response(
            0,
            json.dumps({"unexpected": "format"}).encode(),
        )
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.report("/data/out")

        assert exc_info.value.error_type == "report"

    async def test_report_raises_error_on_invalid_json(self) -> None:
        """report should raise error when response is not valid JSON."""
        runner = MockRunner()
        runner.set_response(0, b"not json")
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.report("/data/out")

        assert exc_info.value.error_type == "report"

    async def test_report_builds_command_with_output_dir_and_json_flag(self) -> None:
        """report should build command with output_dir and --json flag."""
        runner = MockRunner()
        report_data = self._make_report_json(
            running=False, pid=None, finished=0, in_progress=0, staged=0, errored=0
        )
        runner.set_response(0, json.dumps(report_data).encode())
        client = TigerFlowClient(runner, "/home/user")

        await client.report("/data/output")

        cmd = runner.commands[0]
        assert "report" in cmd
        assert "/data/output" in cmd
        assert "--json" in cmd

    async def test_report_raises_error_on_command_failure(self) -> None:
        """report should raise error when tigerflow command fails (e.g. invalid directory)."""
        runner = MockRunner()
        runner.set_response(1, b"", b"Failed to read progress")
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.report("/data/out")

        assert exc_info.value.error_type == "command"

    async def test_report_returns_stopped_pipeline(self) -> None:
        """report should return stopped pipeline data (exit code 0)."""
        runner = MockRunner()
        report_data = self._make_report_json(
            running=False, pid=None, finished=10, in_progress=0, staged=0, errored=2
        )
        runner.set_response(0, json.dumps(report_data).encode())
        client = TigerFlowClient(runner, "/home/user")

        report = await client.report("/data/out")

        assert report.status.running is False
        assert report.progress.pipeline.finished == 10
        assert report.progress.pipeline.errored == 2


class TestTigerFlowClientStop:
    """Tests for TigerFlowClient.stop()."""

    async def test_stop_builds_command_with_output_dir(self) -> None:
        """stop should build command with output directory path."""
        runner = MockRunner()
        runner.set_response(0, b"")
        client = TigerFlowClient(runner, "/home/user")

        await client.stop("/data/out")

        cmd = runner.commands[0]
        assert "tigerflow" in cmd
        assert "stop" in cmd
        assert "/data/out" in cmd

    async def test_stop_raises_stop_error_on_failure(self) -> None:
        """stop should raise stop error when command fails."""
        runner = MockRunner()
        runner.set_response(1, b"", b"Error: Permission denied to stop pipeline")
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.stop("/data/out")

        assert exc_info.value.error_type == "stop"


class TestTigerFlowClientListTasks:
    """Tests for TigerFlowClient.list_tasks()."""

    async def test_list_tasks_returns_parsed_json(self) -> None:
        """list_tasks should return parsed JSON list of tasks."""
        runner = MockRunner()
        tasks_json = json.dumps(
            [
                {"name": "transcribe", "description": "Transcribe audio"},
                {"name": "translate", "description": "Translate text"},
            ]
        )
        runner.set_response(0, tasks_json.encode())
        client = TigerFlowClient(runner, "/home/user")

        tasks = await client.list_tasks()

        assert len(tasks) == 2
        assert tasks[0]["name"] == "transcribe"
        assert tasks[1]["name"] == "translate"

    async def test_list_tasks_builds_correct_command(self) -> None:
        """list_tasks should run tigerflow tasks list --json."""
        runner = MockRunner()
        runner.set_response(0, b"[]")
        client = TigerFlowClient(runner, "/home/user")

        await client.list_tasks()

        cmd = runner.commands[0]
        assert "tigerflow" in cmd
        assert "tasks" in cmd
        assert "list" in cmd
        assert "--json" in cmd

    async def test_list_tasks_raises_on_command_failure(self) -> None:
        """list_tasks should raise error when command fails."""
        runner = MockRunner()
        runner.set_response(1, b"", b"Command not found")
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.list_tasks()

        assert exc_info.value.error_type == "command"

    async def test_list_tasks_raises_on_invalid_json(self) -> None:
        """list_tasks should raise error when response is not valid JSON."""
        runner = MockRunner()
        runner.set_response(0, b"not json")
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.list_tasks()

        assert exc_info.value.error_type == "command"
        assert "Invalid JSON" in str(exc_info.value.details)


class TestTigerFlowClientGetTaskInfo:
    """Tests for TigerFlowClient.get_task_info()."""

    async def test_get_task_info_returns_parsed_json(self) -> None:
        """get_task_info should return parsed JSON task details."""
        runner = MockRunner()
        task_json = json.dumps(
            {
                "name": "transcribe",
                "description": "Transcribe audio files",
                "params": {"language": {"type": "string", "default": "en"}},
            }
        )
        runner.set_response(0, task_json.encode())
        client = TigerFlowClient(runner, "/home/user")

        task = await client.get_task_info("transcribe")

        assert task["name"] == "transcribe"
        assert "params" in task

    async def test_get_task_info_builds_correct_command(self) -> None:
        """get_task_info should run tigerflow tasks info <task> --json."""
        runner = MockRunner()
        runner.set_response(0, b"{}")
        client = TigerFlowClient(runner, "/home/user")

        await client.get_task_info("transcribe")

        cmd = runner.commands[0]
        assert "tigerflow" in cmd
        assert "tasks" in cmd
        assert "info" in cmd
        assert "transcribe" in cmd
        assert "--json" in cmd

    async def test_get_task_info_raises_on_command_failure(self) -> None:
        """get_task_info should raise error when command fails."""
        runner = MockRunner()
        runner.set_response(1, b"", b"Task not found")
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.get_task_info("nonexistent")

        assert exc_info.value.error_type == "command"

    async def test_get_task_info_raises_on_invalid_json(self) -> None:
        """get_task_info should raise error when response is not valid JSON."""
        runner = MockRunner()
        runner.set_response(0, b"not json")
        client = TigerFlowClient(runner, "/home/user")

        with pytest.raises(TigerFlowError) as exc_info:
            await client.get_task_info("transcribe")

        assert exc_info.value.error_type == "command"
        assert "Invalid JSON" in str(exc_info.value.details)
