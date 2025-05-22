from __future__ import annotations

import subprocess
import os
from pathlib import Path
import uuid
import psutil
from datetime import datetime, timezone
from typing import Optional
import requests
from enum import StrEnum, auto
from dataclasses import dataclass

from sqlalchemy.orm import Mapped
from sqlalchemy.ext.asyncio import AsyncSession
from advanced_alchemy.base import UUIDAuditBase

from jinja2 import Environment, PackageLoader

from litestar.datastructures import State

from app.job import Job, JobState, SlurmJob, LocalJob, JobConfig, JobScheduler
from app.logger import logger
from app.utils import find_port
from app.config import ContainerProvider
from app.models.profile import BlackfishProfile, LocalProfile, SlurmProfile


@dataclass
class BaseConfig:
    port: Optional[int]
    # host: Optional[str]


class ServiceStatus(StrEnum):
    SUBMITTED = auto()
    PENDING = auto()
    STARTING = auto()
    HEALTHY = auto()
    UNHEALTHY = auto()
    STOPPED = auto()
    TIMEOUT = auto()
    FAILED = auto()


class Service(UUIDAuditBase):
    __tablename__ = "service"

    name: Mapped[str]
    image: Mapped[str]
    model: Mapped[str]

    profile: Mapped[str]
    host: Mapped[str]
    user: Mapped[Optional[str]]
    home_dir: Mapped[Optional[str]]
    cache_dir: Mapped[Optional[str]]

    job_id: Mapped[Optional[str]]
    port: Mapped[Optional[int]]
    status: Mapped[Optional[ServiceStatus]]

    scheduler: Mapped[Optional[str]]
    provider: Mapped[Optional[ContainerProvider]]
    mount: Mapped[Optional[str]]
    grace_period: Mapped[int]

    __mapper_args__ = {
        "polymorphic_on": "image",
        "polymorphic_identity": "base",
    }

    def __repr__(self) -> str:
        return f"Service(id={self.id}, name={self.name}, image={self.image}, model={self.model}, profile={self.profile}, host={self.host}, user={self.user}, home_dir={self.home_dir}, cache_dir={self.cache_dir}, job_id={self.job_id}, port={self.port}, status={self.status}, scheduler={self.scheduler}, provider={self.provider}, grace_period={self.grace_period}, mount={self.mount})"

    def get_profile(self) -> Optional[BlackfishProfile]:
        if self.scheduler == JobScheduler.Slurm:
            if self.user and self.home_dir and self.cache_dir:
                return SlurmProfile(
                    self.profile, self.host, self.user, self.home_dir, self.cache_dir
                )
        else:
            if self.home_dir and self.cache_dir:
                return LocalProfile(self.profile, self.home_dir, self.cache_dir)

        return None

    async def start(
        self,
        session: AsyncSession,
        app_config: State,
        container_options: BaseConfig,
        job_options: JobConfig,
    ) -> None:
        """Start the service with provided Slurm job and container options. Assumes running in attached state.

        Submits a Slurm job request, creates a new database entry and waits for
        the service to start.

        Args:
            container_options: a dict containing container options (see ContainerConfig).
            job_options: a dict containing job options (see JobConfig).

        Returns:
            None.
        """

        session.add(self)
        await session.flush()  # set self.id

        if self.scheduler == JobScheduler.Slurm:
            script_path = Path(
                os.path.join(app_config.HOME_DIR, "jobs", self.id.hex, "start.sh")
            )
            logger.debug(f"Generating job script and writing to {script_path}.")
            os.makedirs(script_path.parent)
            with open(script_path, "w") as f:
                try:
                    script = self.render_job_script(container_options, job_options)
                    f.write(script)
                except Exception as e:
                    logger.error(f"Unable to render launch script: {e}")
                    return

            logger.info("Starting service")

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
                self.status = ServiceStatus.SUBMITTED
                self.job_id = job_id
            else:
                profile = self.get_profile()
                if profile is None:
                    logger.error("Failed to start service: profile is missing.")
                    return

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
                    self.status = ServiceStatus.SUBMITTED
                    self.job_id = job_id
                except Exception as e:
                    logger.error(f"Failed to submit Slurm job: {e}")
                    return
        else:
            script_path = Path(
                os.path.join(app_config.HOME_DIR, "jobs", self.id.hex, "start.sh")
            )
            logger.debug(f"Generating launch script and writing to {script_path}.")
            os.makedirs(script_path.parent)

            # TODO: find port within start.sh and set after start-up OR find_port here and pass to render_job_script

            self.port = container_options.port
            self.provider = app_config.CONTAINER_PROVIDER
            with open(script_path, "w") as f:
                try:
                    match self.provider:
                        case ContainerProvider.Apptainer:
                            logger.debug("The container provider is Apptainer.")
                            job_id = str(uuid.uuid4())
                            script = self.render_job_script(
                                container_options, job_options
                            )
                        case ContainerProvider.Docker:
                            logger.debug("The container provider is Docker.")
                            script = self.render_job_script(
                                container_options, job_options
                            )
                    f.write(script)
                except Exception as e:
                    logger.error(e)
                    return
            logger.info("Attempting to start service locally...")
            try:
                res = subprocess.check_output(["bash", script_path.as_posix()])
            except Exception as e:
                logger.error(f"Failed to start service: {e}")
            if self.provider == ContainerProvider.Docker:
                job_id = res.decode("utf-8").strip().split()[-1][:12]
            self.status = ServiceStatus.SUBMITTED
            self.job_id = job_id

        logger.info("Adding service to database...")
        session.add(self)
        await session.flush()  # redundant flush provides service ID *now*

        logger.info(f"Created service {self.id}.")

    async def stop(
        self,
        session: AsyncSession,
        timeout: bool = False,
        failed: bool = False,
    ) -> None:
        """Stop the service. Assumes running in attached state.

        The default terminal state is STOPPED, which indicates that the service
        was stopped normally. Use the `failed` or `timeout` flags to indicate
        that the service stopped due to a Slurm job failure or timeout, resp.

        This process updates the database after stopping the service.

        Args:
            timeout: flag indicating the service timed out.
            failed: flag indicating the service Slurm job failed.
        """

        logger.info(f"Stopping service {self.id}")

        if self.status in [
            ServiceStatus.STOPPED,
            ServiceStatus.TIMEOUT,
            ServiceStatus.FAILED,
        ]:
            logger.warning(
                f"Service is already stopped (status={self.status}). Aborting stop."
            )
            return

        if self.job_id is None:
            raise Exception(
                f"Unable to stop service {self.id} because `job_id` is missing."
            )

        job = self.get_job(verbose=True)
        if job is not None:
            job.cancel()

        if self.scheduler == JobScheduler.Slurm:
            await self.close_tunnel(session)

        if timeout:
            self.status = ServiceStatus.TIMEOUT
        elif failed:
            self.status = ServiceStatus.FAILED
        else:
            self.status = ServiceStatus.STOPPED

    async def refresh(
        self, session: AsyncSession, app_config: State
    ) -> Optional[ServiceStatus]:
        """Update the service status. Assumes running in an attached state.

        Determines the service status by pinging the service and then checking
        the Slurm job state if the ping in unsuccessful. Updates the service
        database and returns the status.

        The status returned depends on the starting status because services in a
        "STARTING" status cannot transitionto an "UNHEALTHY" status. The status
        life-cycle is as follows:

            Slurm job submitted -> SUBMITTED
                Slurm job switches to pending -> PENDING
                    Slurm job switches to running -> STARTING
                        API ping successful -> HEALTHY
                        API ping unsuccessful -> STARTING
                        API ping unsuccessful and time limit exceeded -> TIMEOUT
                    Slurm job switches to failed -> FAILED
                Slurm job switches to failed -> FAILED

        A service that successfully starts will be in a HEALTHY status. The status
        remains HEALTHY as long as subsequent updates ping successfully.
        Unsuccessful pings will transition the service status to FAILED if the
        Slurm job has failed; TIMEOUT if the Slurm job times out; and
        UNHEALTHY otherwise.

        An UNHEALTHY service becomes HEALTHY if the update pings successfully.
        Otherwise, the service status changes to FAILED if the Slurm job has
        failed or TIMEOUT if the Slurm job times out.

        Services that enter a terminal status (FAILED, TIMEOUT or STOPPED)
        *cannot* be re-started.
        """

        logger.debug(
            f"Checking status of service {self.id}. Current status is {self.status}."
        )
        if self.status in [
            ServiceStatus.STOPPED,
            ServiceStatus.TIMEOUT,
            ServiceStatus.FAILED,
        ]:
            logger.debug(
                f"Service {self.id} is no longer running. Aborting status refresh."
            )
            return self.status

        if self.job_id is None:
            logger.debug(
                f"service {self.id} has no associated job. Aborting status refresh."
            )
            return self.status

        # The logic for cases below is quite similar and can be extracted into
        # reuseable functions in places, e.g., for running and failed jobs.
        job = self.get_job(verbose=True)
        if isinstance(job, SlurmJob):
            if job.state == JobState.PENDING:
                logger.debug(
                    f"Service {self.id} has not started. Setting status to PENDING."
                )
                self.status = ServiceStatus.PENDING
                return ServiceStatus.PENDING
            elif job.state == JobState.MISSING:
                logger.warning(
                    f"Service {self.id} has no job state (this service is likely"
                    " new or has expired). Aborting status update."
                )
                return self.status
            elif job.state == JobState.CANCELLED:
                logger.debug(
                    f"Service {self.id} has a cancelled job. Setting status to"
                    " STOPPED and stopping the service."
                )
                await self.stop(session)
                return ServiceStatus.STOPPED
            elif job.state == JobState.TIMEOUT:
                logger.debug(
                    f"Service {self.id} has a timed out job. Setting status to"
                    " TIMEOUT and stopping the service."
                )
                await self.stop(session, timeout=True)
                return ServiceStatus.TIMEOUT
            elif job.state == JobState.RUNNING:
                if self.port is None:
                    await self.open_tunnel(job=job)
                res = await self.ping()
                if res is not None and res.ok:
                    logger.debug(
                        f"Service {self.id} responded normally. Setting status to"
                        " HEALTHY."
                    )
                    self.status = ServiceStatus.HEALTHY
                    return ServiceStatus.HEALTHY
                else:
                    logger.debug(
                        f"Service {self.id} did not respond normally. Determining"
                        " status."
                    )
                    if self.status in [
                        ServiceStatus.SUBMITTED,
                        ServiceStatus.PENDING,
                        ServiceStatus.STARTING,
                    ]:
                        if self.created_at is None:
                            raise Exception("Service is missing value `created_at`.")
                        dt = datetime.now(timezone.utc) - self.created_at
                        logger.debug(f"Service created {dt.seconds} seconds ago.")
                        if dt.seconds > self.grace_period:
                            logger.debug(
                                f"Service {self.id} grace period exceeded. Setting"
                                " status to UNHEALTHY."
                            )
                            self.status = ServiceStatus.UNHEALTHY
                            return ServiceStatus.UNHEALTHY
                        else:
                            logger.debug(
                                f"Service {self.id} is still starting. Setting"
                                " status to STARTING."
                            )
                            self.status = ServiceStatus.STARTING
                            return ServiceStatus.STARTING
                    else:
                        logger.debug(
                            f"Service {self.id} is no longer starting. Setting"
                            " status to UNHEALTHY."
                        )
                        self.status = ServiceStatus.UNHEALTHY
                        return ServiceStatus.UNHEALTHY
            else:
                logger.debug(
                    f"Service {self.id} has a failed job"
                    f" (job.state={job.state}). Setting status to FAILED."
                )
                await self.stop(session, failed=True)  # stop will push to database
                return ServiceStatus.FAILED
        elif isinstance(job, LocalJob):
            if job.state == JobState.CREATED:
                logger.debug(
                    f"Service {self.id} has not started. Setting status to PENDING."
                )
                self.status = ServiceStatus.PENDING
                return ServiceStatus.PENDING
            elif job.state == JobState.MISSING:
                logger.warning(
                    f"Service {self.id} has no job state (this service is likely"
                    " new or has expired). Aborting status update."
                )
                return self.status
            elif job.state == JobState.EXITED:
                logger.debug(
                    f"Service {self.id} has a cancelled job. Setting status to"
                    " STOPPED and stopping the service."
                )
                await self.stop(session)
                return ServiceStatus.STOPPED
            elif job.state == JobState.RUNNING:
                res = await self.ping()
                if res is not None and res.ok:
                    logger.debug(
                        f"Service {self.id} responded normally. Setting status to"
                        " HEALTHY."
                    )
                    self.status = ServiceStatus.HEALTHY
                    return ServiceStatus.HEALTHY
                else:
                    logger.debug(
                        f"Service {self.id} did not respond normally. Determining"
                        " status."
                    )

                    if self.created_at is None:
                        raise Exception("Service is missing value `created_at`.")
                    dt = datetime.now(timezone.utc) - self.created_at
                    logger.debug(f"Service created {dt.seconds} seconds ago.")
                    if dt.seconds > self.grace_period:
                        logger.debug(
                            f"Service {self.id} grace period exceeded. Setting"
                            "status to UNHEALTHY."
                        )
                        self.status = ServiceStatus.UNHEALTHY
                        return ServiceStatus.UNHEALTHY
                    else:
                        logger.debug(
                            f"Service {self.id} is still starting. Setting"
                            " status to STARTING."
                        )
                        self.status = ServiceStatus.STARTING
                        return ServiceStatus.STARTING
            elif job.state in [JobState.RESTARTING, JobState.PAUSED]:
                raise NotImplementedError
            else:
                logger.debug(
                    f"Service {self.id} has a failed job"
                    f" (job.state={job.state}). Setting status to FAILED."
                )
                await self.stop(session, failed=True)  # stop will push to database
                return ServiceStatus.FAILED

        return None

    async def open_tunnel(self, job: SlurmJob) -> None:
        """Create an ssh tunnel to connect to the service. Assumes attached to session.

        After creation of the tunnel, the remote port is updated and recorded in the database.
        """

        if self.scheduler == JobScheduler.Slurm:
            if self.job_id is None:
                raise Exception(
                    f"Unable to open tunnel for service {self.id} because `job` is missing."
                )

            if job.port is None:
                raise Exception(
                    f"Unable to open tunnel for service {self.id} because"
                    " `job.port` is missing."
                )
            if job.node is None:
                raise Exception(
                    f"Unable to open tunnel for service {self.id} because"
                    " `job.node` is missing."
                )

            self.port = find_port()
            if self.port is None:
                raise Exception(
                    f"Unable to find an available local port for service {self.id}."
                )

            if self.host == "localhost":
                _ = subprocess.check_output(
                    [
                        "ssh",
                        "-N",
                        "-f",
                        "-L",
                        f"{self.port}:{job.node}:{job.port}",  # e.g., localhost:8080 -> della-h3401:5432
                        f"{self.user}@{job.node}",
                    ]
                )
                logger.debug(
                    f"Established tunnel localhost:{self.port} -> {job.node}:{job.port}"
                )
            else:
                _ = subprocess.check_output(
                    [
                        "ssh",
                        "-N",
                        "-f",
                        "-L",
                        f"{self.port}:{job.node}:{job.port}",
                        f"{self.user}@{self.host}",  # e.g., tom123@della.princeton.edu
                    ]
                )
                logger.debug(
                    f"Established tunnel localhost:{self.port} ->"
                    f" {self.host}:{job.port}"
                )  # noqa: E501
        else:
            logger.error("Service job scheduler variety should be Slurm.")
            raise NotImplementedError

    async def close_tunnel(self, session: AsyncSession) -> None:
        """Kill the ssh tunnel connecting to the API. Assumes attached to session.

        Finds all processes named "ssh" and kills any associated with the service's local port.

        This is equivalent to the shell command:

        ```shell
        pid = $(ps aux | grep ssh | grep 8080")
        kill $pid
        ```
        """
        ps = [p for p in psutil.process_iter() if p.name() == "ssh"]
        for p in ps:
            pid = p.pid
            try:
                cs = p.net_connections()
            except psutil.AccessDenied:
                logger.warning(f"Access denied to process {p}.")
                continue
            for c in cs:
                if c.laddr.port == self.port:
                    try:
                        p.kill()
                        logger.info(f"Closed tunnel on port {self.port} (pid={pid})")
                        self.port = None
                        return
                    except psutil.NoSuchProcess as e:
                        logger.warning(
                            f"Failed to kill process {pid}: (sqlite.Error) {e}"
                        )

        logger.warning(
            f"Failed to close tunnel on port {self.port} (pid={pid}). Setting port to None."
        )
        self.port = None

    def get_job(self, verbose: bool = False) -> Job | None:
        """Fetch the job backing the service."""

        job: Job

        if self.scheduler == JobScheduler.Slurm:
            if self.job_id and self.user and self.home_dir:
                job = SlurmJob(
                    job_id=int(self.job_id),
                    user=self.user,
                    host=self.host,
                    name=self.name,
                    data_dir=os.path.join(self.home_dir, "jobs", self.id.hex),
                )
            else:
                return None
        else:
            if self.job_id and self.provider:
                job = LocalJob(self.job_id, self.provider, self.name)
            else:
                return None

        job.update(verbose=verbose)
        return job

    def render_job_script(
        self,
        container_config: BaseConfig,
        job_config: JobConfig,
    ) -> str:
        env = Environment(loader=PackageLoader("app", "templates"))
        template = env.get_template(f"{self.image}_{self.scheduler or 'local'}.sh")
        job_script = template.render(
            uuid=self.id.hex,
            name=self.name,
            model=self.model,
            provider=self.provider,
            profile=self.get_profile(),
            container_config=container_config,
            job_config=job_config,
            mount=self.mount,
        )

        return job_script

    async def ping(self) -> requests.Response | None:
        logger.debug(f"Pinging service {self.id}")
        try:
            res = requests.get(f"http://localhost:{self.port}/health")
            return res
        except Exception as e:
            logger.error(f"Failed to check health: {e}")
            return None
