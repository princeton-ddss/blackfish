"""Backends that run workers on the coordinator's own machine.

:class:`ThreadBackend` runs workers as threads inside the coordinator, sharing
its :class:`~blackfish.pipelines.store.TaskStore` directly. It is the fastest
way to develop and test a pipeline, and the right choice for a ``LOGIN``-placed
job whose work is IO-bound.

:class:`SubprocessBackend` runs each worker as its own process. It is the honest
local rehearsal of cluster behaviour -- separate interpreters, separate memory,
setup paid per worker, workers killable -- without needing a scheduler.
"""

from __future__ import annotations

import asyncio
import contextlib
import signal
import sys
import threading
from pathlib import Path

from blackfish.pipelines.payload import PayloadStore
from blackfish.pipelines.spec import JobSpec, Pipeline
from blackfish.pipelines.client import QueueClient
from blackfish.pipelines.worker import Worker
from blackfish.server.logger import logger

# How long a stopping worker is given to finish its current batch before it is
# killed. A killed worker loses nothing -- its lease simply expires -- but a
# graceful exit avoids the wait for that expiry.
GRACEFUL_STOP_SECONDS = 30.0


class ThreadBackend:
    """Runs workers as threads in the coordinator process.

    Args:
        store: How workers reach the queues. Typed as a
            :class:`~blackfish.pipelines.client.QueueClient`, since a worker
            needs nothing more than that.
        payloads: Payload store used to encode and resolve task values.
        pipeline: The pipeline being run.
        poll_seconds: Sleep between polls of an empty queue.
    """

    def __init__(
        self,
        store: QueueClient,
        payloads: PayloadStore,
        pipeline: Pipeline,
        poll_seconds: float = 0.05,
    ) -> None:
        self._store = store
        self._payloads = payloads
        self._pipeline = pipeline
        self._poll_seconds = poll_seconds
        self._workers: dict[
            tuple[str, str], list[tuple[threading.Thread, threading.Event]]
        ] = {}

    async def scale(self, run_id: str, job: JobSpec, desired: int) -> None:
        live = await self.count(run_id, job.name)
        key = (run_id, job.name)
        if desired > live:
            for _ in range(desired - live):
                stop = threading.Event()
                worker = Worker(
                    run_id=run_id,
                    pipeline=self._pipeline,
                    job=job,
                    client=self._store,
                    payloads=self._payloads,
                    poll_seconds=self._poll_seconds,
                    idle_timeout=None,
                )
                thread = threading.Thread(
                    target=worker.run,
                    args=(stop,),
                    name=f"pipeline-{job.name}",
                    daemon=True,
                )
                thread.start()
                self._workers.setdefault(key, []).append((thread, stop))
        elif desired < live:
            for _ in range(live - desired):
                _thread, stop = self._workers[key].pop()
                stop.set()

    async def count(self, run_id: str, job: str) -> int:
        key = (run_id, job)
        alive = [entry for entry in self._workers.get(key, []) if entry[0].is_alive()]
        self._workers[key] = alive
        return len(alive)

    async def shutdown(self, run_id: str) -> None:
        for (rid, _job), entries in list(self._workers.items()):
            if rid != run_id:
                continue
            for _thread, stop in entries:
                stop.set()
        deadline = asyncio.get_running_loop().time() + GRACEFUL_STOP_SECONDS
        for (rid, _job), entries in list(self._workers.items()):
            if rid != run_id:
                continue
            for thread, _stop in entries:
                remaining = max(0.0, deadline - asyncio.get_running_loop().time())
                await asyncio.to_thread(thread.join, remaining)
            self._workers.pop((rid, _job), None)


class SubprocessBackend:
    """Runs each worker as a separate ``blackfish.pipelines.worker`` process.

    Args:
        store_path: Path to the coordinator's SQLite store. Workers open it
            directly, which is safe only because they share this filesystem and
            this host -- on a cluster, use an HTTP-backed backend instead.
        payload_dir: Directory backing the payload store.
        python: Interpreter to launch workers with.
        idle_timeout: Seconds of empty queue before a worker exits on its own.
    """

    def __init__(
        self,
        store_path: str | Path,
        payload_dir: str | Path,
        python: str | None = None,
        idle_timeout: float | None = None,
    ) -> None:
        self._store_path = str(store_path)
        self._payload_dir = str(payload_dir)
        self._python = python or sys.executable
        self._idle_timeout = idle_timeout
        self._procs: dict[tuple[str, str], list[asyncio.subprocess.Process]] = {}

    async def scale(self, run_id: str, job: JobSpec, desired: int) -> None:
        live = await self.count(run_id, job.name)
        key = (run_id, job.name)
        if desired > live:
            for _ in range(desired - live):
                proc = await asyncio.create_subprocess_exec(
                    self._python,
                    "-m",
                    "blackfish.pipelines.worker",
                    "--run",
                    run_id,
                    "--job",
                    job.name,
                    "--store",
                    self._store_path,
                    "--payloads",
                    self._payload_dir,
                    "--idle-timeout",
                    str(self._idle_timeout or 0),
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                self._procs.setdefault(key, []).append(proc)
                logger.debug(
                    "Started worker pid=%s for run %s job '%s'",
                    proc.pid,
                    run_id,
                    job.name,
                )
        elif desired < live:
            for _ in range(live - desired):
                proc = self._procs[key].pop()
                await self._stop(proc)

    async def count(self, run_id: str, job: str) -> int:
        key = (run_id, job)
        alive = [proc for proc in self._procs.get(key, []) if proc.returncode is None]
        self._procs[key] = alive
        return len(alive)

    async def shutdown(self, run_id: str) -> None:
        for (rid, job), procs in list(self._procs.items()):
            if rid != run_id:
                continue
            for proc in procs:
                await self._stop(proc)
            self._procs.pop((rid, job), None)

    @staticmethod
    async def _stop(proc: asyncio.subprocess.Process) -> None:
        """Ask a worker to finish its batch and exit; kill it if it will not."""
        if proc.returncode is not None:
            return
        try:
            proc.send_signal(signal.SIGTERM)
        except ProcessLookupError:  # pragma: no cover - raced with exit
            return
        try:
            await asyncio.wait_for(proc.wait(), timeout=GRACEFUL_STOP_SECONDS)
        except asyncio.TimeoutError:
            with contextlib.suppress(ProcessLookupError, OSError):
                proc.kill()
            await proc.wait()


__all__ = ["SubprocessBackend", "ThreadBackend", "GRACEFUL_STOP_SECONDS"]
