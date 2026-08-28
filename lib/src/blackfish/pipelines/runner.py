"""The process that drives one pipeline run.

Started by the server (or the CLI) and then left alone. This is the batch-job
pattern applied to the coordinator: the thing that launches a run does not
*host* it, so the launcher's own lifetime -- an Open OnDemand session, a server
restart, a closed browser tab -- stops being something the run depends on.

What the runner owns:

- the task store, which it is the sole writer of;
- the backend, and therefore the worker processes or allocations;
- a heartbeat, written every tick, which is the only way a monitor can tell
  "coordinating" from "died holding the run open" -- both look identical from
  queue depth alone.

What it deliberately does not own: the run's *existence*. The run is created
and its inputs submitted before the runner starts, so the UI can show a queued
run with its inputs before any process exists, and so relaunching after a crash
is the same command with the same arguments.

Its exit code is a summary, not the record: the store holds the truth, and
:mod:`blackfish.pipelines.supervisor` reads it back.
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from blackfish.pipelines.backends import WorkerBackend
from blackfish.pipelines.coordinator import Coordinator
from blackfish.pipelines.payload import PayloadStore
from blackfish.pipelines.store import TaskStore
from blackfish.server.logger import logger

# Exit codes, so a supervisor that only has the exit status still learns
# something useful. The store is the authority; these are a summary.
EXIT_COMPLETE = 0
EXIT_CANCELLED = 2
EXIT_FAILED = 3

# Set by the early signal handler installed before the event loop exists.
# Without it there is a window -- interpreter start-up, imports, opening the
# store -- in which SIGTERM hits Python's default disposition and kills the
# runner outright, so a run cancelled immediately after launch would report as
# crashed rather than cancelled.
_STOP_REQUESTED = False


def _request_stop(signum: int, _frame: Any) -> None:
    global _STOP_REQUESTED
    _STOP_REQUESTED = True


def build_backend(
    kind: str,
    store: TaskStore,
    payloads: PayloadStore,
    pipeline: Any,
    store_path: str,
    payload_dir: str,
) -> WorkerBackend:
    """Construct the worker backend named on the command line.

    Kept as a switch rather than a plugin registry because the choice is a
    deployment decision with three answers today, and a registry would hide
    which one a given run actually used.
    """
    if kind == "thread":
        from blackfish.pipelines.backends.local import ThreadBackend

        return ThreadBackend(store, payloads, pipeline)
    if kind == "subprocess":
        from blackfish.pipelines.backends.local import SubprocessBackend

        return SubprocessBackend(store_path, payload_dir)
    raise ValueError(f"Unknown backend: {kind!r}")


async def drive(
    coordinator: Coordinator,
    store: TaskStore,
    run_id: str,
    tick_seconds: float,
    stop: asyncio.Event,
) -> int:
    """Tick the run to completion, heartbeating as it goes.

    Written out rather than delegating to ``run_until_complete`` because a
    supervised run needs two things that loop does not do: a heartbeat on every
    tick, and a stop that finishes the tick in progress instead of abandoning
    it mid-transaction.
    """
    while True:
        status = await coordinator.tick(run_id)
        store.heartbeat(run_id)

        if status.complete:
            dead = status.dead_letters
            logger.info(
                "Run %s complete%s",
                run_id,
                f" with {dead} dead-lettered task(s)" if dead else "",
            )
            return EXIT_COMPLETE

        if stop.is_set():
            logger.info("Run %s: stop requested, releasing workers", run_id)
            await coordinator.cancel(run_id)
            store.heartbeat(run_id)
            return EXIT_CANCELLED

        try:
            await asyncio.wait_for(stop.wait(), timeout=tick_seconds)
        except asyncio.TimeoutError:
            pass


async def run(args: argparse.Namespace) -> int:
    store = TaskStore(args.store)
    try:
        pipeline = store.get_pipeline(args.run)
        payloads = PayloadStore(args.payloads)
        backend = build_backend(
            args.backend, store, payloads, pipeline, args.store, args.payloads
        )
        coordinator = Coordinator(
            store, payloads, backend, tick_seconds=args.tick_seconds
        )

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for signum in (signal.SIGTERM, signal.SIGINT):
            # A supervised run is stopped by signal, so the handler must do the
            # least possible: ask the loop to wind down at the next tick
            # boundary, where cancelling is safe.
            loop.add_signal_handler(signum, stop.set)
        if _STOP_REQUESTED:
            # A signal arrived before the loop existed. Honour it rather than
            # starting work that is already unwanted.
            stop.set()

        logger.info(
            "Run %s: driving pipeline '%s' with the %s backend",
            args.run,
            pipeline.name,
            args.backend,
        )
        try:
            return await drive(coordinator, store, args.run, args.tick_seconds, stop)
        finally:
            await backend.shutdown(args.run)
    finally:
        store.close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="blackfish-pipeline-runner")
    parser.add_argument("--run", required=True, help="Run ID, already created")
    parser.add_argument("--store", required=True, help="Task store database path")
    parser.add_argument("--payloads", required=True, help="Payload store directory")
    parser.add_argument(
        "--backend",
        default="thread",
        choices=["thread", "subprocess"],
        help="Where workers run",
    )
    parser.add_argument("--tick-seconds", type=float, default=1.0)
    args = parser.parse_args(argv)

    if not Path(args.store).exists():
        parser.error(f"No task store at {args.store}")

    # Installed before the event loop so the start-up window is covered; the
    # loop replaces these with its own handlers once it is running.
    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)

    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:  # pragma: no cover - signal handler covers this
        return EXIT_CANCELLED
    except Exception:
        # Leave the run RUNNING with a stale heartbeat rather than marking it
        # failed: the supervisor's verdict should come from observing the
        # world, not from the last thing a dying process managed to write.
        logger.exception("Run %s: coordinator failed", args.run)
        return EXIT_FAILED


if __name__ == "__main__":  # pragma: no cover - process entry point
    sys.exit(main())
