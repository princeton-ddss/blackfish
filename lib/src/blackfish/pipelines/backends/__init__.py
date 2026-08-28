"""Where a job's workers actually run.

A backend answers one question the rest of the system deliberately does not:
given that job ``X`` should have ``n`` workers, make that true. The queue, the
DAG semantics and the autoscaling policy are all backend-agnostic, which is what
lets the same pipeline run in-process on a laptop and across Slurm allocations
on a cluster.
"""

from __future__ import annotations

from typing import Protocol

from blackfish.pipelines.spec import JobSpec


class WorkerBackend(Protocol):
    """Manages the worker processes for the jobs of a run."""

    async def scale(self, run_id: str, job: JobSpec, desired: int) -> None:
        """Converge the number of live workers for ``job`` on ``desired``."""
        ...

    async def count(self, run_id: str, job: str) -> int:
        """Return the number of live workers, reaping any that have exited."""
        ...

    async def shutdown(self, run_id: str) -> None:
        """Stop every worker of a run and release its resources."""
        ...


__all__ = ["WorkerBackend"]
