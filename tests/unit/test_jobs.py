import json
import pytest
from unittest import mock
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from litestar import Litestar
from app.jobs.base import BatchJob, BatchJobStatus
from app.jobs.speech_recognition import (
    SpeechRecognitionBatch,
    SpeechRecognitionBatchConfig,
)
from app.job import (
    JobState,
    LocalJob,
    SlurmJob,
    JobScheduler,
    ContainerProvider,
    LocalJobConfig,
    SlurmJobConfig,
)


pytestmark = pytest.mark.anyio


def test_start():
    # TODO: re-write batch_job.start using smaller methods and test these
    pass


async def test_update(session: AsyncSession, app: Litestar) -> None:
    job = BatchJob(
        id=UUID("2a7a8e62-40cc-4240-a825-463e5b11a81f"),
        name="test",
        pipeline="test_pipeline",
        repo_id="test/repo",
        profile="default",
        job_id="test-job",
    )
    job.status = BatchJobStatus.STOPPED
    assert await job.update(session, app.state) == BatchJobStatus.STOPPED, (
        "update should return current status if job is stopped"
    )
    job.status = BatchJobStatus.TIMEOUT
    assert await job.update(session, app.state) == BatchJobStatus.TIMEOUT, (
        "update should return current status if job is timed out"
    )
    job.status = BatchJobStatus.FAILED
    assert await job.update(session, app.state) == BatchJobStatus.FAILED, (
        "update should return current status if job is failed"
    )
    job.status = BatchJobStatus.COMPLETED
    assert await job.update(session, app.state) == BatchJobStatus.COMPLETED, (
        "update should return current status if job is completed"
    )

    job.status = BatchJobStatus.SUBMITTED
    job.job_id = None
    assert await job.update(session, app.state) == BatchJobStatus.SUBMITTED, (
        "update should return current status if job_id is missing"
    )


@mock.patch.object(BatchJob, "stop")
@mock.patch.object(BatchJob, "get_progress")
async def test_update_from_slurm(
    get_progress: mock.Mock, stop: mock.Mock, session: AsyncSession, app: Litestar
) -> None:
    batch_job = BatchJob(
        id=UUID("2a7a8e62-40cc-4240-a825-463e5b11a81f"),
        name="test",
        pipeline="test_pipeline",
        repo_id="test/repo",
        profile="hpc",
        user="test",
        host="hpc.example.com",
        home_dir="/home/test/.blackfish",
        scheduler=JobScheduler.Slurm,
        job_id="99999",
        status=BatchJobStatus.SUBMITTED,
    )

    job = SlurmJob("99999", "test", "hpc.example.com", "/home/test/.blackfish")

    job.state = JobState.MISSING
    assert (
        await batch_job.update_from_slurm(session, app.state, job)
        == BatchJobStatus.SUBMITTED
    ), "update_from_slurm should return current status if Slurm job state is MISSING"

    job.state = JobState.PENDING
    assert (
        await batch_job.update_from_slurm(session, app.state, job)
        == BatchJobStatus.PENDING
    ), "update_from_slurm should return PENDING if Slurm job is pending"

    job.state = JobState.CANCELLED
    assert (
        await batch_job.update_from_slurm(session, app.state, job)
        == BatchJobStatus.STOPPED
    ), "update_from_slurm should return STOPPED if Slurm job is cancelled"
    stop.assert_called_once()
    stop.reset_mock()

    job.state = JobState.TIMEOUT
    assert (
        await batch_job.update_from_slurm(session, app.state, job)
        == BatchJobStatus.TIMEOUT
    ), "update_from_slurm should return TIMEOUT if Slurm job is timed out"
    stop.assert_called_once()
    stop.reset_mock()

    job.state = JobState.COMPLETED
    assert (
        await batch_job.update_from_slurm(session, app.state, job)
        == BatchJobStatus.COMPLETED
    ), "update_from_slurm should return COMPLETED if Slurm job is completed"
    stop.assert_called_once()
    stop.reset_mock()

    job.state = JobState.RUNNING
    assert (
        await batch_job.update_from_slurm(session, app.state, job)
        == BatchJobStatus.RUNNING
    ), "update_from_slurm should return RUNNING if Slurm job is running"
    get_progress.assert_called_once()

    job.state = None
    assert (
        await batch_job.update_from_slurm(session, app.state, job)
        == BatchJobStatus.FAILED
    ), "update_from_slurm should return FAILED if Slurm job state is None"
    stop.assert_called_once()


@mock.patch.object(BatchJob, "stop")
@mock.patch.object(BatchJob, "get_progress")
async def test_update_from_local(
    get_progress: mock.Mock, stop: mock.Mock, session: AsyncSession, app: Litestar
) -> None:
    batch_job = BatchJob(
        id=UUID("2a7a8e62-40cc-4240-a825-463e5b11a81f"),
        name="test",
        pipeline="test_pipeline",
        repo_id="test/repo",
        profile="hpc",
        provider=ContainerProvider.Docker,
        job_id="test-job",
        status=BatchJobStatus.SUBMITTED,
    )

    job = LocalJob("test-job", ContainerProvider.Docker)

    job.state = JobState.MISSING
    assert (
        await batch_job.update_from_local(session, app.state, job)
        == BatchJobStatus.SUBMITTED
    ), "update_from_local should return current status if local job state is MISSING"

    job.state = JobState.CREATED
    assert (
        await batch_job.update_from_local(session, app.state, job)
        == BatchJobStatus.PENDING
    ), "update_from_local should return PENDING if local job is created"

    job.state = JobState.EXITED
    assert (
        await batch_job.update_from_local(session, app.state, job)
        == BatchJobStatus.STOPPED
    ), "update_from_local should return STOPPED if local job is exited"
    stop.assert_called_once()
    stop.reset_mock()

    job.state = JobState.RUNNING
    assert (
        await batch_job.update_from_local(session, app.state, job)
        == BatchJobStatus.RUNNING
    ), "update_from_local should return RUNNING if local job is running"
    get_progress.assert_called_once()

    job.state = None
    assert (
        await batch_job.update_from_local(session, app.state, job)
        == BatchJobStatus.FAILED
    ), "update_from_local should return FAILED if local job state is None"
    stop.assert_called_once()


@mock.patch.object(LocalJob, "cancel")
@mock.patch.object(SlurmJob, "cancel")
@mock.patch.object(BatchJob, "get_progress")
@mock.patch.object(LocalJob, "update")
@mock.patch.object(SlurmJob, "update")
async def test_stop(
    update_slurm: mock.Mock,
    update_local: mock.Mock,
    get_progress: mock.Mock,
    cancel_slurm: mock.Mock,
    cancel_local: mock.Mock,
    app: Litestar,
    session: AsyncSession,
) -> None:
    batch_job = BatchJob(
        id=UUID("2a7a8e62-40cc-4240-a825-463e5b11a81f"),
        name="test",
        pipeline="test_pipeline",
        repo_id="test/repo",
        profile="default",
    )

    batch_job.status = BatchJobStatus.STOPPED
    assert await batch_job.stop(session, app.state) is None, (
        "Should return None when job is stopped"
    )
    batch_job.status = BatchJobStatus.TIMEOUT
    assert await batch_job.stop(session, app.state) is None, (
        "Should return None when job is timed out"
    )
    batch_job.status = BatchJobStatus.FAILED
    assert await batch_job.stop(session, app.state) is None, (
        "Should return None when job is failed"
    )
    batch_job.status = BatchJobStatus.COMPLETED
    assert await batch_job.stop(session, app.state) is None, (
        "Should return None when job is completed"
    )

    batch_job.status = BatchJobStatus.RUNNING
    batch_job.job_id = None
    with pytest.raises(
        Exception,
        match="Unable to stop batch job 2a7a8e62-40cc-4240-a825-463e5b11a81f because `job_id` is missing.",
    ):
        await batch_job.stop(session, app.state)

    batch_job.status = BatchJobStatus.RUNNING
    batch_job.job_id = "test-job"
    batch_job.provider = ContainerProvider.Docker
    await batch_job.stop(session, app.state)
    cancel_local.assert_called_once()

    batch_job.status = BatchJobStatus.RUNNING
    batch_job.job_id = "66666"
    batch_job.scheduler = JobScheduler.Slurm
    batch_job.user = "test"
    batch_job.host = "hpc.example.com"
    batch_job.home_dir = "/home/test/.blackfish"
    await batch_job.stop(session, app.state)
    cancel_slurm.assert_called_once()


@mock.patch.object(LocalJob, "update")
@mock.patch.object(SlurmJob, "update")
def test_get_job(update_slurm: mock.Mock, update_local: mock.Mock) -> None:
    batch_job = SpeechRecognitionBatch(
        id=UUID("2a7a8e62-40cc-4240-a825-463e5b11a81f"),
        name="test",
        pipeline="test_pipeline",
        repo_id="openai/whisper-large-v3",
        profile="default",
        provider=ContainerProvider.Docker,
        mount="/home/test",
    )
    assert batch_job.get_job() is None, (
        "get_job should return None if the job_id is missing"
    )

    batch_job = SpeechRecognitionBatch(
        id=UUID("2a7a8e62-40cc-4240-a825-463e5b11a81f"),
        name="test",
        pipeline="test_pipeline",
        repo_id="openai/whisper-large-v3",
        profile="default",
        mount="/home/test",
        job_id="test-job",
    )
    assert batch_job.get_job() is None, (
        "get_job should return None for non-Slurm profiles with missing provider"
    )

    batch_job = SpeechRecognitionBatch(
        id=UUID("2a7a8e62-40cc-4240-a825-463e5b11a81f"),
        name="test",
        pipeline="test_pipeline",
        repo_id="openai/whisper-large-v3",
        profile="default",
        provider=ContainerProvider.Docker,
        mount="/home/test",
        job_id="test-job",
    )
    job = batch_job.get_job()
    assert job == LocalJob("test-job", ContainerProvider.Docker, "test")
    update_local.assert_called_once()

    batch_job = SpeechRecognitionBatch(
        id=UUID("2a7a8e62-40cc-4240-a825-463e5b11a81f"),
        name="test",
        pipeline="test_pipeline",
        repo_id="openai/whisper-large-v3",
        profile="hpc",
        user="test",
        host="hpc.example.com",
        home_dir="/home/test/.blackfish",
        scheduler=JobScheduler.Slurm,
        mount="/home/test",
        job_id="66666",
    )
    job = batch_job.get_job()
    assert job == SlurmJob(
        job_id=66666,
        user="test",
        host="hpc.example.com",
        name="test",
        data_dir="/home/test/.blackfish/jobs/2a7a8e6240cc4240a825463e5b11a81f",
    )
    update_slurm.assert_called_once()


def test_get_speech_recognition_progress(app: Litestar) -> None:
    batch_job = SpeechRecognitionBatch(
        id=UUID("2a7a8e62-40cc-4240-a825-463e5b11a81f"),
        name="test",
        pipeline="speech_recognition",
        repo_id="openai/whisper-large-v3",
        profile="default",
        provider=ContainerProvider.Docker,
    )
    job = batch_job.get_progress(app.state)
    assert job is None, "get_progress should return None if mount is not set"

    batch_job = SpeechRecognitionBatch(
        id=UUID("2a7a8e62-40cc-4240-a825-463e5b11a81f"),
        name="test",
        pipeline="speech_recognition",
        repo_id="openai/whisper-large-v3",
        profile="default",
        provider=ContainerProvider.Docker,
        mount="/home/test",
    )
    job = batch_job.get_progress(app.state)
    assert job is None, (
        "get_progress should return None if checkpoint file does not exist"
    )


def test_render_speech_recognition_script(app: Litestar) -> None:
    with open("tests/unit/snapshots/jobs.json", "r") as f:
        script_snapshots = json.load(f)

    # Local
    batch_job = SpeechRecognitionBatch(
        id=UUID("2a7a8e62-40cc-4240-a825-463e5b11a81f"),
        name="test",
        pipeline="speech_recognition",
        repo_id="openai/whisper-large-v3",
        profile="default",
        provider=ContainerProvider.Docker,
        mount="/home/test",
    )
    job_config = LocalJobConfig(gres=True)
    container_config = SpeechRecognitionBatchConfig(
        model_dir="/home/test/.blackfish/models/models--openai-whisper-large-v3",
        revision="169d4a4341b33bc18d8881c4b69c2e104e1cc0af",
    )
    script = batch_job.render_job_script(app.state, job_config, container_config)
    assert script == script_snapshots["speech_recognition_local_gres_true"]

    batch_job = SpeechRecognitionBatch(
        id=UUID("2a7a8e62-40cc-4240-a825-463e5b11a81f"),
        name="test",
        pipeline="speech_recognition",
        repo_id="openai/whisper-large-v3",
        profile="default",
        provider=ContainerProvider.Docker,
        mount="/home/test",
    )
    job_config = LocalJobConfig(gres=False)
    container_config = SpeechRecognitionBatchConfig(
        model_dir="/home/test/.blackfish/models/models--openai-whisper-large-v3",
        revision="169d4a4341b33bc18d8881c4b69c2e104e1cc0af",
    )
    script = batch_job.render_job_script(app.state, job_config, container_config)
    assert script == script_snapshots["speech_recognition_local_gres_false"]

    batch_job = SpeechRecognitionBatch(
        id=UUID("2a7a8e62-40cc-4240-a825-463e5b11a81f"),
        name="test",
        pipeline="speech_recognition",
        repo_id="openai/whisper-large-v3",
        profile="does-not-exist",
        provider=ContainerProvider.Docker,
        mount="/home/test",
    )
    job_config = LocalJobConfig(gres=False)
    container_config = SpeechRecognitionBatchConfig(
        model_dir="/home/test/.blackfish/models/models--openai-whisper-large-v3",
        revision="169d4a4341b33bc18d8881c4b69c2e104e1cc0af",
    )
    script = batch_job.render_job_script(app.state, job_config, container_config)
    assert script == script_snapshots["speech_recognition_local_missing_profile"]

    batch_job = SpeechRecognitionBatch(
        id=UUID("2a7a8e62-40cc-4240-a825-463e5b11a81f"),
        name="test",
        pipeline="speech_recognition",
        repo_id="openai/whisper-large-v3",
        profile="default",
        provider=ContainerProvider.Docker,
    )
    job_config = LocalJobConfig(gres=False)
    container_config = SpeechRecognitionBatchConfig(
        model_dir="/home/test/.blackfish/models/models--openai-whisper-large-v3",
        revision="169d4a4341b33bc18d8881c4b69c2e104e1cc0af",
    )
    script = batch_job.render_job_script(app.state, job_config, container_config)
    assert script == script_snapshots["speech_recognition_local_missing_mount"]

    batch_job = SpeechRecognitionBatch(
        id=UUID("2a7a8e62-40cc-4240-a825-463e5b11a81f"),
        name="test",
        pipeline="speech_recognition",
        repo_id="openai/whisper-large-v3",
        profile="default",
        provider=ContainerProvider.Docker,
        mount="/home/test",
    )
    job_config = LocalJobConfig(gres=False)
    container_config = SpeechRecognitionBatchConfig(
        model_dir="/home/test/.blackfish/models/models--openai-whisper-large-v3",
        revision="169d4a4341b33bc18d8881c4b69c2e104e1cc0af",
        kwargs=["--language", "en"],
    )
    script = batch_job.render_job_script(app.state, job_config, container_config)
    assert script == script_snapshots["speech_recognition_local_with_kwargs"]

    # Slurm
    batch_job = SpeechRecognitionBatch(
        id=UUID("2a7a8e62-40cc-4240-a825-463e5b11a81f"),
        name="test",
        pipeline="speech_recognition",
        repo_id="openai/whisper-large-v3",
        profile="hpc",
        scheduler="slurm",
        mount="/home/test",
    )
    job_config = SlurmJobConfig(
        name="test",
        time="00:30:00",
        nodes=1,
        ntasks_per_node=1,
        mem=8,
        gres=0,
        partition="test",
        constraint="gpu80",
    )
    container_config = SpeechRecognitionBatchConfig(
        model_dir="/home/test/.blackfish/models/models--openai-whisper-large-v3",
        revision="169d4a4341b33bc18d8881c4b69c2e104e1cc0af",
    )
    script = batch_job.render_job_script(app.state, job_config, container_config)
    assert script == script_snapshots["speech_recognition_slurm_gres_0"]

    batch_job = SpeechRecognitionBatch(
        id=UUID("2a7a8e62-40cc-4240-a825-463e5b11a81f"),
        name="test",
        pipeline="speech_recognition",
        repo_id="openai/whisper-large-v3",
        profile="hpc",
        scheduler="slurm",
        mount="/home/test",
    )
    job_config = SlurmJobConfig(
        name="test",
        time="00:30:00",
        nodes=1,
        ntasks_per_node=1,
        mem=8,
        gres=1,
        partition="test",
        constraint="gpu80",
    )
    container_config = SpeechRecognitionBatchConfig(
        model_dir="/home/test/.blackfish/models/models--openai-whisper-large-v3",
        revision="169d4a4341b33bc18d8881c4b69c2e104e1cc0af",
    )
    script = batch_job.render_job_script(app.state, job_config, container_config)
    assert script == script_snapshots["speech_recognition_slurm_gres_1"]

    batch_job = SpeechRecognitionBatch(
        id=UUID("2a7a8e62-40cc-4240-a825-463e5b11a81f"),
        name="test",
        pipeline="speech_recognition",
        repo_id="openai/whisper-large-v3",
        profile="hpc",
        scheduler="slurm",
        mount="/home/test",
    )
    job_config = SlurmJobConfig(
        name="test",
        time="00:30:00",
        nodes=1,
        ntasks_per_node=1,
        mem=8,
        gres=4,
        partition="test",
        constraint="gpu80",
    )
    container_config = SpeechRecognitionBatchConfig(
        model_dir="/home/test/.blackfish/models/models--openai-whisper-large-v3",
        revision="169d4a4341b33bc18d8881c4b69c2e104e1cc0af",
    )
    script = batch_job.render_job_script(app.state, job_config, container_config)
    assert script == script_snapshots["speech_recognition_slurm_gres_4"]
