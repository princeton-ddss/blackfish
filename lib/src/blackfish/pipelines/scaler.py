"""Deciding how many workers each job should have.

The policy is deliberately boring, and all of it is a pure function of queue
depth so it can be tested without a cluster. Two asymmetries are worth calling
out, because both come from Slurm rather than from queueing theory:

- **Scale up now, scale down slowly.** A new worker costs a trip through the
  Slurm queue, which can be minutes. Releasing one that is about to be needed
  again is therefore far more expensive than holding it a little longer, so
  growth is immediate and shrinking waits for several consecutive idle ticks.
- **Never scale on backlog alone.** Backlog is measured in tasks and workers
  consume tasks ``batch_size`` at a time, so a 100-task backlog on a job with
  ``batch_size=32`` needs four workers, not a hundred.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil

from blackfish.pipelines.spec import JobSpec
from blackfish.pipelines.store import JobStatus

# Consecutive ticks a job must look over-provisioned before a worker is
# released. At the coordinator's default tick this is a couple of minutes of
# genuine idleness, which is short next to Slurm queue time and long enough to
# ride out an upstream job's momentary stall.
DEFAULT_SCALE_DOWN_AFTER = 3


@dataclass(frozen=True, slots=True)
class ScalingDecision:
    """What the autoscaler wants for one job, and why."""

    job: str
    current: int
    desired: int
    reason: str

    @property
    def changed(self) -> bool:
        return self.current != self.desired


@dataclass
class Autoscaler:
    """Queue-depth autoscaler with scale-down hysteresis.

    Args:
        scale_down_after: Consecutive over-provisioned ticks before releasing a
            worker.
    """

    scale_down_after: int = DEFAULT_SCALE_DOWN_AFTER
    _idle_ticks: dict[str, int] = field(default_factory=dict, repr=False)

    def decide(self, job: JobSpec, status: JobStatus, current: int) -> ScalingDecision:
        """Return the worker count ``job`` should have right now.

        Args:
            job: The job's spec, for its bounds and batch size.
            status: Live queue depth and completion state.
            current: Workers the backend reports as running.
        """
        if status.complete:
            self._idle_ticks.pop(job.name, None)
            return ScalingDecision(job.name, current, 0, "job complete")

        # Leased tasks already have a worker; counting them keeps a job from
        # being scaled down while its workers are mid-batch on a drained queue.
        pending = status.backlog + status.leased
        want = ceil(pending / job.batch_size) if pending else 0
        want = max(want, job.min_workers)
        want = min(want, job.max_workers)

        if want > current:
            self._idle_ticks.pop(job.name, None)
            return ScalingDecision(
                job.name,
                current,
                want,
                f"backlog {status.backlog} over batch size {job.batch_size}",
            )

        if want == current:
            self._idle_ticks.pop(job.name, None)
            return ScalingDecision(job.name, current, current, "at target")

        ticks = self._idle_ticks.get(job.name, 0) + 1
        if ticks < self.scale_down_after:
            self._idle_ticks[job.name] = ticks
            return ScalingDecision(
                job.name,
                current,
                current,
                f"over-provisioned for {ticks}/{self.scale_down_after} ticks",
            )
        self._idle_ticks.pop(job.name, None)
        return ScalingDecision(
            job.name, current, want, f"idle for {self.scale_down_after} ticks"
        )

    def forget(self, job: str) -> None:
        """Drop hysteresis state for a job, e.g. when its run ends."""
        self._idle_ticks.pop(job, None)
