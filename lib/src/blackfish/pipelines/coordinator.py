"""The coordinator: owns the DAG, the queues, and the scaling decisions.

The coordinator is a long-running process on the login node -- in production,
the Blackfish server itself. It is the only process that opens the task store,
the only one that talks to Slurm, and the only one that has an opinion about how
many workers a job should have. Workers know none of this; they poll a queue.

A tick does four things, in this order:

1. **Reclaim expired leases.** A worker that was preempted, ran out of walltime
   or was OOM-killed leaves tasks leased. Nothing else recovers them.
2. **Read the run's status.** Queue depths and, from them, which jobs are
   complete.
3. **Scale each job.** Ask the autoscaler, tell the backend.
4. **Settle the run** when every job is complete.

The order matters: reclaiming first means the backlog the autoscaler sees
already includes work that fell out of a dead worker, so capacity is requested
in the same tick the loss is noticed rather than the next one.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping, Sequence
from typing import Any

from blackfish.pipelines.backends import WorkerBackend
from blackfish.pipelines.payload import PayloadStore
from blackfish.pipelines.scaler import Autoscaler, ScalingDecision
from blackfish.pipelines.spec import Pipeline
from blackfish.pipelines.store import RunState, RunStatus, TaskStore
from blackfish.server.logger import logger

DEFAULT_TICK_SECONDS = 1.0


class Coordinator:
    """Drives pipeline runs to completion.

    Args:
        store: The task store. The coordinator owns it exclusively.
        payloads: Payload store, used to encode submitted inputs and decode
            results.
        backend: Where workers run.
        autoscaler: Scaling policy. A default one is created if omitted.
        tick_seconds: Sleep between ticks of :meth:`run_until_complete`.
    """

    def __init__(
        self,
        store: TaskStore,
        payloads: PayloadStore,
        backend: WorkerBackend,
        autoscaler: Autoscaler | None = None,
        tick_seconds: float = DEFAULT_TICK_SECONDS,
    ) -> None:
        self.store = store
        self.payloads = payloads
        self.backend = backend
        self.autoscaler = autoscaler or Autoscaler()
        self.tick_seconds = tick_seconds

    # ------------------------------------------------------------------
    # Runs
    # ------------------------------------------------------------------

    def start_run(
        self,
        pipeline: Pipeline,
        inputs: Mapping[str, Sequence[Any]] | Sequence[Any],
        seal: bool = True,
        run_id: str | None = None,
    ) -> str:
        """Register a run and enqueue its inputs.

        Args:
            pipeline: The DAG to run.
            inputs: Values for the source jobs. A bare sequence is accepted
                when the pipeline has exactly one source.
            seal: Whether to declare the sources closed immediately. Pass
                ``False`` for a run that keeps receiving inputs -- but note
                that an unsealed source can never complete, by design: an empty
                queue and a slow producer look identical from the outside.
            run_id: Optional explicit run ID.

        Returns:
            The run ID.
        """
        by_job = self._inputs_by_job(pipeline, inputs)
        rid = self.store.create_run(pipeline, run_id=run_id)
        for job_name, values in by_job.items():
            refs = [self.payloads.put(value) for value in values]
            self.store.submit(rid, job_name, refs)
            if seal:
                self.store.seal(rid, job_name)
        logger.info(
            "Started pipeline run %s (%s) with %d input(s)",
            rid,
            pipeline.name,
            sum(len(values) for values in by_job.values()),
        )
        return rid

    def submit(
        self,
        run_id: str,
        job: str,
        values: Sequence[Any],
        keys: Sequence[str] | None = None,
    ) -> int:
        """Add inputs to an unsealed source job of a running pipeline.

        Args:
            run_id: The run.
            job: A source job.
            values: The inputs.
            keys: Optional stable identity per value, which makes the
                submission idempotent within this run. Pass the file path when
                inputs are files: re-scanning a directory then enqueues only
                what is new, so a standing run over a growing directory needs
                no bookkeeping of its own.

        Returns:
            The number of inputs actually enqueued.
        """
        refs = [self.payloads.put(value) for value in values]
        return self.store.submit(run_id, job, refs, keys=keys)

    def seal(self, run_id: str, job: str) -> None:
        """Declare a source job closed. Required before the run can complete."""
        self.store.seal(run_id, job)

    async def tick(self, run_id: str) -> RunStatus:
        """Advance a run by one scheduling round."""
        reclaimed = self.store.reclaim_expired(run_id)
        if reclaimed:
            logger.info(
                "Run %s: reclaimed %d task(s) from expired leases", run_id, reclaimed
            )

        pipeline = self.store.get_pipeline(run_id)
        status = self.store.run_status(run_id)

        for spec in pipeline.jobs:
            job_status = status.job(spec.name)
            current = await self.backend.count(run_id, spec.name)
            decision = self.autoscaler.decide(spec, job_status, current)
            if decision.changed:
                self._log_decision(run_id, decision)
                await self.backend.scale(run_id, spec, decision.desired)

        if status.complete and status.state is RunState.RUNNING:
            await self.backend.shutdown(run_id)
            self.store.set_run_state(run_id, RunState.COMPLETE)
            for spec in pipeline.jobs:
                self.autoscaler.forget(spec.name)
            dead = status.dead_letters
            logger.info(
                "Run %s complete%s",
                run_id,
                f" with {dead} dead-lettered task(s)" if dead else "",
            )
            return self.store.run_status(run_id)
        return status

    async def run_until_complete(
        self, run_id: str, timeout: float | None = None
    ) -> RunStatus:
        """Tick until every job is complete.

        Raises:
            TimeoutError: If ``timeout`` elapses first. The run is left intact
                and can be resumed by ticking again -- nothing about it lives
                in this coroutine.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            status = await self.tick(run_id)
            if status.complete:
                return status
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Run {run_id} did not complete within {timeout}s;"
                    f" outstanding: "
                    + ", ".join(
                        f"{job.job}={job.outstanding}"
                        for job in status.jobs
                        if job.outstanding
                    )
                )
            await asyncio.sleep(self.tick_seconds)

    async def cancel(self, run_id: str) -> None:
        """Stop a run's workers and mark it cancelled.

        Leaves the queues as they are: a cancelled run keeps its state, so the
        work already done is not lost if it is resumed.
        """
        await self.backend.shutdown(run_id)
        self.store.set_run_state(run_id, RunState.CANCELLED)

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def results(self, run_id: str, job: str | None = None) -> list[Any]:
        """Decoded outputs of the run's sink jobs."""
        return [self.payloads.get(ref) for ref in self.store.results(run_id, job)]

    def dead_letters(self, run_id: str) -> tuple[tuple[str, str, str], ...]:
        """``(job, task_id, error)`` for tasks that exhausted their retries."""
        return self.store.dead_letters(run_id)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _inputs_by_job(
        pipeline: Pipeline, inputs: Mapping[str, Sequence[Any]] | Sequence[Any]
    ) -> dict[str, list[Any]]:
        sources = {job.name for job in pipeline.sources}
        if isinstance(inputs, Mapping):
            unknown = sorted(set(inputs) - sources)
            if unknown:
                raise ValueError(
                    f"Inputs given for non-source job(s): {', '.join(unknown)}."
                    f" Sources are: {', '.join(sorted(sources))}"
                )
            return {name: list(values) for name, values in inputs.items()}
        if len(sources) != 1:
            raise ValueError(
                f"Pipeline '{pipeline.name}' has {len(sources)} source jobs, so"
                " inputs must be a mapping of job name to values"
            )
        return {next(iter(sources)): list(inputs)}

    @staticmethod
    def _log_decision(run_id: str, decision: ScalingDecision) -> None:
        logger.info(
            "Run %s: scaling job '%s' %d -> %d (%s)",
            run_id,
            decision.job,
            decision.current,
            decision.desired,
            decision.reason,
        )
