import os
import subprocess
import uuid
from pathlib import Path
from typing import Optional
from enum import StrEnum, auto
from dataclasses import dataclass

from sqlalchemy.orm import Mapped
from sqlalchemy.ext.asyncio import AsyncSession
from advanced_alchemy.base import UUIDAuditBase
from litestar.datastructures import State
from jinja2 import Environment, PackageLoader

from app.config import BlackfishConfig, ContainerProvider
from app.job import JobScheduler, JobConfig, LocalJob, SlurmJob, Job, JobState
from app.logger import logger
from app.models.profile import BlackfishProfile, deserialize_profile


@dataclass
class BaseConfig: ...


class BatchJobStatus(StrEnum):
    SUBMITTED = auto()
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    STOPPED = auto()
    FAILED = auto()
    TIMEOUT = auto()


def format_status(status: BatchJobStatus | None) -> str:
    """Format job status for display."""
    return status.upper() if status else "NONE"


@dataclass
class BatchJobProgress:
    ntotal: int = 0
    nsuccess: int = 0
    nfail: int = 0


class BatchJob(UUIDAuditBase):
    __tablename__ = "jobs"
    name: Mapped[str]
    pipeline: Mapped[str]
    repo_id: Mapped[str]
    profile: Mapped[str]
    user: Mapped[Optional[str]]
    host: Mapped[Optional[str]]
    home_dir: Mapped[Optional[str]]
    cache_dir: Mapped[Optional[str]]
    job_id: Mapped[Optional[str]]
    status: Mapped[Optional[BatchJobStatus]]
    ntotal: Mapped[Optional[int]]
    nsuccess: Mapped[Optional[int]]
    nfail: Mapped[Optional[int]]
    scheduler: Mapped[Optional[str]]
    provider: Mapped[Optional[ContainerProvider]]
    mount: Mapped[Optional[str]]
    __mapper_args__ = {
        "polymorphic_on": "pipeline",
        "polymorphic_identity": "base",
    }

    def __repr__(self) -> str:
        return (
            f"<BatchJob(name={self.name}, status={self.status}, job_id={self.job_id})>"
        )

    def get_profile(
        self, app_config: State | BlackfishConfig
    ) -> BlackfishProfile | None:
        logger.debug(f"Fetching profile for batch job {self.id}")
        return deserialize_profile(app_config.HOME_DIR, self.profile)

    async def start(
        self,
        session: AsyncSession,
        app_config: State,
        job_options: JobConfig,
        container_options: BaseConfig,
    ) -> None:
        logger.debug("Adding job to database")
        session.add(self)
        await session.flush()  # set self.id

        profile = self.get_profile(app_config)
        if self.scheduler == JobScheduler.Slurm:
            script_path = Path(
                os.path.join(app_config.HOME_DIR, "jobs", self.id.hex, "start.sh")
            )
            logger.debug(f"Generating job script and writing to {script_path}.")
            os.makedirs(script_path.parent)
            with open(script_path, "w") as f:
                try:
                    script = self.render_job_script(
                        app_config, job_options, container_options
                    )
                    f.write(script)
                except Exception as e:
                    logger.error(f"Failed to render job script: {e}")
                    return None

            logger.info("Starting batch job")

            if self.host == "localhost":
                logger.debug("Submitting slurm job locally.")
                res = subprocess.check_output(
                    [
                        "sbatch",
                        "--chdir",
                        script_path.parent,
                        script_path,
                    ]
                )
                job_id = res.decode("utf-8").strip().split()[-1]
                self.status = BatchJobStatus.SUBMITTED
                self.job_id = job_id
            else:
                profile = self.get_profile(app_config)
                if profile is None:
                    logger.error("Failed to start batch job: profile is missing.")
                    return None

                logger.debug(f"Copying job script to {self.host}:{profile.home_dir}.")
                remote_script_dir = os.path.join(profile.home_dir, "jobs", self.id.hex)

                try:
                    _ = subprocess.check_output(
                        [
                            "ssh",
                            f"{self.user}@{self.host}",
                            "mkdir",
                            "-p",
                            remote_script_dir,
                        ]
                    )
                except Exception as e:
                    logger.error(f"Failed to copy job script to remote host: {e}.")
                    return

                try:
                    _ = subprocess.check_output(
                        [
                            "scp",
                            script_path,
                            (f"{self.user}@{self.host}:{remote_script_dir}"),
                        ]
                    )
                except Exception as e:
                    logger.error(f"Failed to copy job script to remote host: {e}")
                    return

                logger.debug(f"Submitting batch job to {self.host}.")
                try:
                    res = subprocess.check_output(
                        [
                            "ssh",
                            f"{self.user}@{self.host}",
                            "sbatch",
                            "--chdir",
                            remote_script_dir,
                            os.path.join(remote_script_dir, "start.sh"),
                        ]
                    )
                    job_id = res.decode("utf-8").strip().split()[-1]
                    self.status = BatchJobStatus.SUBMITTED
                    self.job_id = job_id
                except Exception as e:
                    logger.error(f"Failed to submit Slurm job: {e}")
                    return
        else:
            script_path = Path(
                os.path.join(app_config.HOME_DIR, "jobs", self.id.hex, "start.sh")
            )
            logger.debug(f"Generating job script and writing to {script_path}.")
            os.makedirs(script_path.parent)

            self.provider = app_config.CONTAINER_PROVIDER
            with open(script_path, "w") as f:
                try:
                    match self.provider:
                        case ContainerProvider.Apptainer:
                            logger.debug("The container provider is Apptainer.")
                            job_id = str(uuid.uuid4())
                            script = self.render_job_script(
                                app_config, job_options, container_options
                            )
                        case ContainerProvider.Docker:
                            logger.debug("The container provider is Docker.")
                            script = self.render_job_script(
                                app_config, job_options, container_options
                            )
                    f.write(script)
                except Exception as e:
                    logger.error(f"Failed to render job script: {e}")
                    return
            logger.info("Attempting to start batch job locally...")
            try:
                res = subprocess.check_output(["bash", script_path.as_posix()])
            except Exception as e:
                logger.error(f"Failed to start batch job: {e}")
            if self.provider == ContainerProvider.Docker:
                job_id = res.decode("utf-8").strip().split()[-1][:12]
            self.status = BatchJobStatus.SUBMITTED
            self.job_id = job_id

        logger.debug("Updating database entry")
        session.add(self)
        await session.flush()

    async def stop(
        self,
        session: AsyncSession,
        app_config: State,
        timeout: bool = False,
        failed: bool = False,
        completed: bool = False,
    ) -> None:
        logger.debug(f"Stopping batch job {self.id}")

        if self.status in [
            BatchJobStatus.STOPPED,
            BatchJobStatus.TIMEOUT,
            BatchJobStatus.FAILED,
            BatchJobStatus.COMPLETED,
        ]:
            logger.warning(
                f"Batch job is already stopped (status={self.status}). Aborting stop."
            )
            return

        if self.job_id is None:
            raise Exception(
                f"Unable to stop batch job {self.id} because `job_id` is missing."
            )

        job = self.get_job(verbose=True)
        if job is not None:
            job.cancel()

        progress = self.get_progress(app_config)
        if progress is not None:
            self.ntotal = progress.ntotal
            self.nsuccess = progress.nsuccess
            self.nfail = progress.nfail

        if timeout:
            self.status = BatchJobStatus.TIMEOUT
        elif failed:
            self.status = BatchJobStatus.FAILED
        elif completed:
            self.status = BatchJobStatus.COMPLETED
        else:
            self.status = BatchJobStatus.STOPPED

    async def update(
        self, session: AsyncSession, app_config: State
    ) -> BatchJobStatus | None:
        logger.debug(
            f"Checking status of batch job {self.id}. Current status is {format_status(self.status)}."
        )
        if self.status in [
            BatchJobStatus.STOPPED,
            BatchJobStatus.TIMEOUT,
            BatchJobStatus.FAILED,
            BatchJobStatus.COMPLETED,
        ]:
            logger.debug(
                f"Batch job {self.id} is no longer running. Aborting status update."
            )
            return self.status

        if self.job_id is None:
            logger.debug(
                f"Batch job {self.id} has no associated job. Aborting status update."
            )
            return self.status

        job = self.get_job(verbose=True)
        if isinstance(job, SlurmJob):
            return await self.update_from_slurm(session, app_config, job)
        elif isinstance(job, LocalJob):
            return await self.update_from_local(session, app_config, job)
        return None

    async def update_from_slurm(
        self, session: AsyncSession, app_config: State, job: SlurmJob
    ) -> BatchJobStatus | None:
        if job.state == JobState.PENDING:
            logger.debug(
                f"Batch job {self.id} has not started. Setting status to PENDING."
            )
            self.status = BatchJobStatus.PENDING
            return BatchJobStatus.PENDING
        elif job.state == JobState.MISSING:
            logger.warning(
                f"Batch job {self.id} has no job state (this batch job is likely"
                " new or has expired). Aborting status update."
            )
            return self.status
        elif job.state == JobState.CANCELLED:
            logger.debug(
                f"Batch job {self.id} has a cancelled job. Setting status to"
                " STOPPED and stopping the batch job."
            )
            await self.stop(session, app_config)
            return BatchJobStatus.STOPPED
        elif job.state == JobState.TIMEOUT:
            logger.debug(
                f"Batch job {self.id} has a timed out job. Setting status to"
                " TIMEOUT and stopping the batch job."
            )
            await self.stop(session, app_config, timeout=True)
            return BatchJobStatus.TIMEOUT
        elif job.state == JobState.COMPLETED:
            logger.debug(
                f"Batch job {self.id} has completed. Setting status to"
                " COMPLETED and stopping the batch job."
            )
            await self.stop(session, app_config, completed=True)
            return BatchJobStatus.COMPLETED
        elif job.state == JobState.RUNNING:
            logger.debug(
                f"Batch job {self.id} is running. Setting status to"
                " RUNNING and checking progress."
            )
            self.status = BatchJobStatus.RUNNING
            progress = self.get_progress(app_config)
            if progress is not None:
                self.ntotal = progress.ntotal
                self.nsuccess = progress.nsuccess
                self.nfail = progress.nfail
            return BatchJobStatus.RUNNING
        else:
            logger.debug(
                f"Batch job {self.id} has a failed job"
                f" (job.state={job.state}). Setting status to FAILED."
            )
            await self.stop(session, app_config, failed=True)
            return BatchJobStatus.FAILED

    async def update_from_local(
        self, session: AsyncSession, app_config: State, job: LocalJob
    ) -> BatchJobStatus | None:
        if job.state == JobState.CREATED:
            logger.debug(
                f"Batch job {self.id} has not started. Setting status to PENDING."
            )
            self.status = BatchJobStatus.PENDING
            return BatchJobStatus.PENDING
        elif job.state == JobState.MISSING:
            logger.warning(
                f"Batch job {self.id} has a missing job state (this batch job is likely"
                " new or has expired). Aborting status update."
            )
            return self.status
        elif job.state == JobState.EXITED:
            logger.debug(
                f"Batch job {self.id} has exited. Setting status to"
                " STOPPED and stopping the batch job."
            )
            await self.stop(session, app_config)
            return BatchJobStatus.STOPPED
        elif job.state == JobState.RUNNING:
            logger.debug(
                f"Batch job {self.id} is running. Setting status to"
                " RUNNING and checking progress."
            )
            self.status = BatchJobStatus.RUNNING
            progress = self.get_progress(app_config)
            if progress is not None:
                self.ntotal = progress.ntotal
                self.nsuccess = progress.nsuccess
                self.nfail = progress.nfail
            return BatchJobStatus.RUNNING
        elif job.state in [JobState.RESTARTING, JobState.PAUSED]:
            raise NotImplementedError
        else:
            logger.debug(
                f"Batch job {self.id} has a failed job"
                f" (job.state={job.state}). Setting status to FAILED."
            )
            await self.stop(session, app_config, failed=True)
            return BatchJobStatus.FAILED

    def get_progress(self, app_config: State) -> BatchJobProgress | None:
        raise NotImplementedError(
            "BatchJob.get_progress() must be implemented in subclasses."
        )

    def get_job(self, verbose: bool = False) -> Job | None:
        """Fetch the job backing the batch job."""

        job: Job

        if not self.job_id:
            logger.warning("Unable to fetch job: `self.job_id` missing.")
            return None

        if self.scheduler == JobScheduler.Slurm:
            if self.user and self.host and self.home_dir:
                job = SlurmJob(
                    job_id=int(self.job_id),
                    user=self.user,
                    host=self.host,
                    name=self.name,
                    data_dir=os.path.join(self.home_dir, "jobs", self.id.hex),
                )
            else:
                return None
        elif self.provider is not None:
            job = LocalJob(self.job_id, self.provider, self.name)
        else:
            logger.warning("Unable to fetch job: `self.provider` missing.")
            return None

        job.update(verbose=verbose)
        return job

    def render_job_script(
        self,
        app_config: State | BlackfishConfig,
        job_config: JobConfig,
        container_config: BaseConfig,
    ) -> str:
        env = Environment(
            loader=PackageLoader(
                "app",
                "templates",
            )
        )
        template = env.get_template(
            f"jobs/{self.pipeline}_{self.scheduler or 'local'}.sh"
        )
        job_script = template.render(
            uuid=self.id.hex,
            name=self.name,
            model=self.repo_id,
            provider=self.provider,
            profile=self.get_profile(app_config),
            container_config=container_config,
            job_config=job_config,
            mount=self.mount,
        )

        return job_script
