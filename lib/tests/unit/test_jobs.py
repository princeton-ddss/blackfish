"""Unit tests for BatchJob orchestration logic."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

from blackfish.server.config import ContainerProvider
from blackfish.server.images import DEFAULT_IMAGES
from blackfish.server.job import JobState
from blackfish.server.jobs.base import (
    BatchJob,
    BatchJobStatus,
    create_tigerflow_client,
    create_tigerflow_client_for_profile,
)
from blackfish.server.jobs.client import (
    TigerFlowClient,
    TigerFlowReport,
    TigerFlowReportStatus,
    TigerFlowProgress,
    TigerFlowPipelineProgress,
    TigerFlowError,
    TigerFlowVersions,
)
from blackfish.server.jobs.tasks import (
    is_supported_task,
    get_task_library,
    build_pipeline_config,
)


pytestmark = pytest.mark.anyio


class MockAppConfig:
    """Mock app config for testing."""

    HOME_DIR = "/home/test/.blackfish"
    IMAGES = DEFAULT_IMAGES
    CONTAINER_PROVIDER = ContainerProvider.Apptainer


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
        # SQLAlchemy column defaults only apply on flush; set them explicitly
        # so the restart-loop arithmetic in ``update`` has real ints to work with.
        "restarts": 0,
        "max_restarts": 20,
        "stalled_restarts": 0,
        "max_stalled_restarts": 1,
        "processed_highwater": 0,
    }
    defaults.update(kwargs)
    return BatchJob(**defaults)


def create_mock_client() -> AsyncMock:
    """Create a mock TigerFlowClient.

    ``runner.run`` defaults to a success tuple so directory checks
    (``_ensure_directories``) pass; override per-test as needed.
    """
    client = AsyncMock(spec=TigerFlowClient)
    client.host = "localhost"
    client.runner = AsyncMock()
    client.runner.run = AsyncMock(return_value=(0, b"", b""))
    return client


class TestBatchJobStart:
    """Tests for BatchJob.start()."""

    async def test_start_calls_check_health(self) -> None:
        """start should verify the image (check_health) before submitting."""
        job = create_test_batch_job()
        client = create_mock_client()
        client.check_health.return_value = TigerFlowVersions(
            tigerflow="0.1.0", tigerflow_ml="0.1.0"
        )

        with patch.object(job, "_submit", new=AsyncMock(return_value="99")):
            await job.start(MockAppConfig(), client)

        client.check_health.assert_called_once()

    async def test_start_stores_versions_for_reproducibility(self) -> None:
        """start should store tigerflow versions on the job."""
        job = create_test_batch_job()
        client = create_mock_client()
        client.check_health.return_value = TigerFlowVersions(
            tigerflow="0.2.0", tigerflow_ml="0.3.0"
        )

        with patch.object(job, "_submit", new=AsyncMock(return_value="99")):
            await job.start(MockAppConfig(), client)

        assert job.tigerflow_version == "0.2.0"
        assert job.tigerflow_ml_version == "0.3.0"

    async def test_start_submits_and_records_slurm_job_id(self) -> None:
        """start should submit the allocation and record the returned job id."""
        job = create_test_batch_job()
        client = create_mock_client()
        client.check_health.return_value = TigerFlowVersions(
            tigerflow="0.1.0", tigerflow_ml="0.1.0"
        )

        submit = AsyncMock(return_value="123456")
        with patch.object(job, "_submit", new=submit):
            await job.start(MockAppConfig(), client)

        submit.assert_called_once()
        assert job.pid == "123456"

    async def test_start_sets_status_to_running(self) -> None:
        """start should set status to RUNNING on success."""
        job = create_test_batch_job()
        client = create_mock_client()
        client.check_health.return_value = TigerFlowVersions(
            tigerflow="0.1.0", tigerflow_ml="0.1.0"
        )

        with patch.object(job, "_submit", new=AsyncMock(return_value="99")):
            await job.start(MockAppConfig(), client)

        assert job.status == BatchJobStatus.RUNNING

    async def test_start_propagates_tigerflow_error(self) -> None:
        """start should propagate a missing-image TigerFlowError from check_health."""
        job = create_test_batch_job()
        client = create_mock_client()
        client.check_health.side_effect = TigerFlowError("missing", "host")

        with pytest.raises(TigerFlowError):
            await job.start(MockAppConfig(), client)


def make_mock_report(
    running: bool = True,
    pid: int | None = 12345,
    finished: int = 5,
    in_progress: int = 3,
    staged: int | None = 2,
    errored: int = 0,
) -> TigerFlowReport:
    """Create a TigerFlowReport for testing."""
    return TigerFlowReport(
        status=TigerFlowReportStatus(running=running, pid=pid),
        progress=TigerFlowProgress(
            pipeline=TigerFlowPipelineProgress(
                finished=finished,
                in_progress=in_progress,
                staged=staged,
                errored=errored,
            ),
            tasks=[],
        ),
        metrics={},
        errors={},
    )


def _drive_update(
    job: BatchJob,
    *,
    total: int,
    slurm_state: JobState,
    submit_job_id: str = "654321",
) -> AsyncMock:
    """Patch the update collaborators (input count, slurm state, resubmit).

    Returns the ``_submit`` mock so callers can assert on resubmission.
    """
    submit = AsyncMock(return_value=submit_job_id)
    job._count_input_files = AsyncMock(return_value=total)  # type: ignore[method-assign]
    job._slurm_state = AsyncMock(return_value=slurm_state)  # type: ignore[method-assign]
    job._submit = submit  # type: ignore[method-assign]
    return submit


class TestBatchJobUpdate:
    """Tests for BatchJob.update() and its restart policy."""

    async def test_update_records_progress_and_stays_running_when_alive(self) -> None:
        """Slurm alive with work remaining -> RUNNING, high-water bumped."""
        job = create_test_batch_job(status=BatchJobStatus.RUNNING)
        client = create_mock_client()
        client.report.return_value = make_mock_report(
            finished=5, in_progress=3, staged=2, errored=0
        )
        submit = _drive_update(job, total=10, slurm_state=JobState.RUNNING)

        result = await job.poll(client, MockAppConfig())

        assert result == BatchJobStatus.RUNNING
        assert job.staged == 5  # in_progress + staged
        assert job.finished == 5
        assert job.errored == 0
        assert job.processed_highwater == 5
        submit.assert_not_called()

    async def test_update_completes_when_processed_reaches_total(self) -> None:
        """processed >= total -> STOPPED."""
        job = create_test_batch_job(status=BatchJobStatus.RUNNING)
        client = create_mock_client()
        client.report.return_value = make_mock_report(
            finished=10, in_progress=0, staged=None, errored=0
        )
        submit = _drive_update(job, total=10, slurm_state=JobState.COMPLETED)

        result = await job.poll(client, MockAppConfig())

        assert result == BatchJobStatus.STOPPED
        assert job.finished == 10
        submit.assert_not_called()

    async def test_update_resubmits_when_ended_with_progress(self) -> None:
        """Allocation ended, progress advanced, under budget -> resubmit + RUNNING."""
        job = create_test_batch_job(
            status=BatchJobStatus.RUNNING,
            restarts=0,
            processed_highwater=2,
            stalled_restarts=3,
        )
        client = create_mock_client()
        client.report.return_value = make_mock_report(
            finished=5, in_progress=0, staged=None, errored=0
        )
        submit = _drive_update(job, total=10, slurm_state=JobState.COMPLETED)

        result = await job.poll(client, MockAppConfig())

        assert result == BatchJobStatus.RUNNING
        submit.assert_called_once()
        assert job.pid == "654321"
        assert job.restarts == 1
        # Forward progress resets the stall counter and raises the high-water mark.
        assert job.stalled_restarts == 0
        assert job.processed_highwater == 5

    async def test_update_stalls_when_no_progress(self) -> None:
        """Ended, no progress, stall budget reached -> STALLED."""
        job = create_test_batch_job(
            status=BatchJobStatus.RUNNING,
            restarts=1,
            processed_highwater=5,
            stalled_restarts=0,
            max_stalled_restarts=1,
        )
        client = create_mock_client()
        client.report.return_value = make_mock_report(
            finished=5, in_progress=0, staged=None, errored=0
        )
        submit = _drive_update(job, total=10, slurm_state=JobState.COMPLETED)

        result = await job.poll(client, MockAppConfig())

        assert result == BatchJobStatus.STALLED
        assert job.stalled_restarts == 1
        submit.assert_not_called()

    async def test_update_exhausts_when_restart_budget_spent(self) -> None:
        """restarts >= max_restarts -> EXHAUSTED (checked before stall)."""
        job = create_test_batch_job(
            status=BatchJobStatus.RUNNING,
            restarts=20,
            max_restarts=20,
            processed_highwater=5,
        )
        client = create_mock_client()
        client.report.return_value = make_mock_report(
            finished=6, in_progress=0, staged=None, errored=0
        )
        submit = _drive_update(job, total=10, slurm_state=JobState.COMPLETED)

        result = await job.poll(client, MockAppConfig())

        assert result == BatchJobStatus.EXHAUSTED
        submit.assert_not_called()

    async def test_update_propagates_tigerflow_error(self) -> None:
        """update should propagate TigerFlowError from client.report."""
        job = create_test_batch_job(status=BatchJobStatus.RUNNING)
        client = create_mock_client()
        client.report.side_effect = TigerFlowError("report", "host", "failed")

        with pytest.raises(TigerFlowError):
            await job.poll(client, MockAppConfig())

    @pytest.mark.parametrize(
        "terminal",
        [
            BatchJobStatus.STOPPED,
            BatchJobStatus.STALLED,
            BatchJobStatus.EXHAUSTED,
            BatchJobStatus.BROKEN,
        ],
    )
    async def test_update_short_circuits_terminal_jobs(
        self, terminal: BatchJobStatus
    ) -> None:
        """Terminal jobs return immediately without remote calls or counter churn."""
        job = create_test_batch_job(status=terminal, stalled_restarts=1)
        client = create_mock_client()
        submit = _drive_update(job, total=10, slurm_state=JobState.COMPLETED)

        result = await job.poll(client, MockAppConfig())

        assert result == terminal
        # No report/count/sacct/resubmit work, and counters are untouched.
        client.report.assert_not_called()
        submit.assert_not_called()
        assert job.stalled_restarts == 1

    async def test_update_stops_when_input_dir_has_no_files(self) -> None:
        """Ended allocation with zero matching inputs -> STOPPED, not STALLED."""
        job = create_test_batch_job(status=BatchJobStatus.RUNNING)
        client = create_mock_client()
        client.report.return_value = make_mock_report(
            finished=0, in_progress=0, staged=None, errored=0
        )
        submit = _drive_update(job, total=0, slurm_state=JobState.COMPLETED)

        result = await job.poll(client, MockAppConfig())

        assert result == BatchJobStatus.STOPPED
        submit.assert_not_called()

    async def test_poll_defers_restart_when_input_count_inconclusive(self) -> None:
        """Allocation ended but the input count is inconclusive (None, e.g. a
        transient find/SSH failure): don't resubmit. Stay RUNNING and let the
        next poll retry once the count is readable again."""
        job = create_test_batch_job(status=BatchJobStatus.RUNNING)
        client = create_mock_client()
        client.report.return_value = make_mock_report(
            finished=5, in_progress=0, staged=None, errored=0
        )
        submit = _drive_update(job, total=None, slurm_state=JobState.COMPLETED)

        result = await job.poll(client, MockAppConfig())

        assert result == BatchJobStatus.RUNNING
        submit.assert_not_called()


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

    @patch("blackfish.server.jobs.base.remote")
    async def test_stop_cancels_real_allocation_but_not_local(
        self, mock_remote: Mock
    ) -> None:
        """stop must cancel a Slurm allocation (else it burns GPUs until walltime)
        and mark the job STOPPED; a LocalProfile (local-<uuid>) has no allocation."""
        mock_remote.run = AsyncMock()

        slurm_job = create_test_batch_job(
            status=BatchJobStatus.RUNNING, host="localhost", pid="4242"
        )
        await slurm_job.stop(create_mock_client())
        assert slurm_job.status == BatchJobStatus.STOPPED
        assert mock_remote.run.await_count == 1  # scancel issued

        mock_remote.run.reset_mock()
        local_job = create_test_batch_job(
            status=BatchJobStatus.RUNNING, host="localhost", pid="local-abc"
        )
        await local_job.stop(create_mock_client())
        assert local_job.status == BatchJobStatus.STOPPED
        mock_remote.run.assert_not_called()  # nothing to cancel


class TestBatchJobEnsureDirectories:
    """Input validation + output setup at job start."""

    async def test_missing_input_dir_fails_fast(self) -> None:
        """A nonexistent input_dir must raise (fail fast), not be silently created."""
        job = create_test_batch_job()
        client = create_mock_client()
        client.runner.run = AsyncMock(return_value=(1, b"", b""))  # test -d fails

        with pytest.raises(ValueError, match="Input directory does not exist"):
            await job._ensure_directories(client)


class TestBatchJobLaunchByProfileType:
    """The launch template + mechanism are chosen by profile *type*, not host.

    A SlurmProfile uses sbatch + batch_slurm.sh even when reached over a local
    runner (host=localhost, the Open OnDemand pattern); a LocalProfile uses
    bash + batch_local.sh and never sbatch.
    """

    def _slurm_localhost(self):
        from blackfish.server.models.profile import SlurmProfile

        return SlurmProfile(
            name="onburst",
            host="localhost",
            user="alice",
            home_dir="/home/alice/.blackfish",
            cache_dir="/scratch/cache",
        )

    def _local(self):
        from blackfish.server.models.profile import LocalProfile

        return LocalProfile(
            name="local",
            home_dir="/home/alice/.blackfish",
            cache_dir="/scratch/cache",
        )

    @patch("blackfish.server.jobs.base.deserialize_profile")
    def test_slurm_localhost_renders_slurm_template(
        self, mock_deserialize: Mock
    ) -> None:
        mock_deserialize.return_value = self._slurm_localhost()
        job = create_test_batch_job(
            host="localhost", resources={"gres": 1, "time": "02:00:00"}
        )

        script = job._render_script(MockAppConfig())

        # batch_slurm.sh carries #SBATCH directives with the requested resources.
        assert "#SBATCH" in script
        assert "--time=02:00:00" in script
        assert "--gres=gpu:1" in script
        assert "apptainer run" in script

    @patch("blackfish.server.jobs.base.deserialize_profile")
    def test_local_profile_renders_local_template(self, mock_deserialize: Mock) -> None:
        mock_deserialize.return_value = self._local()
        job = create_test_batch_job(host="localhost")

        script = job._render_script(MockAppConfig())

        # batch_local.sh has no scheduler directives.
        assert "#SBATCH" not in script

    @patch("blackfish.server.jobs.base.remote")
    @patch("blackfish.server.jobs.base.deserialize_profile")
    async def test_slurm_localhost_submits_via_sbatch(
        self,
        mock_deserialize: Mock,
        mock_remote: Mock,
        tmp_path,
    ) -> None:
        mock_deserialize.return_value = self._slurm_localhost()
        mock_remote.run = AsyncMock(
            return_value=Mock(stdout=b"Submitted batch job 4242")
        )
        job = create_test_batch_job(host="localhost")
        app_config = Mock(HOME_DIR=str(tmp_path))

        with patch.object(job, "_render_script", return_value="#!/bin/bash\n"):
            job_id = await job._submit(app_config)

        assert job_id == "4242"
        # sbatch was used, not bash.
        assert mock_remote.run.call_args.args[0][0] == "sbatch"

    @patch("blackfish.server.jobs.base.remote")
    @patch("blackfish.server.jobs.base.deserialize_profile")
    async def test_local_profile_submits_via_bash_not_sbatch(
        self,
        mock_deserialize: Mock,
        mock_remote: Mock,
        tmp_path,
    ) -> None:
        mock_deserialize.return_value = self._local()
        mock_remote.run = AsyncMock(return_value=Mock(stdout=b""))
        job = create_test_batch_job(host="localhost")
        app_config = Mock(HOME_DIR=str(tmp_path))

        with patch.object(job, "_render_script", return_value="#!/bin/bash\n"):
            job_id = await job._submit(app_config)

        # Ran the container directly with bash; no Slurm job id.
        assert mock_remote.run.call_args.args[0][0] == "bash"
        assert job_id.startswith("local-")


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
    def test_locates_sif_via_profile_cache_not_model_cache(
        self, mock_deserialize: Mock
    ) -> None:
        """The SIF is located under the profile's cache_dir, not job.cache_dir
        (which is the HF model cache, e.g. <profile.cache_dir>/models)."""
        from blackfish.server.models.profile import SlurmProfile

        mock_deserialize.return_value = SlurmProfile(
            name="default",
            host="della",
            user="alice",
            home_dir="/home/alice/.blackfish",
            cache_dir="/scratch/.blackfish",
        )
        job = create_test_batch_job(
            host="localhost",
            home_dir="/home/alice/.blackfish",
            cache_dir="/scratch/.blackfish/models",
        )

        client = create_tigerflow_client(job, MockAppConfig())

        assert client.image is DEFAULT_IMAGES["tigerflow_ml"]
        assert client.provider is ContainerProvider.Apptainer
        assert client.cache_dir == "/scratch/.blackfish"
        assert client.sif_path == "/scratch/.blackfish/images/tigerflow-ml_0.1.1.sif"

    @patch("blackfish.server.jobs.base.deserialize_profile")
    def test_slurm_job_uses_apptainer_even_when_host_detects_docker(
        self, mock_deserialize: Mock
    ) -> None:
        """The cluster runs Apptainer, so a Slurm job's client uses Apptainer
        regardless of the Blackfish host's locally detected provider."""
        from blackfish.server.models.profile import SlurmProfile

        mock_deserialize.return_value = SlurmProfile(
            name="default",
            host="della",
            user="alice",
            home_dir="/home/alice/.blackfish",
            cache_dir="/scratch/.blackfish",
        )
        job = create_test_batch_job(host="della", user="alice")

        class DockerHostConfig:
            HOME_DIR = "/home/test/.blackfish"
            IMAGES = DEFAULT_IMAGES
            CONTAINER_PROVIDER = ContainerProvider.Docker

        client = create_tigerflow_client(job, DockerHostConfig())

        assert client.provider is ContainerProvider.Apptainer

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
        )
        mock_deserialize.return_value = mock_profile

        client = create_tigerflow_client_for_profile("test-slurm", MockAppConfig())

        assert isinstance(client.runner, SSHRunner)
        assert client.runner.user == "testuser"
        assert client.runner.host == "cluster.edu"
        assert client.cache_dir == "/scratch/cache"

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
        assert is_supported_task("detect") is True
        assert is_supported_task("ocr") is True
        assert is_supported_task("transcribe") is True
        assert is_supported_task("translate") is True

    def test_is_supported_task_returns_false_for_invalid_task(self) -> None:
        """is_supported_task should return False for unsupported tasks."""
        assert is_supported_task("nonexistent") is False

    def test_get_task_library_returns_local_module_for_valid_task(self) -> None:
        """get_task_library should return the task's ``local`` module."""
        module = get_task_library("transcribe")
        assert module == "tigerflow_ml.audio.transcribe.local"
        assert module.endswith(".local")

    def test_get_task_library_raises_for_invalid_task(self) -> None:
        """get_task_library should raise ValueError for unsupported tasks."""
        with pytest.raises(ValueError, match="Unsupported task"):
            get_task_library("nonexistent")

    def test_build_pipeline_config_builds_local_task(self) -> None:
        """build_pipeline_config should emit a single ``local`` task entry."""
        config = build_pipeline_config(task="transcribe", input_ext=".wav")

        assert list(config.keys()) == ["tasks"]
        task = config["tasks"][0]
        assert task["name"] == "transcribe"
        assert task["kind"] == "local"
        assert task["module"] == "tigerflow_ml.audio.transcribe.local"
        assert task["module"].endswith(".local")
        assert task["input_ext"] == ".wav"
        # Removed fields from the old venv-based signature are gone.
        assert "venv_path" not in task
        assert "resources" not in task
        assert "worker_resources" not in task
        assert "setup_commands" not in task

    def test_build_pipeline_config_includes_optional_params_and_output_ext(
        self,
    ) -> None:
        """params and output_ext are included when provided."""
        config = build_pipeline_config(
            task="transcribe",
            input_ext=".wav",
            params={"model": "openai/whisper-large-v3", "language": "en"},
            output_ext=".json",
        )

        task = config["tasks"][0]
        assert task["output_ext"] == ".json"
        assert task["params"]["model"] == "openai/whisper-large-v3"
        assert task["params"]["language"] == "en"
