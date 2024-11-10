import os
import time
import json
import subprocess
from dataclasses import dataclass, asdict, replace

from enum import Enum
from typing import Optional
from app.logger import logger


class JobState(Enum):
    "BOOT_FAIL"  # Job terminated due to launch failure (BF)

    "CANCELLED"  # Job was explicitly cancelled by the user or system administrator (CA)
    "COMPLETED"  # Job terminated all processes on all nodes with exit code of zero (CD)
    "DEADLINE"  # Job terminated on deadline (DL)
    "FAILED"  # Job terminated with non-zero exit code or other failure condition (F)
    "NODE_FAIL"  # Job terminated due to failure of one or more allocated nodes (NF)
    "OUT_OF_MEMORY"  # Job experienced out of memory error (OOM)
    "PENDING"  # Job is awaiting resource allocation (PD)
    "PREEMPTED"  # Job terminated due to preemption (PR)
    "RUNNING"  # Job currently has an allocation (R)
    "REQUEUED"  # Job was requeued (RQ)
    "RESIZING"  # Job is about to change size (RS)
    "REVOKED"  # Sibling removed from cluster due to other cluster starting the job (RV)
    "SUSPENDED"  # Job has an allocation, but execution has been suspended (S)
    "TIMEOUT"  # Job terminated upon reaching its time limit (TO)


@dataclass
class JobConfig:
    def data(self) -> dict:
        return {
            k: v
            for k, v in filter(lambda item: item[1] is not None, asdict(self).items())
        }

    def replace(self, changes: dict) -> None:
        return replace(self, **changes)


@dataclass
class LocalJobConfig(JobConfig):
    """Job configuration for running a service locally."""

    user: Optional[str] = None
    home_dir: Optional[str] = None  # e.g., /home/{user}/.blackfish
    cache_dir: Optional[str] = None  # e.g., /scratch/gpfs/models
    model_dir: Optional[str] = None  # e.g., /scratch/gpfs/models
    gres: Optional[bool] = False


@dataclass
class SlurmJobConfig(JobConfig):
    """Job configuration for running a service as a Slurm job."""

    host: Optional[str] = None
    user: Optional[str] = None
    name: Optional[str] = "blackfish"
    time: Optional[str] = "00:15:00"
    nodes: Optional[int] = 1
    ntasks_per_node: Optional[int] = 8
    mem: Optional[int] = 16
    gres: Optional[int] = 0  # i.e., gpu:<gres>
    partition: Optional[str] = None  # e.g., mig
    constraint: Optional[str] = None  # e.g., gpu80
    home_dir: Optional[str] = None  # e.g., /home/{user}/.blackfish
    cache_dir: Optional[str] = None  # e.g., /scratch/gpfs/{user}/.blackfish
    model_dir: Optional[str] = None  # e.g., /scratch/gpfs/{user}/.blackfish/models


@dataclass
class EC2JobConfig(JobConfig): ...


@dataclass
class Job:
    """A light-weight Slurm job dataclass."""

    job_id: int
    user: str
    host: str
    name: Optional[str] = None
    node: Optional[str] = None
    port: Optional[int] = None
    state: Optional[str] = None
    options: Optional[JobConfig] = None

    def update(self) -> Optional[str]:
        """Attempt to update the job state from Slurm accounting and return the new
        state (or current state if the update fails).

        If the job state switches from PENDING or MISSING to RUNNING, also update
        the job node and port.

        This method logs a warning if the update fails, but does not raise an exception.
        """
        logger.debug(f"Updating job state (job_id={self.job_id}).")
        try:
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

            new_state = "MISSING" if res == b"" else res.decode("utf-8").strip()
            logger.debug(
                f"The current job state is: {new_state} (job_id=${self.job_id})"
            )
            if (
                self.state in [None, "MISSING", "PENDING"]
                and new_state == "RUNNING"
                and self.node is None
                and self.port is None
            ):
                logger.debug(
                    f"Job state updated from {self.state} to RUNNING"
                    f" (job_id={self.job_id}). Fetching node and port."
                )
                self.fetch_node()
                self.fetch_port()
            elif self.state is not None and self.state != new_state:
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
            res = subprocess.check_output(
                [
                    "ssh",
                    f"{self.user}@{self.host}",
                    "ls",
                    os.path.join(".blackfish", str(self.job_id)),
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

    def wait(self, period: int = 5) -> dict:
        """Wait for the job to start, re-checking the job's status every `period` seconds."""

        logger.debug(f"waiting for job {self.job_id} to start")
        time.sleep(period)  # wait for slurm to accept job
        while True:
            self.update_state()
            if self.state == "MISSING":
                logger.debug(
                    f"job {self.job_id} state is missing. Re-trying in"
                    f" {period} seconds."
                )
            elif self.state == "PENDING":
                logger.debug(
                    f"job {self.job_id} is pending. Re-trying in {period} seconds."
                )
            elif self.state == "RUNNING":
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
            subprocess.check_output(
                ["ssh", f"{self.user}@{self.host}", "scancel", str(self.job_id)]
            )
        except subprocess.CalledProcessError as e:
            logger.warning(
                f"Failed to cancel job (job_id={self.job_id}, code={e.returncode})."
            )


@dataclass
class LocalJob:
    """A light-weight local job dataclass."""

    job_id: int
    provider: str  # docker or apptainer
    name: Optional[str] = None
    state: Optional[str] = (
        None  # "created", "running", "restarting", "exited", "paused", "dead",
    )
    options: Optional[JobConfig] = None

    def update(self):
        logger.debug(f"Updating job state (job_id={self.job_id})")
        try:
            if self.provider == "docker":
                res = subprocess.check_output(
                    [
                        "docker",
                        "inspect",
                        f"{self.job_id}",
                        "--format='{{ .State.Status }}'",  # or {{ json .State }}
                    ]
                )
                new_state = (
                    "MISSING"
                    if res == b""
                    else res.decode("utf-8").strip().strip("'").upper()
                )
                logger.debug(
                    f"The current job state is: {new_state} (job_id={self.job_id})"
                )
                if self.state is not None and self.state != new_state:
                    logger.debug(
                        f"Job state updated from {self.state} to {new_state}"
                        f" (job_id={self.job_id})"
                    )
                self.state = new_state
            elif self.provider == "apptainer":
                res = subprocess.check_output(
                    ["apptainer", "instance", "list", "--json", f"{self.job_id}"]
                )
                body = json.loads(res)
                if body["instances"] == []:
                    new_state = "STOPPED"
                else:
                    new_state = "RUNNING"

                logger.debug(f"The current job state is: {new_state} (job_id={self.job_id})")
                if self.state is not None and self.state != new_state:
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
            if self.provider == "docker":
                subprocess.check_output(
                    ["docker", "container", "stop", f"{self.job_id}"]
                )
            elif self.provider == "apptainer":
                subprocess.check_output(
                    ["apptainer", "instance", "stop", f"{self.job_id}"]
                )
        except subprocess.CalledProcessError as e:
            logger.warning(
                f"Failed to cancel job (job_id={self.job_id}, code={e.returncode})."
            )
