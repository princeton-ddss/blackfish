import os
import time
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
            k:v
            for k, v in filter(lambda item: item[1] is not None, asdict(self).items())
        }

    def replace(self, changes: dict) -> None:
        return replace(self, **changes)


@dataclass
class LocalJobConfig(JobConfig):
    name: str
    gres: int  # i.e., gpu:<gres>


@dataclass
class SlurmJobConfig(JobConfig):
    host: Optional[str] = None
    name: Optional[str] = "blackfish"
    time: Optional[str] = "00:15:00"
    nodes: Optional[int] = 1
    ntasks_per_node: Optional[int] = 4
    mem: Optional[int] = 8
    gres: Optional[int] = 0  # i.e., gpu:<gres>
    partition: Optional[str] = None  # e.g., mig
    constraint: Optional[str] = None  # e.g., gpu80


@dataclass
class EC2JobConfig(JobConfig): ...


class Job:
    """A light-weight Slurm job dataclass."""

    job_id: int
    user: str
    host: str
    name: Optional[str] = None
    node: Optional[str] = None
    port: Optional[int] = None
    state: Optional[JobState] = None
    options: Optional[JobConfig] = None

    def update_state(self):
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
            logger.debug(f"current job state: {self.state}, new job state: {new_state}")
            if self.state in [None, "MISSING", "PENDING"] and new_state == "RUNNING":
                logger.debug(
                    "job state switched from PENDING to RUNNING"
                    f" (job_id={self.job_id})."
                )
                self.update_node()
                self.update_port()
            self.state = new_state
            logger.debug(f"job {self.job_id} state set to {self.state}")
        except subprocess.CalledProcessError as e:
            logger.warning(
                f"failed to update job state (job_id={self.job_id},"
                f" code={e.returncode})."
            )

        return self.state

    def update_node(self) -> Optional[str]:
        logger.debug(f"updating node for job {self.job_id}.")
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
        logger.debug(f"job {self.job_id} node set to {self.node}.")

        return self.node

    def update_port(self) -> Optional[int]:
        logger.debug(f"updating port for job {self.job_id}.")
        res = subprocess.check_output(
            [
                "ssh",
                f"{self.user}@{self.host}",
                "ls",
                os.path.join(".blackfish", str(self.job_id)),
            ]
        )
        self.port = None if res == b"" else int(res.decode("utf-8").strip())
        logger.debug(f"job {self.job_id} port set to {self.port}")

        return self.port

    def wait(self, period: int = 5) -> dict:
        """Wait for the job to start."""

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
                self.update_node()
                self.update_port()
                return {"ok": True}
            else:
                logger.debug(f"job {self.job_id} failed (state={self.state}).")
                return {"ok": False}

            time.sleep(period)

    def cancel(self) -> None:
        logger.debug(f"canceling job {self.job_id}.")
        subprocess.check_output(
            ["ssh", f"{self.user}@{self.host}", "scancel", str(self.job_id)]
        )
