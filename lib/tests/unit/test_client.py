"""Tests for TigerFlow client and command runners."""

import asyncio
import json
from unittest import mock

import pytest

from blackfish.server.config import ContainerProvider
from blackfish.server.images import DEFAULT_IMAGES
from blackfish.server.jobs.client import (
    LocalRunner,
    SSHRunner,
    TigerFlowClient,
    TigerFlowError,
    TigerFlowVersions,
)


pytestmark = pytest.mark.anyio


IMAGE = DEFAULT_IMAGES["tigerflow_ml"]
SIF_PATH = f"/cache/images/{IMAGE.sif}"


def make_client(
    runner, cache_dir: str = "/cache", provider=ContainerProvider.Apptainer
):
    """Build a TigerFlowClient wired to the tigerflow-ml image."""
    return TigerFlowClient(
        runner=runner,
        home_dir="/home/user",
        image=IMAGE,
        provider=provider,
        cache_dir=cache_dir,
    )


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
            ("missing", "image not found"),
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
    """Tests for TigerFlowClient basics and command construction."""

    def test_host_property_delegates_to_runner(self) -> None:
        """Host property should return the runner's host."""
        runner = MockRunner("my-cluster")
        client = make_client(runner)
        assert client.host == "my-cluster"

    def test_sif_path_uses_cache_dir(self) -> None:
        """The SIF path lives under {cache_dir}/images/{image.sif}."""
        runner = MockRunner()
        client = make_client(runner, cache_dir="/cache")
        assert client.sif_path == SIF_PATH

    def test_tigerflow_cmd_apptainer(self) -> None:
        """Apptainer command should exec the SIF with the PYTHONNOUSERSITE env."""
        runner = MockRunner()
        client = make_client(runner, provider=ContainerProvider.Apptainer)

        cmd = client._tigerflow_cmd("report /out --json", binds=["/out"])

        assert "apptainer exec" in cmd
        assert "--env PYTHONNOUSERSITE=1" in cmd
        assert SIF_PATH in cmd
        assert "--bind /out" in cmd
        assert cmd.rstrip().endswith("tigerflow report /out --json")

    def test_tigerflow_cmd_apptainer_no_binds(self) -> None:
        """Apptainer command without binds omits the --bind flag."""
        runner = MockRunner()
        client = make_client(runner, provider=ContainerProvider.Apptainer)

        cmd = client._tigerflow_cmd("tasks list --json")

        assert "apptainer exec" in cmd
        assert "--bind" not in cmd
        assert SIF_PATH in cmd

    def test_tigerflow_cmd_docker(self) -> None:
        """Docker command should run the docker_ref image, binding paths with -v."""
        runner = MockRunner()
        client = make_client(runner, provider=ContainerProvider.Docker)

        cmd = client._tigerflow_cmd("report /out --json", binds=["/out"])

        assert "docker run --rm" in cmd
        assert "-v /out:/out" in cmd
        assert IMAGE.docker_ref in cmd
        assert cmd.rstrip().endswith("tigerflow report /out --json")


class TestTigerFlowClientCheckHealth:
    """Tests for TigerFlowClient.check_health()."""

    async def test_check_health_returns_versions_when_image_present(self) -> None:
        """check_health returns versions when the SIF exists and versions read."""
        runner = MockRunner()
        runner.set_responses(
            [
                (0, b"", b""),  # test -f sif (present)
                (0, b"0.1.1\n", b""),  # tigerflow version
                (0, b"0.1.1\n", b""),  # tigerflow-ml version
            ]
        )
        client = make_client(runner)

        versions = await client.check_health()

        assert isinstance(versions, TigerFlowVersions)
        assert versions.tigerflow == "0.1.1"
        assert versions.tigerflow_ml == "0.1.1"

    async def test_check_health_probes_sif_existence(self) -> None:
        """The health check should probe the SIF path via a `test -f`."""
        runner = MockRunner()
        runner.set_responses(
            [
                (0, b"", b""),
                (0, b"0.1.1\n", b""),
                (0, b"0.1.1\n", b""),
            ]
        )
        client = make_client(runner)

        await client.check_health()

        probe = runner.commands[0]
        assert "test -f" in probe
        assert SIF_PATH in probe

    async def test_check_health_raises_missing_when_sif_absent(self) -> None:
        """check_health raises a 'missing' error when the SIF is not present."""
        runner = MockRunner()
        runner.set_response(1, b"", b"")  # test -f fails
        client = make_client(runner)

        with pytest.raises(TigerFlowError) as exc_info:
            await client.check_health()

        assert exc_info.value.error_type == "missing"
        assert "image not found" in exc_info.value.user_message()


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
        client = make_client(runner)

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
        client = make_client(runner)

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
        client = make_client(runner)

        with pytest.raises(TigerFlowError) as exc_info:
            await client.check_capabilities()

        assert exc_info.value.error_type == "unsupported"
        assert "report" in str(exc_info.value.details).lower()

    async def test_check_capabilities_ignores_other_errors(self) -> None:
        """check_capabilities should not raise for non-'unknown command' errors."""
        runner = MockRunner()
        runner.set_responses(
            [
                (1, b"", b"Error: connection refused"),  # fails for other reason
            ]
        )
        client = make_client(runner)

        # Should not raise - error is not "unknown command"
        await client.check_capabilities()


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
        client = make_client(runner)

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
        runner.set_response(0, json.dumps({"unexpected": "format"}).encode())
        client = make_client(runner)

        with pytest.raises(TigerFlowError) as exc_info:
            await client.report("/data/out")

        assert exc_info.value.error_type == "report"

    async def test_report_raises_error_on_invalid_json(self) -> None:
        """report should raise error when response is not valid JSON."""
        runner = MockRunner()
        runner.set_response(0, b"not json")
        client = make_client(runner)

        with pytest.raises(TigerFlowError) as exc_info:
            await client.report("/data/out")

        assert exc_info.value.error_type == "report"

    async def test_report_builds_container_command_with_sif_and_flags(self) -> None:
        """report should run `tigerflow report` in the image, binding the output dir."""
        runner = MockRunner()
        report_data = self._make_report_json(
            running=False, pid=None, finished=0, in_progress=0, staged=0, errored=0
        )
        runner.set_response(0, json.dumps(report_data).encode())
        client = make_client(runner)

        await client.report("/data/output")

        cmd = runner.commands[0]
        assert SIF_PATH in cmd
        assert "tigerflow report" in cmd
        assert "/data/output" in cmd
        assert "--json" in cmd
        assert "--bind /data/output" in cmd

    async def test_report_raises_error_on_command_failure(self) -> None:
        """report should raise error when tigerflow command fails."""
        runner = MockRunner()
        runner.set_response(1, b"", b"Failed to read progress")
        client = make_client(runner)

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
        client = make_client(runner)

        report = await client.report("/data/out")

        assert report.status.running is False
        assert report.progress.pipeline.finished == 10
        assert report.progress.pipeline.errored == 2


class TestTigerFlowClientStop:
    """Tests for TigerFlowClient.stop()."""

    async def test_stop_builds_container_command_with_output_dir(self) -> None:
        """stop should run `tigerflow stop` in the image, binding the output dir."""
        runner = MockRunner()
        runner.set_response(0, b"")
        client = make_client(runner)

        await client.stop("/data/out")

        cmd = runner.commands[0]
        assert SIF_PATH in cmd
        assert "tigerflow stop" in cmd
        assert "/data/out" in cmd
        assert "--bind /data/out" in cmd

    async def test_stop_raises_stop_error_on_failure(self) -> None:
        """stop should raise stop error when command fails."""
        runner = MockRunner()
        runner.set_response(1, b"", b"Error: Permission denied to stop pipeline")
        client = make_client(runner)

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
        client = make_client(runner)

        tasks = await client.list_tasks()

        assert len(tasks) == 2
        assert tasks[0]["name"] == "transcribe"
        assert tasks[1]["name"] == "translate"

    async def test_list_tasks_builds_container_command(self) -> None:
        """list_tasks should run `tigerflow tasks list --json` in the image."""
        runner = MockRunner()
        runner.set_response(0, b"[]")
        client = make_client(runner)

        await client.list_tasks()

        cmd = runner.commands[0]
        assert SIF_PATH in cmd
        assert "tigerflow tasks list --json" in cmd

    async def test_list_tasks_raises_on_command_failure(self) -> None:
        """list_tasks should raise error when command fails."""
        runner = MockRunner()
        runner.set_response(1, b"", b"Command not found")
        client = make_client(runner)

        with pytest.raises(TigerFlowError) as exc_info:
            await client.list_tasks()

        assert exc_info.value.error_type == "command"

    async def test_list_tasks_raises_on_invalid_json(self) -> None:
        """list_tasks should raise error when response is not valid JSON."""
        runner = MockRunner()
        runner.set_response(0, b"not json")
        client = make_client(runner)

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
        client = make_client(runner)

        task = await client.get_task_info("transcribe")

        assert task["name"] == "transcribe"
        assert "params" in task

    async def test_get_task_info_builds_container_command(self) -> None:
        """get_task_info should run `tigerflow tasks info <task> --json` in the image."""
        runner = MockRunner()
        runner.set_response(0, b"{}")
        client = make_client(runner)

        await client.get_task_info("transcribe")

        cmd = runner.commands[0]
        assert SIF_PATH in cmd
        assert "tigerflow tasks info transcribe --json" in cmd

    async def test_get_task_info_raises_on_command_failure(self) -> None:
        """get_task_info should raise error when command fails."""
        runner = MockRunner()
        runner.set_response(1, b"", b"Task not found")
        client = make_client(runner)

        with pytest.raises(TigerFlowError) as exc_info:
            await client.get_task_info("nonexistent")

        assert exc_info.value.error_type == "command"

    async def test_get_task_info_raises_on_invalid_json(self) -> None:
        """get_task_info should raise error when response is not valid JSON."""
        runner = MockRunner()
        runner.set_response(0, b"not json")
        client = make_client(runner)

        with pytest.raises(TigerFlowError) as exc_info:
            await client.get_task_info("transcribe")

        assert exc_info.value.error_type == "command"
        assert "Invalid JSON" in str(exc_info.value.details)
