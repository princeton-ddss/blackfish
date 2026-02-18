"""Unit tests for BatchJob orchestration logic."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

from blackfish.server.jobs.base import (
    BatchJob,
    BatchJobStatus,
    create_tigerflow_client,
    create_tigerflow_client_for_profile,
)
from blackfish.server.jobs.client import (
    TigerFlowClient,
    TigerFlowStatus,
    TigerFlowError,
    TigerFlowVersions,
)
from blackfish.server.jobs.tasks import (
    is_supported_task,
    get_task_library,
    build_pipeline_config,
)


pytestmark = pytest.mark.anyio


def create_test_batch_job(**kwargs) -> BatchJob:
    """Create a test batch job with default values."""
    defaults = {
        "id": UUID("2a7a8e62-40cc-4240-a825-463e5b11a81f"),
        "name": "test-job",
        "task": "transcribe",
        "repo_id": "openai/whisper-large-v3",
        "input_dir": "/data/input",
        "output_dir": "/data/output",
        "input_ext": ".wav",
        "output_ext": ".json",
        "profile": "default",
        "host": "localhost",
    }
    defaults.update(kwargs)
    return BatchJob(**defaults)


def create_mock_client() -> AsyncMock:
    """Create a mock TigerFlowClient."""
    return AsyncMock(spec=TigerFlowClient)


class TestBatchJobStart:
    """Tests for BatchJob.start()."""

    async def test_start_calls_check_health(self) -> None:
        """start should check tigerflow health before running."""
        job = create_test_batch_job()
        client = create_mock_client()
        client.check_health.return_value = TigerFlowVersions(
            tigerflow="0.1.0", tigerflow_ml="0.1.0"
        )

        await job.start(client)

        client.check_health.assert_called_once()

    async def test_start_stores_versions_for_reproducibility(self) -> None:
        """start should store tigerflow versions on the job."""
        job = create_test_batch_job()
        client = create_mock_client()
        client.check_health.return_value = TigerFlowVersions(
            tigerflow="0.2.0", tigerflow_ml="0.3.0"
        )

        await job.start(client)

        assert job.tigerflow_version == "0.2.0"
        assert job.tigerflow_ml_version == "0.3.0"

    async def test_start_builds_config_with_repo_id_in_params(self) -> None:
        """start should include repo_id as model in config params."""
        job = create_test_batch_job(repo_id="openai/whisper-large-v3")
        client = create_mock_client()
        client.check_health.return_value = TigerFlowVersions(
            tigerflow="0.1.0", tigerflow_ml="0.1.0"
        )

        await job.start(client)

        call_args = client.run.call_args
        config = call_args.kwargs["config"]
        assert config["tasks"][0]["params"]["model"] == "openai/whisper-large-v3"

    async def test_start_includes_revision_in_params(self) -> None:
        """start should include revision in config params when set."""
        job = create_test_batch_job(revision="main")
        client = create_mock_client()
        client.check_health.return_value = TigerFlowVersions(
            tigerflow="0.1.0", tigerflow_ml="0.1.0"
        )

        await job.start(client)

        call_args = client.run.call_args
        config = call_args.kwargs["config"]
        assert config["tasks"][0]["params"]["revision"] == "main"

    async def test_start_merges_user_params(self) -> None:
        """start should merge user params with model/revision."""
        job = create_test_batch_job(params={"language": "en", "beam_size": 5})
        client = create_mock_client()
        client.check_health.return_value = TigerFlowVersions(
            tigerflow="0.1.0", tigerflow_ml="0.1.0"
        )

        await job.start(client)

        call_args = client.run.call_args
        config = call_args.kwargs["config"]
        params = config["tasks"][0]["params"]
        assert params["language"] == "en"
        assert params["beam_size"] == 5
        assert params["model"] == "openai/whisper-large-v3"

    async def test_start_sets_status_to_running(self) -> None:
        """start should set status to RUNNING on success."""
        job = create_test_batch_job()
        client = create_mock_client()
        client.check_health.return_value = TigerFlowVersions(
            tigerflow="0.1.0", tigerflow_ml="0.1.0"
        )

        await job.start(client)

        assert job.status == BatchJobStatus.RUNNING

    async def test_start_propagates_tigerflow_error(self) -> None:
        """start should propagate TigerFlowError from client."""
        job = create_test_batch_job()
        client = create_mock_client()
        client.check_health.return_value = TigerFlowVersions(
            tigerflow="0.1.0", tigerflow_ml="0.1.0"
        )
        client.run.side_effect = TigerFlowError("run", "host", "failed")

        with pytest.raises(TigerFlowError):
            await job.start(client)


class TestBatchJobUpdate:
    """Tests for BatchJob.update()."""

    async def test_update_sets_current_status_when_running(self) -> None:
        """update should set status to RUNNING when tigerflow reports running."""
        job = create_test_batch_job(status=BatchJobStatus.RUNNING)
        client = create_mock_client()
        client.status.return_value = TigerFlowStatus(
            pid=12345,
            running=True,
            staged=10,
            finished=5,
            failed=0,
            tasks=[],
        )

        result = await job.update(client)

        assert result == BatchJobStatus.RUNNING
        assert job.staged == 10
        assert job.finished == 5
        assert job.errored == 0
        assert job.pid == "12345"

    async def test_update_sets_current_status_when_stopped(self) -> None:
        """update should set status to STOPPED when tigerflow reports not running."""
        job = create_test_batch_job(status=BatchJobStatus.RUNNING)
        client = create_mock_client()
        client.status.return_value = TigerFlowStatus(
            pid=None,
            running=False,
            staged=10,
            finished=5,
            failed=5,
            tasks=[],
        )

        result = await job.update(client)

        assert result == BatchJobStatus.STOPPED
        assert job.staged == 10
        assert job.finished == 5
        assert job.errored == 5

    async def test_update_propagates_tigerflow_error(self) -> None:
        """update should propagate TigerFlowError from client."""
        job = create_test_batch_job(status=BatchJobStatus.RUNNING)
        client = create_mock_client()
        client.status.side_effect = TigerFlowError("status", "host", "failed")

        with pytest.raises(TigerFlowError):
            await job.update(client)


class TestBatchJobStop:
    """Tests for BatchJob.stop()."""

    async def test_stop_skips_when_already_stopped(self) -> None:
        """stop should skip client call when already stopped."""
        job = create_test_batch_job(status=BatchJobStatus.STOPPED)
        client = create_mock_client()

        await job.stop(client)

        client.stop.assert_not_called()

    async def test_stop_calls_client_stop(self) -> None:
        """stop should call client.stop with output_dir."""
        job = create_test_batch_job(status=BatchJobStatus.RUNNING)
        client = create_mock_client()

        await job.stop(client)

        client.stop.assert_called_once_with("/data/output")

    async def test_stop_propagates_tigerflow_error(self) -> None:
        """stop should propagate TigerFlowError from client."""
        job = create_test_batch_job()
        client = create_mock_client()
        client.stop.side_effect = TigerFlowError("stop", "host", "failed")

        with pytest.raises(TigerFlowError):
            await job.stop(client)


class TestCreateTigerflowClient:
    """Tests for create_tigerflow_client factory function."""

    @patch("blackfish.server.jobs.base.deserialize_profile")
    def test_raises_error_when_remote_job_missing_user(
        self, mock_deserialize: Mock
    ) -> None:
        """create_tigerflow_client should raise when remote job has no user."""
        mock_deserialize.return_value = None
        job = create_test_batch_job(host="remote.cluster.edu", user=None)

        with pytest.raises(ValueError, match="Missing user or host"):
            create_tigerflow_client(job, MockAppConfig())

    @patch("blackfish.server.jobs.base.deserialize_profile")
    def test_raises_error_when_remote_job_missing_host(
        self, mock_deserialize: Mock
    ) -> None:
        """create_tigerflow_client should raise when remote job has no host."""
        mock_deserialize.return_value = None
        job = create_test_batch_job(host=None, user="testuser")

        with pytest.raises(ValueError, match="Missing user or host"):
            create_tigerflow_client(job, MockAppConfig())

    @patch("blackfish.server.jobs.base.deserialize_profile")
    def test_uses_python_path_from_slurm_profile(self, mock_deserialize: Mock) -> None:
        """create_tigerflow_client should use python_path from SlurmProfile."""
        mock_profile = Mock()
        mock_profile.home_dir = "/home/user"
        mock_profile.python_path = "/opt/python3.11/bin/python3"
        # Make isinstance check work for SlurmProfile
        mock_deserialize.return_value = mock_profile

        job = create_test_batch_job(host="localhost")

        with patch("blackfish.server.jobs.base.isinstance", return_value=True):
            client = create_tigerflow_client(job, MockAppConfig())

        assert client.python_path == "/opt/python3.11/bin/python3"

    @patch("blackfish.server.jobs.base.deserialize_profile")
    def test_creates_ssh_runner_for_remote_job(self, mock_deserialize: Mock) -> None:
        """create_tigerflow_client should create SSHRunner for remote job."""
        from blackfish.server.jobs.client import SSHRunner

        mock_deserialize.return_value = None
        job = create_test_batch_job(
            host="remote.cluster.edu", user="testuser", home_dir="/home/testuser"
        )

        client = create_tigerflow_client(job, MockAppConfig())

        assert isinstance(client.runner, SSHRunner)
        assert client.runner.user == "testuser"
        assert client.runner.host == "remote.cluster.edu"


class TestCreateTigerflowClientForProfile:
    """Tests for create_tigerflow_client_for_profile factory function."""

    @patch("blackfish.server.jobs.base.deserialize_profile")
    def test_raises_file_not_found_when_profile_missing(
        self, mock_deserialize: Mock
    ) -> None:
        """Should raise FileNotFoundError when profile doesn't exist."""
        mock_deserialize.return_value = None

        with pytest.raises(FileNotFoundError, match="Profile 'nonexistent' not found"):
            create_tigerflow_client_for_profile("nonexistent", MockAppConfig())

    @patch("blackfish.server.jobs.base.deserialize_profile")
    def test_creates_ssh_runner_for_slurm_profile(self, mock_deserialize: Mock) -> None:
        """Should create SSHRunner for SlurmProfile."""
        from blackfish.server.models.profile import SlurmProfile
        from blackfish.server.jobs.client import SSHRunner

        mock_profile = SlurmProfile(
            name="test-slurm",
            user="testuser",
            host="cluster.edu",
            home_dir="/home/testuser/.blackfish",
            cache_dir="/scratch/cache",
            python_path="/opt/python/bin/python3",
        )
        mock_deserialize.return_value = mock_profile

        client = create_tigerflow_client_for_profile("test-slurm", MockAppConfig())

        assert isinstance(client.runner, SSHRunner)
        assert client.runner.user == "testuser"
        assert client.runner.host == "cluster.edu"
        assert client.python_path == "/opt/python/bin/python3"

    @patch("blackfish.server.jobs.base.deserialize_profile")
    def test_creates_local_runner_for_local_profile(
        self, mock_deserialize: Mock
    ) -> None:
        """Should create LocalRunner for LocalProfile."""
        from blackfish.server.models.profile import LocalProfile
        from blackfish.server.jobs.client import LocalRunner

        mock_profile = LocalProfile(
            name="test-local",
            home_dir="/home/user/.blackfish",
            cache_dir="/tmp/cache",
        )
        mock_deserialize.return_value = mock_profile

        client = create_tigerflow_client_for_profile("test-local", MockAppConfig())

        assert isinstance(client.runner, LocalRunner)
        assert client.python_path == "python3"  # Default for local


class MockAppConfig:
    """Mock app config for testing."""

    HOME_DIR = "/home/test/.blackfish"


class TestBatchJobRepr:
    """Tests for BatchJob.__repr__()."""

    def test_repr_includes_name_task_status(self) -> None:
        """__repr__ should include name, task, and status."""
        job = create_test_batch_job(
            name="my-job", task="transcribe", status=BatchJobStatus.RUNNING
        )

        result = repr(job)

        assert "my-job" in result
        assert "transcribe" in result
        assert "running" in result


class TestTasks:
    """Tests for task registry functions."""

    def test_is_supported_task_returns_true_for_valid_task(self) -> None:
        """is_supported_task should return True for supported tasks."""
        assert is_supported_task("transcribe") is True
        assert is_supported_task("translate") is True

    def test_is_supported_task_returns_false_for_invalid_task(self) -> None:
        """is_supported_task should return False for unsupported tasks."""
        assert is_supported_task("nonexistent") is False

    def test_get_task_library_returns_library_for_valid_task(self) -> None:
        """get_task_library should return the library module for a task."""
        assert get_task_library("transcribe") == "tigerflow_ml.transcribe"

    def test_get_task_library_raises_for_invalid_task(self) -> None:
        """get_task_library should raise ValueError for unsupported tasks."""
        with pytest.raises(ValueError, match="Unsupported task"):
            get_task_library("nonexistent")

    def test_build_pipeline_config_includes_resources(self) -> None:
        """build_pipeline_config should include resources when provided."""
        resources = {"cpus": 4, "memory": "16GB", "gpus": 1}

        config = build_pipeline_config(
            task="transcribe",
            resources=resources,
        )

        assert config["tasks"][0]["resources"] == resources
