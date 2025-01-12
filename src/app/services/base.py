import subprocess
import os
import uuid
import psutil
from datetime import datetime, timezone
from typing import Optional
import requests
from dataclasses import dataclass, asdict, replace
from enum import StrEnum, auto

from sqlalchemy.orm import Mapped
from sqlalchemy.ext.asyncio import AsyncSession
from advanced_alchemy.base import UUIDAuditBase

from litestar.datastructures import State

from app.job import Job, JobState, SlurmJob, LocalJob
from app.logger import logger
from app.utils import find_port


@dataclass
class ContainerConfig:
    provider: Optional[str] = "apptainer"

    def data(self) -> dict:
        return {
            k: v
            for k, v in filter(lambda item: item[1] is not None, asdict(self).items())
        }

    def replace(self, changes: dict) -> None:
        return replace(self, **changes)


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
    endpoints: Mapped[Optional[str]]
    image: Mapped[str]
    model: Mapped[str]
    profile: Mapped[str]
    status: Mapped[Optional[str]]
    user: Mapped[Optional[str]]
    host: Mapped[str]
    port: Mapped[Optional[int]]
    job_type: Mapped[str]
    job_id: Mapped[Optional[str]]
    grace_period: Mapped[Optional[int]] = 180
    mounts: Mapped[Optional[str]]

    __mapper_args__ = {
        "polymorphic_on": "image",
        "polymorphic_identity": "base",
    }

    def __repr__(self) -> str:
        return (
            f"Service(id={self.id}, name={self.name}, status={self.status},"
            f" host={self.host}, image={self.image})"
        )

    async def start(
        self,
        session: AsyncSession,
        config: State,
        container_options: dict,
        job_options: dict,
    ):
        """Start the service with provided Slurm job and container options. Assumes running in attached state.

        Submits a Slurm job request, creates a new database entry and waits for
        the service to start.

        Args:
            container_options: a dict containing container options (see ContainerConfig).
            job_options: a dict containing job options (see JobConfig).

        Returns:
            None.
        """

        if self.job_type == "local":
            logger.debug(f"Generating launch script and writing to {config.HOME_DIR}.")
            self.port = container_options["port"]
            container_options["provider"] = config.CONTAINER_PROVIDER
            with open(os.path.join(config.HOME_DIR, "start.sh"), "w") as f:
                try:
                    if container_options["provider"] == "apptainer":
                        logger.debug("The container provider is Apptainer.")
                        job_id = str(uuid.uuid4())
                        script = self.launch_script(
                            container_options, job_options, job_id
                        )
                    elif container_options["provider"] == "docker":
                        logger.debug("The container provider is Docker.")
                        script = self.launch_script(container_options, job_options)
                    f.write(script)
                except Exception as e:
                    logger.error(e)
            logger.info("Starting local service")
            res = subprocess.check_output(
                ["bash", os.path.join(config.HOME_DIR, "start.sh")]
            )
            if container_options["provider"] == "docker":
                job_id = res.decode("utf-8").strip().split()[-1][:12]
            self.status = ServiceStatus.SUBMITTED
            self.job_id = job_id
        elif self.job_type == "slurm":
            logger.debug(f"Generating job script and writing to {config.HOME_DIR}.")
            with open(os.path.join(config.HOME_DIR, "start.sh"), "w") as f:
                try:
                    script = self.launch_script(container_options, job_options)
                    f.write(script)
                except Exception as e:
                    logger.error(f"Unable to render launch script: {e}")

            logger.info("Starting service")

            if self.host == "localhost":
                logger.debug("submitting batch job on login node.")
                res = subprocess.check_output(
                    ["sbatch", os.path.join(config.HOME_DIR, "start.sh")]
                )
            else:
                logger.debug(
                    f"Copying job script to {self.host}:{job_options['home_dir']}."
                )
                _ = subprocess.check_output(
                    [
                        "scp",
                        os.path.join(config.HOME_DIR, "start.sh"),
                        (
                            f"{self.user}@{self.host}:{os.path.join(job_options['home_dir'], 'start.sh')}"
                        ),
                    ]
                )
                logger.debug(f"Submitting batch job to {self.user}@{self.host}.")
                res = subprocess.check_output(
                    [
                        "ssh",
                        f"{self.user}@{self.host}",
                        "sbatch",
                        "--chdir",
                        f"{job_options['home_dir']}",
                        f"{job_options['home_dir']}/start.sh",
                    ]
                )

            job_id = res.decode("utf-8").strip().split()[-1]

            self.status = ServiceStatus.SUBMITTED
            self.job_id = job_id
        elif self.job_type == "ec2":
            raise NotImplementedError
        else:
            raise Exception("Job type should be one of: local, slurm.")

        logger.info("Adding service to database")
        session.add(self)
        await session.flush()  # redundant flush provides service ID *now*

        logger.info(f"Created service {self.id}.")

    async def stop(
        self,
        session: AsyncSession,
        config: State,
        delay: int = 0,
        timeout: bool = False,
        failed: bool = False,
    ):
        """Stop the service after `delay` seconds. Assumes running in attached state.

        The default terminal state is STOPPED, which indicates that the service
        was stopped normally. Use the `failed` or `timeout` flags to indicate
        that the service stopped due to a Slurm job failure or timeout, resp.

        This process updates the database after stopping the service.

        Args:
            delay: The number of seconds to wait before stopping the service.
            timeout: A flag indicating the service timed out.
            failed: A flag indicating the service Slurm job failed.
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

        if self.job_type == "local":
            job = self.get_job(config.CONTAINER_PROVIDER)
            job.cancel()
        elif self.job_type == "slurm":
            job = self.get_job()
            job.cancel()
            await self.close_tunnel(session)
        elif self.job_type == "ec2":
            raise NotImplementedError
        else:
            raise Exception  # TODO: JobTypeError

        if timeout:
            self.status = ServiceStatus.TIMEOUT
        elif failed:
            self.status = ServiceStatus.FAILED
        else:
            self.status = ServiceStatus.STOPPED

    async def refresh(self, session: AsyncSession, config: State):
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

        if self.job_type == "local":
            job = self.get_job(config.CONTAINER_PROVIDER)
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
                await self.stop(session, config)
                return ServiceStatus.STOPPED
            elif job.state == JobState.RUNNING:
                res = await self.ping()
                if res["ok"]:
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
                await self.stop(
                    session, config, failed=True
                )  # stop will push to database
                return ServiceStatus.FAILED
        elif self.job_type == "slurm":
            job = self.get_job()
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
                await self.stop(session, config)
                return ServiceStatus.STOPPED
            elif job.state == JobState.TIMEOUT:
                logger.debug(
                    f"Service {self.id} has a timed out job. Setting status to"
                    " TIMEOUT and stopping the service."
                )
                await self.stop(session, config, timeout=True)
                return ServiceStatus.TIMEOUT
            elif job.state == JobState.RUNNING:
                if self.port is None:
                    await self.open_tunnel(session)
                res = await self.ping()
                if res["ok"]:
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
                await self.stop(
                    session, config, failed=True
                )  # stop will push to database
                return ServiceStatus.FAILED
        elif self.job_type == "ec2":
            raise NotImplementedError
        else:
            raise Exception  # TODO: JobTypeError

    async def open_tunnel(self, session: AsyncSession) -> None:
        """Create an ssh tunnel to connect to the service. Assumes attached to session.

        After creation of the tunnel, the remote port is updated and recorded in the database.
        """

        if self.job_id is None:
            raise Exception(
                f"Unable to open tunnel for service {self.id} because `job` is missing."
            )
        job = self.get_job()
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
            raise Exception(f"Unable to find an available port for service {self.id}.")

        if self.job_type == "slurm":
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
            cs = p.connections()
            for c in cs:
                if c.laddr.port == self.port:
                    try:
                        p.kill()
                        logger.info(f"Closed tunnel on port {self.port} (pid={pid})")
                    except psutil.NoSuchProcess as e:
                        logger.warning(
                            f"Failed to kill process {pid} sqlite.Error({e})"
                        )

        self.port = None

    def get_job(self, provider: str = None) -> Job:
        """Fetch the Slurm job backing the service."""
        if self.job_type == "slurm":
            job = SlurmJob(self.job_id, self.user, self.host)
        elif self.job_type == "local":
            job = LocalJob(self.job_id, provider)
        job.update()
        return job

    def launch_cmd(self, container_options: dict, job_options: dict) -> str:
        raise NotImplementedError(
            "`launch_cmd` should only be called on subtypes of Service"
        )

    def launch_script(self, container_options: dict, job_options: dict) -> str:
        raise NotImplementedError(
            "`launch_script` should only be called on subtypes of Service"
        )

    async def call(self, inputs, **kwargs) -> dict:
        raise NotImplementedError("`call` should only be called on subtypes of Service")

    async def ping(self) -> dict:
        logger.debug(f"Pinging service {self.id}")
        try:
            res = requests.get(f"http://127.0.0.1:{self.port}/health")
            logger.debug(f"Response status code: {res.status_code}")
            return {"ok": res.ok}
        except Exception as e:
            return {"ok": False, "error": e}
