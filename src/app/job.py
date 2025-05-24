import os
import time
import json
import subprocess
from dataclasses import dataclass

from enum import StrEnum, auto
from typing import Optional, Union
from app.logger import logger
from app.config import ContainerProvider


class JobState(StrEnum):
    BOOT_FAIL = auto()  # terminated due to launch failure (BF)
    CANCELLED = auto()  # explicitly cancelled by the user or system administrator (CA)
    COMPLETED = (
        auto()
    )  # terminated all processes on all nodes with exit code of zero (CD)
    DEADLINE = auto()  # terminated on deadline (DL)
    FAILED = auto()  # terminated with non-zero exit code or other failure condition (F)
    NODE_FAIL = auto()  # terminated due to failure of one or more allocated nodes (NF)
    OUT_OF_MEMORY = auto()  # Job experienced out of memory error (OOM)
    CREATED = auto()
    PENDING = auto()  # Job is awaiting resource allocation (PD)
    PREEMPTED = auto()  # Job terminated due to preemption (PR)
    RUNNING = auto()  # Job currently has an allocation (R)
    REQUEUED = auto()  # Job was requeued (RQ)
    RESIZING = auto()  # Job is about to change size (RS)
    REVOKED = auto()  # removed from cluster due to other cluster starting the job (RV)
    SUSPENDED = auto()  # has an allocation, but execution has been suspended (S)
    TIMEOUT = auto()  # terminated upon reaching its time limit (TO)
    RESTARTING = auto()
    PAUSED = auto()
    EXITED = auto()
    MISSING = auto()
    STOPPED = auto()


class JobScheduler(StrEnum):
    Slurm = auto()


@dataclass
class LocalJobConfig:
    """Job configuration for running a service locally."""

    gres: Optional[bool] = False


@dataclass
class SlurmJobConfig:
    """Job configuration for running a service as a Slurm job."""

    name: Optional[str]
    time: str = "00:30:00"
    nodes: int = 1
    ntasks_per_node: int = 8
    mem: int = 16
    gres: int = 0  # i.e., gpu:<gres>
    partition: Optional[str] = None  # e.g., mig
    constraint: Optional[str] = None  # e.g., gpu80


JobConfig = Union[LocalJobConfig, SlurmJobConfig]


@dataclass
class Job:
    def cancel(self) -> None:
        raise NotImplementedError()

    def update(self, verbose: bool = False) -> Optional[str]:
        raise NotImplementedError()

    def remove(self) -> None:
        raise NotImplementedError()


def parse_state(res: bytes) -> JobState:
    if res == b"":
        return JobState.MISSING

    lowered = res.decode("utf-8").strip().strip("'").lower()

    if "cancelled" in lowered:
        return JobState.CANCELLED
    else:
        return JobState(lowered)


@dataclass
class SlurmJob(Job):
    """A light-weight Slurm job dataclass."""

    job_id: int
    user: str
    host: str
    data_dir: str
    name: Optional[str] = None
    node: Optional[str] = None
    port: Optional[int] = None
    state: Optional[JobState] = None
    options: Optional[JobConfig] = None

    def is_local(self) -> bool:
        return self.host == "localhost"

    def update(self, verbose: bool = False) -> Optional[str]:
        """Attempt to update the job state from Slurm accounting and return the new
        state (or current state if the update fails).

        If the job state switches from PENDING or MISSING to RUNNING, also update
        the job node and port.

        This method logs a warning if the update fails, but does not raise an exception.
        """
        if verbose:
            logger.debug(f"Updating job state (job_id={self.job_id}).")
        try:
            if self.is_local():
                res = subprocess.check_output(
                    [
                        "sacct",
                        "-n",
                        "-P",
                        "-X",
                        "-u",
                        self.user,
                        "-j",
                        str(self.job_id),
                        "-o",
                        "State",
                    ]
                )
            else:
                res = subprocess.check_output(
                    [
                        "ssh",
                        f"{self.user}@{self.host}",
                        "sacct",
                        "-n",
                        "-P",
                        "-X",
                        "-u",
                        self.user,
                        "-j",
                        str(self.job_id),
                        "-o",
                        "State",
                    ]
                )

            new_state = parse_state(res)
            if verbose:
                logger.debug(
                    f"The current job state is: {new_state} (job_id=${self.job_id})"
                )
            if (
                self.state in [None, JobState.MISSING, JobState.PENDING]
                and new_state == JobState.RUNNING
                and self.node is None
                and self.port is None
            ):
                if verbose:
                    logger.debug(
                        f"Job state updated from {self.state} to RUNNING"
                        f" (job_id={self.job_id}). Fetching node and port."
                    )
                self.fetch_node()
                self.fetch_port()
            elif self.state is not None and self.state != new_state:
                if verbose:
                    logger.debug(
                        f"Job state updated from {self.state} to {new_state}"
                        f" (job_id={self.job_id})."
                    )
            self.state = new_state
        except subprocess.CalledProcessError as e:
            logger.warning(
                f"Failed to update job state (job_id={self.job_id},"
                f" code={e.returncode})."
            )

        return self.state

    def fetch_node(self) -> Optional[str]:
        """Attempt to update the job node from Slurm accounting and return the new
        node (or the current node if the update fails).

        This method logs a warning if the update fails, but does not raise an exception.
        """
        logger.debug(f"Fetching node for job {self.job_id}.")
        try:
            if self.is_local():
                res = subprocess.check_output(
                    [
                        "sacct",
                        "-n",
                        "-P",
                        "-X",
                        "-u",
                        self.user,
                        "-j",
                        str(self.job_id),
                        "-o",
                        "NodeList",
                    ]
                )
            else:
                res = subprocess.check_output(
                    [
                        "ssh",
                        f"{self.user}@{self.host}",
                        "sacct",
                        "-n",
                        "-P",
                        "-X",
                        "-u",
                        self.user,
                        "-j",
                        str(self.job_id),
                        "-o",
                        "NodeList",
                    ]
                )

            self.node = None if res == b"" else res.decode("utf-8").strip()
            logger.debug(f"Job {self.job_id} node set to {self.node}.")
        except subprocess.CalledProcessError as e:
            logger.warning(
                f"Failed to update job node (job_id={self.job_id},"
                f" code={e.returncode})."
            )

        return self.node

    def fetch_port(self) -> Optional[int]:
        """Attempt to update the job port and return the new port (or the current
        port if the update fails)

        The job port is stored as a directory in the remote Blackfish home when a port
        is assigned to a service container.

        This method logs a warning if the update fails, but does not raise an exception.
        """
        logger.debug(f"Fetching port for job {self.job_id}.")
        try:
            if self.is_local():
                res = subprocess.check_output(
                    [
                        "ls",
                        os.path.join(self.data_dir, str(self.job_id)),
                    ]
                )
            else:
                res = subprocess.check_output(
                    [
                        "ssh",
                        f"{self.user}@{self.host}",
                        "ls",
                        os.path.join(self.data_dir, str(self.job_id)),
                    ]
                )
            self.port = None if res == b"" else int(res.decode("utf-8").strip())
            logger.debug(f"Job {self.job_id} port set to {self.port}")
        except subprocess.CalledProcessError as e:
            logger.warning(
                f"Failed to update job port (job_id={self.job_id},"
                f" code={e.returncode})."
            )

        return self.port

    def wait(self, period: int = 5) -> dict[str, bool]:
        """Wait for the job to start, re-checking the job's status every `period` seconds."""

        logger.debug(f"waiting for job {self.job_id} to start")
        time.sleep(period)  # wait for slurm to accept job
        while True:
            self.update()
            if self.state == JobState.MISSING:
                logger.debug(
                    f"job {self.job_id} state is missing. Re-trying in"
                    f" {period} seconds."
                )
            elif self.state == JobState.PENDING:
                logger.debug(
                    f"job {self.job_id} is pending. Re-trying in {period} seconds."
                )
            elif self.state == JobState.RUNNING:
                logger.debug(f"job {self.job_id} is running.")
                self.fetch_node()
                self.fetch_port()
                return {"ok": True}
            else:
                logger.debug(f"job {self.job_id} failed (state={self.state}).")
                return {"ok": False}

            time.sleep(period)

    def cancel(self) -> None:
        """Cancel a Slurm job by issuing the `scancel` command on the remote host.

        This method logs a warning if the update fails, but does not raise an exception.
        """
        try:
            logger.debug(f"Canceling job {self.job_id}")
            if self.is_local():
                subprocess.check_output(["scancel", str(self.job_id)])
            else:
                subprocess.check_output(
                    ["ssh", f"{self.user}@{self.host}", "scancel", str(self.job_id)]
                )
        except subprocess.CalledProcessError as e:
            logger.warning(
                f"Failed to cancel job (job_id={self.job_id}, code={e.returncode})."
            )

    def remove(self) -> None:
        pass


@dataclass
class LocalJob(Job):
    """A light-weight local job dataclass."""

    job_id: str
    provider: ContainerProvider  # docker or apptainer
    name: Optional[str] = None
    state: Optional[str] = (
        None  # "created", "running", "restarting", "exited", "paused", "dead"
    )
    options: Optional[JobConfig] = None

    def update(self, verbose: bool = False) -> Optional[str]:
        if verbose:
            logger.debug(f"Updating job state (job_id={self.job_id})")
        try:
            if self.provider == ContainerProvider.Docker:
                res = subprocess.check_output(
                    [
                        "docker",
                        "inspect",
                        f"{self.job_id}",
                        "--format='{{ .State.Status }}'",  # or {{ json .State }}
                    ]
                )
                new_state = parse_state(res)
                if verbose:
                    logger.debug(
                        f"The current job state is: {new_state} (job_id={self.job_id})"
                    )
                if self.state is not None and self.state != new_state:
                    if verbose:
                        logger.debug(
                            f"Job state updated from {self.state} to {new_state}"
                            f" (job_id={self.job_id})"
                        )
                self.state = new_state
            elif self.provider == ContainerProvider.Apptainer:
                res = subprocess.check_output(
                    ["apptainer", "instance", "list", "--json", f"{self.name}"]
                )
                body = json.loads(res)
                if body["instances"] == []:
                    new_state = JobState.STOPPED
                else:
                    new_state = JobState.RUNNING

                if verbose:
                    logger.debug(
                        f"The current job state is: {new_state} (job_id={self.job_id})"
                    )
                if self.state is not None and self.state != new_state:
                    if verbose:
                        logger.debug(
                            f"Job state updated from {self.state} to {new_state}"
                            f" (job_id={self.job_id})."
                        )
                self.state = new_state
        except subprocess.CalledProcessError as e:
            logger.warning(
                f"Failed to update job state (job_id={self.job_id},"
                f" code={e.returncode})."
            )

        return self.state

    def cancel(self) -> None:
        try:
            logger.debug(f"Canceling job {self.job_id}")
            if self.provider == ContainerProvider.Docker:
                subprocess.check_output(
                    ["docker", "container", "stop", f"{self.job_id}"]
                )
            elif self.provider == ContainerProvider.Apptainer:
                subprocess.check_output(
                    ["apptainer", "instance", "stop", f"{self.name}"]
                )
        except subprocess.CalledProcessError as e:
            logger.warning(
                f"Failed to cancel job (job_id={self.job_id}, code={e.returncode})."
            )

    def remove(self) -> None:
        try:
            logger.debug(f"Removing job {self.job_id}")
            if self.provider == ContainerProvider.Docker:
                subprocess.check_output(["docker", "container", "rm", f"{self.job_id}"])
            elif self.provider == ContainerProvider.Apptainer:
                logger.info("Nothing to remove (provider is Apptainer). Skipping.")
        except subprocess.CalledProcessError as e:
            logger.warning(
                f"Failed to remove job (job_id={self.job_id}, code={e.returncode})."
            )
