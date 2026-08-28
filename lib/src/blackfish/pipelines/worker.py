"""The worker loop: set up once, then process many batches.

A worker is a plain process. It starts, runs its job's ``setup`` exactly once,
and then loops: lease a batch, call the function, write the outputs back. This
is the whole reason pipelines are not expressible as chained Slurm jobs -- the
expensive part of an ML job is almost always the setup (loading weights onto a
GPU), and a scheduler that gives you one allocation per task makes you pay it
per task.

Workers only ever dial *out*. A compute node can reach the coordinator on the
login node; nothing can reach the compute node. So the worker polls, and every
interaction is a method on a :class:`~blackfish.pipelines.client.QueueClient` --
satisfied directly by :class:`~blackfish.pipelines.store.TaskStore` when the
worker shares a host with the coordinator, and over HTTP when it does not.
"""

from __future__ import annotations

import argparse
import importlib
import os
import signal
import socket
import sys
import threading
import time
from typing import Any, Callable, Sequence

from blackfish.pipelines.client import QueueClient
from blackfish.pipelines.payload import PayloadStore
from blackfish.pipelines.spec import Cardinality, JobSpec, Pipeline
from blackfish.pipelines.store import Task, cardinality_check
from blackfish.server.logger import logger

# How long a worker waits before re-polling an empty queue. Short enough that a
# newly enqueued task is picked up promptly, long enough that an idle pipeline
# does not hammer the coordinator.
DEFAULT_POLL_SECONDS = 2.0

# How long a worker keeps polling an empty queue before exiting. Exiting frees
# the Slurm allocation; the autoscaler brings a worker back when work returns.
DEFAULT_IDLE_TIMEOUT_SECONDS = 300.0


def resolve(path: str) -> Callable[..., Any]:
    """Import ``"package.module:attribute"`` and return the attribute.

    Raises:
        ImportError: If the module cannot be imported.
        AttributeError: If the module has no such attribute.
        ValueError: If the path is not of the expected form.
    """
    if ":" not in path:
        raise ValueError(f"Expected 'module:attribute', got {path!r}")
    module_name, _, attribute = path.partition(":")
    module = importlib.import_module(module_name)
    try:
        return getattr(module, attribute)  # type: ignore[no-any-return]
    except AttributeError as exc:
        raise AttributeError(
            f"Module '{module_name}' has no attribute '{attribute}'"
        ) from exc


class Worker:
    """Runs one job of one pipeline run until it is told to stop.

    Args:
        run_id: The run this worker serves.
        pipeline: The run's pipeline, for downstream routing.
        job: The job to run. Must belong to ``pipeline``.
        client: How to reach the queues.
        payloads: How to encode and resolve payload references.
        owner: Identifier recorded on leases, for debugging. Defaults to
            ``host:pid``.
        poll_seconds: Sleep between polls of an empty queue.
        idle_timeout: Exit after this many seconds without work. ``None`` to
            run until stopped.
    """

    def __init__(
        self,
        run_id: str,
        pipeline: Pipeline,
        job: JobSpec,
        client: QueueClient,
        payloads: PayloadStore,
        owner: str | None = None,
        poll_seconds: float = DEFAULT_POLL_SECONDS,
        idle_timeout: float | None = DEFAULT_IDLE_TIMEOUT_SECONDS,
    ) -> None:
        self.run_id = run_id
        self.pipeline = pipeline
        self.job = job
        self.client = client
        self.payloads = payloads
        self.owner = owner or f"{socket.gethostname()}:{os.getpid()}"
        self.poll_seconds = poll_seconds
        self.idle_timeout = idle_timeout

        self._downstream = pipeline.downstream(job.name)
        self._is_sink = not self._downstream
        self._fn: Callable[..., Any] | None = None
        self._ctx: Any = None
        self._has_ctx = False
        self.batches = 0
        self.tasks_processed = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Import the job's function and run its setup, once."""
        if self._fn is not None:
            return
        self._fn = resolve(self.job.fn)
        if self.job.setup is not None:
            started = time.monotonic()
            self._ctx = resolve(self.job.setup)()
            self._has_ctx = True
            logger.info(
                "Worker %s: setup for job '%s' completed in %.1fs",
                self.owner,
                self.job.name,
                time.monotonic() - started,
            )

    def run(self, stop: threading.Event | None = None) -> None:
        """Process batches until stopped, or until idle for ``idle_timeout``."""
        self.start()
        stop = stop or threading.Event()
        idle_since: float | None = None
        while not stop.is_set():
            if self.run_once():
                idle_since = None
                continue
            now = time.monotonic()
            idle_since = now if idle_since is None else idle_since
            if self.idle_timeout is not None and now - idle_since >= self.idle_timeout:
                logger.info(
                    "Worker %s: idle for %.0fs, releasing job '%s'",
                    self.owner,
                    self.idle_timeout,
                    self.job.name,
                )
                return
            stop.wait(self.poll_seconds)

    # ------------------------------------------------------------------
    # One batch
    # ------------------------------------------------------------------

    def run_once(self) -> bool:
        """Lease and process at most one batch.

        Returns:
            Whether any work was done. ``False`` means the queue had nothing
            for this worker, and the caller should back off.
        """
        self.start()
        tasks = self.client.lease(
            self.run_id,
            self.job.name,
            self.job.batch_size,
            self.job.lease_seconds,
            self.owner,
        )
        if not tasks:
            return False
        if self.job.cardinality is Cardinality.MANY_TO_ONE:
            return self._process_reduce(tasks)
        return self._process_map(tasks)

    def _process_map(self, tasks: Sequence[Task]) -> bool:
        """Handle a 1:1 or 1:N batch: call, emit per input, acknowledge."""
        task_ids = [task.task_id for task in tasks]
        try:
            values = [self.payloads.get(task.payload) for task in tasks]
            outputs = self._call(values)
            groups = cardinality_check(self.job.cardinality, values, outputs)
            refs = {
                task.task_id: [self.payloads.put(value) for value in group]
                for task, group in zip(tasks, groups, strict=True)
            }
        except Exception as exc:  # noqa: BLE001 - any user error retries the batch
            self._fail(task_ids, exc)
            return True

        self.client.complete_batch(
            self.run_id,
            self.job.name,
            refs,
            self._downstream,
            record_results=self._is_sink,
        )
        self.batches += 1
        self.tasks_processed += len(tasks)
        return True

    def _process_reduce(self, tasks: Sequence[Task]) -> bool:
        """Handle an N:1 batch: fold two or more partials into one.

        A lone partial is either the reduce's final answer -- emitted if every
        upstream job has finished -- or one of several still being folded
        elsewhere, in which case the worker puts it back untouched. Folding it
        alone would return it unchanged and spin forever.
        """
        task_ids = [task.task_id for task in tasks]
        if len(tasks) == 1:
            finalized = self.client.finalize_reduce(
                self.run_id,
                self.job.name,
                tasks[0].task_id,
                self._downstream,
                record_results=self._is_sink,
            )
            if finalized:
                self.batches += 1
                self.tasks_processed += 1
                return True
            self.client.release(self.run_id, self.job.name, task_ids)
            return False

        try:
            values = [self.payloads.get(task.payload) for task in tasks]
            partial = self._call(values)
            ref = self.payloads.put(partial)
        except Exception as exc:  # noqa: BLE001 - any user error retries the batch
            self._fail(task_ids, exc)
            return True

        self.client.fold_batch(self.run_id, self.job.name, task_ids, ref)
        self.batches += 1
        self.tasks_processed += len(tasks)
        return True

    def _call(self, values: list[Any]) -> Any:
        assert self._fn is not None  # start() ran
        if self._has_ctx:
            return self._fn(values, self._ctx)
        return self._fn(values)

    def _fail(self, task_ids: Sequence[str], exc: BaseException) -> None:
        error = f"{type(exc).__name__}: {exc}"
        retried, dead = self.client.fail_batch(
            self.run_id,
            self.job.name,
            task_ids,
            error,
            self.job.max_attempts,
        )
        logger.warning(
            "Worker %s: job '%s' batch failed (%s); %d retried, %d dead-lettered",
            self.owner,
            self.job.name,
            error,
            retried,
            dead,
        )


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for a worker process.

    Slurm launches this inside an allocation; the local backend launches it as
    a subprocess. Either way the worker is handed a run, a job and a way to
    reach the coordinator, and figures out the rest from the stored pipeline.
    """
    parser = argparse.ArgumentParser(prog="blackfish-pipeline-worker")
    parser.add_argument("--run", required=True, help="Run ID")
    parser.add_argument("--job", required=True, help="Job name")
    parser.add_argument(
        "--store",
        help="Path to the coordinator's SQLite store (same-host workers only)",
    )
    parser.add_argument(
        "--url",
        help="Coordinator base URL, for workers on a compute node",
    )
    parser.add_argument("--payloads", required=True, help="Payload store directory")
    parser.add_argument("--poll-seconds", type=float, default=DEFAULT_POLL_SECONDS)
    parser.add_argument(
        "--idle-timeout",
        type=float,
        default=DEFAULT_IDLE_TIMEOUT_SECONDS,
        help="Exit after this many idle seconds; 0 to run until killed",
    )
    args = parser.parse_args(argv)

    if bool(args.store) == bool(args.url):
        parser.error("Pass exactly one of --store or --url")

    client: QueueClient
    if args.store:
        from blackfish.pipelines.store import TaskStore

        client = TaskStore(args.store)
    else:
        from blackfish.pipelines.client import HttpQueueClient

        client = HttpQueueClient(args.url)

    pipeline = client.get_pipeline(args.run)
    worker = Worker(
        run_id=args.run,
        pipeline=pipeline,
        job=pipeline.job(args.job),
        client=client,
        payloads=PayloadStore(args.payloads),
        poll_seconds=args.poll_seconds,
        idle_timeout=args.idle_timeout or None,
    )

    stop = threading.Event()

    def _handle(signum: int, _frame: Any) -> None:
        # Leases expire on their own, so an interrupted batch is re-delivered
        # without any cleanup here. Just stop taking new work.
        logger.info("Worker %s: received signal %d, stopping", worker.owner, signum)
        stop.set()

    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)

    worker.run(stop)
    return 0


if __name__ == "__main__":  # pragma: no cover - process entry point
    sys.exit(main())
