"""ML pipelines: DAGs of long-lived, autoscaled workers on HPC clusters.

A pipeline is a directed acyclic graph of jobs connected by durable task queues.
Each job runs its expensive setup once per worker and then serves many tasks, so
a model's weights are loaded per *allocation* rather than per item -- which is
the thing a chain of Slurm jobs, or a workflow engine that assumes cheap
workers, cannot express.

    from blackfish.pipelines import Cardinality, JobSpec, Pipeline, run_local

    pipeline = Pipeline(
        name="transcribe-and-summarize",
        jobs=(
            JobSpec(name="transcribe", fn="my.jobs:transcribe",
                    setup="my.jobs:load_whisper", batch_size=8,
                    max_workers=4, resources={"gpus": 1}),
            JobSpec(name="summarize", fn="my.jobs:summarize",
                    cardinality=Cardinality.MANY_TO_ONE, batch_size=16),
        ),
        edges=(("transcribe", "summarize"),),
    )

    status, results = await run_local(pipeline, ["a.wav", "b.wav"])

The pieces, in the order they matter:

- :mod:`~blackfish.pipelines.spec` -- what a job is, and what its cardinality
  means.
- :mod:`~blackfish.pipelines.store` -- the queues, the leases, and the argument
  for why fan-in is correct.
- :mod:`~blackfish.pipelines.worker` -- the loop that pays setup once.
- :mod:`~blackfish.pipelines.scaler` -- how many workers a job should have.
- :mod:`~blackfish.pipelines.coordinator` -- the thing that ties them together.
- :mod:`~blackfish.pipelines.backends` -- where workers actually run: threads,
  subprocesses, or Ray actors inside Slurm allocations.
"""

from __future__ import annotations

import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from blackfish.pipelines.coordinator import Coordinator
from blackfish.pipelines.payload import PayloadStore
from blackfish.pipelines.scaler import Autoscaler, ScalingDecision
from blackfish.pipelines.spec import Cardinality, JobSpec, Pipeline, Placement
from blackfish.pipelines.store import (
    JobStatus,
    RunState,
    RunStatus,
    Task,
    TaskState,
    TaskStore,
)

__all__ = [
    "Autoscaler",
    "Cardinality",
    "Coordinator",
    "JobSpec",
    "JobStatus",
    "PayloadStore",
    "Pipeline",
    "Placement",
    "RunState",
    "RunStatus",
    "ScalingDecision",
    "Task",
    "TaskState",
    "TaskStore",
    "run_local",
]


async def run_local(
    pipeline: Pipeline,
    inputs: Mapping[str, Sequence[Any]] | Sequence[Any],
    root: str | Path | None = None,
    timeout: float | None = 60.0,
    tick_seconds: float = 0.02,
) -> tuple[RunStatus, list[Any]]:
    """Run a pipeline to completion in this process, using worker threads.

    For development, tests and small jobs. The semantics are identical to a
    cluster run -- same queues, same cardinality rules, same autoscaler -- only
    the backend differs, so a pipeline that behaves here behaves there.

    Args:
        pipeline: The DAG to run.
        inputs: Values for the source jobs.
        root: Directory for the task store and spilled payloads. A temporary
            directory is used if omitted.
        timeout: Seconds before giving up.
        tick_seconds: Coordinator tick interval.

    Returns:
        The final run status and the decoded outputs of the sink jobs.
    """
    from blackfish.pipelines.backends.local import ThreadBackend

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(root) if root is not None else Path(tmp)
        base.mkdir(parents=True, exist_ok=True)
        store = TaskStore(base / "pipeline.db")
        payloads = PayloadStore(base / "payloads")
        backend = ThreadBackend(store, payloads, pipeline)
        coordinator = Coordinator(store, payloads, backend, tick_seconds=tick_seconds)
        run_id = coordinator.start_run(pipeline, inputs)
        try:
            status = await coordinator.run_until_complete(run_id, timeout=timeout)
            return status, coordinator.results(run_id)
        finally:
            await backend.shutdown(run_id)
            store.close()
