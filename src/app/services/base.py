import random
import subprocess
import os
import psutil
from datetime import datetime
from typing import Optional
from requests import Response
from dataclasses import dataclass, asdict, replace

from sqlalchemy.orm import Mapped
from sqlalchemy.ext.asyncio import AsyncSession
from advanced_alchemy.base import UUIDAuditBase

from litestar.datastructures import State

from app.job import Job
from app.logger import logger
from app.utils import find_port


@dataclass
class ContainerConfig:

    def data(self) -> dict:
        return {
            k: v
            for k, v in filter(lambda item: item[1] is not None, asdict(self).items())
        }

    def replace(self, changes: dict) -> None:
        return replace(self, **changes)


class Service(UUIDAuditBase):
    __tablename__ = "service"

    name: Mapped[str]
    endpoints: Mapped[Optional[str]]
    image: Mapped[str]
    model: Mapped[str]
    status: Mapped[Optional[str]]
    user: Mapped[Optional[str]]
    host: Mapped[str]
    port: Mapped[Optional[int]]
    # TODO: remote_port: Mapped[Optional[int]]
    job_type: Mapped[str]
    job_id: Mapped[Optional[str]]
    grace_period: Mapped[Optional[int]] = 180

    __mapper_args__ = {
        "polymorphic_on": "image",
        "polymorphic_identity": "base",
    }

    def __repr__(self) -> str:
        return f"Service(id={self.id}, name={self.name}, status={self.status}, host={self.host}, image={self.image})"

    async def start(
        self,
        session: AsyncSession,
        state: State,
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
        logger.debug(f"Generating job script and writing to {state.BLACKFISH_HOME_DIR}.")
        with open(os.path.join(state.BLACKFISH_HOME_DIR, "start.sh"), "w") as f:
            try:
                script = self.launch_script(container_options, job_options)
                f.write(script)
            except Exception as e:
                logger.error(e)

        logger.info("Starting service")
        if self.job_type == "local":
            raise NotImplementedError
        elif self.job_type == "slurm":
            if self.host == "localhost":
                logger.debug("submitting batch job on login node.")
                res = subprocess.check_output(
                    ["sbatch", os.path.join(state.BLACKFISH_HOME_DIR, "start.sh")]
                )
            else:
                logger.debug(
                    f"Copying job script to {self.host}:{job_options['home_dir']}."
                )
                _ = subprocess.check_output(
                    [
                        "scp",
                        os.path.join(state.BLACKFISH_HOME_DIR, "start.sh"),
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

            self.status = "SUBMITTED"
            self.job_id = job_id
        elif self.job_type == "ec2":
            raise NotImplementedError
        elif self.job_type == "test":
            if self.host == "localhost":
                logger.debug("[TEST] submitting batch job on login node.")
            else:
                logger.debug(f"[TEST] copying job script to {job_options['home_dir']}.")
                logger.debug(f"[TEST] submitting batch job to {self.user}@{self.host}.")

            self.status = "SUBMITTED"
            self.job_id = f"test-{random.randint(10_000, 11_000)}"
        else:
            raise Exception("Job type should be one of: local, slurm, ec2, test.")

        logger.info("Adding service to database")
        session.add(self)
        await session.flush()  # redundant flush provides service ID *now*

        logger.info(f"Created service {self.id}.")

    async def stop(
        self,
        session: AsyncSession,
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

        if self.status in ["STOPPED", "TIMEOUT", "FAILED"]:
            logger.warn(f"Service is already stopped (status={self.status}). Aborting stop.")
            return

        if self.job_type == "local":
            raise NotImplementedError
        elif self.job_type == "slurm":
            if self.job_id is None:
                raise Exception(
                    f"Unable to stop service {self.id} because `job` is missing."
                )

            job = self.get_job()
            job.cancel()
            await self.close_tunnel(session)
        elif self.job_type == "ec2":
            raise NotImplementedError
        elif self.job_type == "test":
            raise NotImplementedError
        else:
            raise Exception  # TODO: JobTypeError

        if timeout:
            self.status = "TIMEOUT"
        elif failed:
            self.status = "FAILED"
        else:
            self.status = "STOPPED"

    async def refresh(self, session: AsyncSession):
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
            f"Checking status of service {self.id}. Current status is" f" {self.status}."
        )
        if self.status in [
            "STOPPED",
            "TIMEOUT",
            "FAILED",
        ]:
            logger.debug(
                f"Service {self.id} is no longer running. Aborting status refresh."
            )
            return self.status

        if self.job_type == "local":
            raise NotImplementedError
        elif self.job_type == "slurm":
            if self.job_id is None:
                logger.debug(
                    f"service {self.id} has no associated job. Aborting status refresh."
                )
                return self.status

            job = self.get_job()  # or job_status = self.get_job_state()

            if job.state == "PENDING":
                logger.debug(
                    f"Service {self.id} has not started. Setting status to PENDING."
                )
                self.status = "PENDING"
                return "PENDING"
            elif job.state == "MISSING":
                logger.warning(
                    f"service {self.id} has no job state (this service is likely"
                    " new or has expired). Aborting status update."
                )
                return self.status
            elif job.state is not None and "CANCELLED" in job.state:
                logger.debug(
                    f"Service {self.id} has a cancelled job. Setting status to"
                    " STOPPED and stopping the service."
                )
                await self.stop(session)
                # if push:
                #     self.push(session, updated=datetime.now())
                return "STOPPED"
            elif job.state == "TIMEOUT":
                logger.debug(
                    f"Service {self.id} has a timed out job. Setting status to"
                    " TIMEOUT and stopping the service."
                )
                await self.stop(session, timeout=True)
                # if push:
                #     self.push(session, updated=datetime.now())
                return "TIMEOUT"
            elif job.state == "RUNNING":
                if self.port is None:
                    self.open_tunnel(session)
                res = self.ping()
                if res["ok"]:
                    logger.debug(
                        f"service {self.id} responded normally. Setting status to"
                        " HEALTHY."
                    )
                    self.status = "HEALTHY"
                    return "HEALTHY"
                else:
                    logger.debug(
                        f"service {self.id} did not respond normally. Determining"
                        " status."
                    )
                    if self.status in [
                        "SUBMITTED",
                        "PENDING",
                        "STARTING",
                    ]:
                        if self.created is None:
                            raise Exception("Service is missing value `created`.")
                        dt = datetime.now() - self.created
                        if dt.seconds > self.start_period:
                            logger.debug(
                                f"service {self.id} grace period exceeded. Setting"
                                "status to UNHEALTHY."
                            )
                            self.status = "UNHEALTHY"
                            return "UNHEALTHY"
                        else:
                            logger.debug(
                                f"service {self.id} is still starting. Setting"
                                " status to STARTING."
                            )
                            self.status = "STARTING"
                            return "STARTING"
                    else:
                        logger.debug(
                            f"service {self.id} is no longer starting. Setting"
                            " status to UNHEALTHY."
                        )
                        self.status = "UNHEALTHY"
                        return "UNHEALTHY"
            else:
                logger.debug(
                    f"service {self.id} has a failed job"
                    f" (job.state={job.state}). Setting status to FAILED."
                )
                await self.stop(session, failed=True)  # stop will push to database
                return "FAILED"
        elif self.job_type == "ec2":
            raise NotImplementedError
        elif self.job_type == "test":
            logger.warn("Refresh not implemented for job type 'test'. Skipping.")
        else:
            raise Exception  # TODO: JobTypeError

    async def open_tunnel(self, session: AsyncSession) -> None:
        """Create an ssh tunnel to connect to the service. Assumes attched to session.

        After creation of the tunnel, the remote port is updated and recorded in the database.
        """

        if self.job_id is None:
            raise Exception(
                f"Unable to open tunnel for service {self.id} because `job` is"
                " missing."
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
                        f"{self.port}:{job.node}:{job.port}",
                        f"{self.user}@{job.node}",
                    ]
                )
                logger.info(
                    f"established tunnel localhost:{self.port} -> {job.node}:{job.port}"
                )
            else:
                _ = subprocess.check_output(
                    [
                        "ssh",
                        "-N",
                        "-f",
                        "-L",
                        f"{self.port}:{job.node}:{job.port}",
                        f"{self.user}@{self.host}",
                    ]
                )
                logger.info(
                    f"established tunnel localhost:{self.port} -> {self.host}:{job.port}"
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
                        logger.info(f"closed tunnel on port {self.port} (pid={pid})")
                    except psutil.NoSuchProcess as e:
                        logger.warning(
                            f"unable to kill process {pid} sqlite.Error({e})"
                        )

        self.port = None

    def get_job(self) -> Job:
        """Fetch the Slurm job backing the service."""
        job = Job(self.job_id, self.user, self.host)
        job.update()
        return job

    def launch_script(self, container_options: dict, job_options: dict) -> str:
        raise NotImplementedError(
            "`launch_script` should only be called on subtypes of Service"
        )

    def call(self, inputs, **kwargs) -> Response:
        raise NotImplementedError("`call` should only be called on subtypes of Service")