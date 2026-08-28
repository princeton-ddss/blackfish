"""Launching a run as its own process, and watching it from outside.

The server does not host a run; it starts one and then observes it. That is
the same relationship Blackfish already has with a batch job -- submit, then
read the world back -- and it is what makes a run independent of the thing that
started it. An Open OnDemand session ending, the server restarting, or a
browser tab closing are all survivable, because none of them is where the run
lives.

Observation is deliberately *evidence-based* rather than remembered:

- **Is the process there?** A pid alone is not enough. Pids are recycled, and a
  supervisor that persists them across a server restart will eventually check
  one that now belongs to something else -- so the launch time is recorded and
  compared against the process's own start time.
- **Is it working?** Queue depth cannot distinguish a coordinator that is
  working from one that died holding the run open. The heartbeat can.
- **Did it finish?** The store says so, and it says so whether or not anyone
  was watching when it happened.

Nothing here needs the run's own process to cooperate beyond writing that
heartbeat, so a run whose coordinator was killed uncleanly still reports an
accurate verdict.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import psutil

from blackfish.pipelines.store import RunInfo, RunState, RunStatus, TaskStore
from blackfish.server.logger import logger

# How long without a heartbeat before a live process is called unresponsive.
# Generous next to the runner's default one-second tick: a coordinator doing a
# slow scaling call to Slurm is not a hung one.
DEFAULT_STALE_AFTER_SECONDS = 60.0

# How long a stopping runner is given to release its workers before it is
# killed. It cancels at a tick boundary, so this only has to cover one tick
# plus the backend's own shutdown.
DEFAULT_GRACE_SECONDS = 60.0


class RunVerdict(StrEnum):
    """What a monitor concludes about a run, from evidence rather than memory."""

    QUEUED = "queued"
    """Created, inputs submitted, no process started yet."""

    STARTING = "starting"
    """A live process that has not yet checked in. Distinct from RUNNING
    because "launched" and "working" are not the same claim, and treating a
    process that has never heartbeated as healthy hides a runner that dies
    during start-up."""

    RUNNING = "running"
    """A live process, heartbeating."""

    UNRESPONSIVE = "unresponsive"
    """The process is alive but has not checked in. Hung, or wedged on a call
    that never returns -- distinguishable from crashed, and worth distinguishing
    because the fix is different."""

    COMPLETE = "complete"
    CANCELLED = "cancelled"

    CRASHED = "crashed"
    """No process, and the run never settled. The queues are intact, so the
    remedy is to launch a runner again on the same run."""


@dataclass(frozen=True, slots=True)
class RunHandle:
    """What the supervisor remembers about a launch, and persists.

    ``started_at`` is not decoration: checked against the process's own create
    time, it is what stops a recycled pid from being mistaken for a live run.
    """

    run_id: str
    pid: int
    started_at: float
    command: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunHandle":
        return cls(
            run_id=str(data["run_id"]),
            pid=int(data["pid"]),
            started_at=float(data["started_at"]),
            command=[str(part) for part in data.get("command", [])],
        )


@dataclass(frozen=True, slots=True)
class RunObservation:
    """A monitor's view of a run at one moment."""

    run_id: str
    verdict: RunVerdict
    alive: bool
    pid: int | None
    heartbeat_age: float | None
    info: RunInfo
    status: RunStatus | None

    @property
    def settled(self) -> bool:
        """Whether the run will not change again without another launch."""
        return self.verdict in (
            RunVerdict.COMPLETE,
            RunVerdict.CANCELLED,
            RunVerdict.CRASHED,
        )


@dataclass(frozen=True, slots=True)
class RunPaths:
    """Where a run's files live. One directory per run, so it can be shown,
    archived or deleted as a unit."""

    root: Path

    @property
    def store(self) -> Path:
        return self.root / "pipeline.db"

    @property
    def payloads(self) -> Path:
        return self.root / "payloads"

    @property
    def log(self) -> Path:
        return self.root / "runner.log"

    @property
    def handle(self) -> Path:
        return self.root / "handle.json"


class RunSupervisor:
    """Starts run processes and reports on them.

    Args:
        root: Directory holding one subdirectory per run.
        python: Interpreter to launch runners with.
        stale_after: Seconds without a heartbeat before a live process is
            called unresponsive.
    """

    def __init__(
        self,
        root: str | os.PathLike[str],
        python: str | None = None,
        stale_after: float = DEFAULT_STALE_AFTER_SECONDS,
    ) -> None:
        self.root = Path(root)
        self.python = python or sys.executable
        self.stale_after = stale_after

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def paths(self, run_id: str) -> RunPaths:
        """Where this run's files live, creating the directory if needed."""
        paths = RunPaths(self.root / run_id)
        paths.root.mkdir(parents=True, exist_ok=True)
        return paths

    def open_store(self, run_id: str, read_only: bool = False) -> TaskStore:
        """Open a run's store.

        The server creates the run and submits inputs through a writable store,
        then monitors through a read-only one. WAL allows both alongside the
        runner's own writer.
        """
        return TaskStore(self.paths(run_id).store, read_only=read_only)

    # ------------------------------------------------------------------
    # Launching
    # ------------------------------------------------------------------

    def launch(
        self,
        run_id: str,
        backend: str = "thread",
        tick_seconds: float = 1.0,
    ) -> RunHandle:
        """Start a runner for an already-created run, detached from this process.

        ``start_new_session`` puts the runner in its own session and process
        group, so it does not receive the signals the launcher gets -- notably
        the SIGHUP that ends a terminal or a portal session.

        Note that this is *not* by itself enough on every system: a login node
        with ``logind``'s ``KillUserProcesses=yes`` reaps a user's processes at
        logout regardless of session. Where that is set, the durable form of
        "separate process" is a Slurm allocation, and this launcher is the
        development equivalent.
        """
        paths = self.paths(run_id)
        paths.payloads.mkdir(parents=True, exist_ok=True)

        command = [
            self.python,
            "-m",
            "blackfish.pipelines.runner",
            "--run",
            run_id,
            "--store",
            str(paths.store),
            "--payloads",
            str(paths.payloads),
            "--backend",
            backend,
            "--tick-seconds",
            str(tick_seconds),
        ]

        # Append rather than truncate: a relaunch after a crash should not
        # destroy the log that explains the crash.
        with open(paths.log, "a") as log:
            log.write(
                f"\n--- launching runner at {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            log.flush()
            process = subprocess.Popen(
                command,
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                cwd=os.getcwd(),
            )

        handle = RunHandle(
            run_id=run_id,
            pid=process.pid,
            started_at=_create_time(process.pid) or time.time(),
            command=command,
        )
        self.save_handle(handle)
        logger.info("Run %s: launched runner pid=%d", run_id, handle.pid)
        return handle

    def save_handle(self, handle: RunHandle) -> None:
        self.paths(handle.run_id).handle.write_text(json.dumps(handle.to_dict()))

    def load_handle(self, run_id: str) -> RunHandle | None:
        """Recover a launch record, e.g. after the server itself restarted."""
        path = self.paths(run_id).handle
        if not path.exists():
            return None
        try:
            return RunHandle.from_dict(json.loads(path.read_text()))
        except (ValueError, KeyError):
            logger.warning("Run %s: unreadable handle at %s", run_id, path)
            return None

    # ------------------------------------------------------------------
    # Observing
    # ------------------------------------------------------------------

    def is_alive(self, handle: RunHandle) -> bool:
        """Whether the launched process is still the one running, and running.

        Three ways this can be wrong if written naively, all of them found by
        watching real processes rather than mocks:

        - **Zombies.** A dead child stays in the process table until its parent
          reaps it, and every "does this pid exist" check says yes. Since the
          launcher *is* the parent, a crashed runner would otherwise report as
          healthy forever.
        - **Recycled pids.** After a restart the supervisor is checking pids it
          did not launch in this process, so the create time is compared
          against the launch record.
        - **Orphans.** Once the launcher is gone the runner is reparented to
          init, there is no zombie, and reaping is not ours to do -- so the
          reap is best-effort and its failure is not evidence of anything.
        """
        _reap(handle.pid)
        created = _create_time(handle.pid)
        if created is None:
            return False
        if _is_zombie(handle.pid):
            return False
        # Allow a small tolerance: the create time is read just after fork, so
        # it can differ from the kernel's by a scheduling quantum.
        return abs(created - handle.started_at) < 1.0

    def observe(self, run_id: str, with_status: bool = True) -> RunObservation:
        """Report on a run, from the store and the process table.

        Args:
            run_id: The run.
            with_status: Also count queue depths. Skip it for a cheap poll of
                many runs; :meth:`~blackfish.pipelines.store.TaskStore.run_info`
                alone is enough to decide the verdict.
        """
        store = self.open_store(run_id, read_only=True)
        try:
            info = store.run_info(run_id)
            status = store.run_status(run_id) if with_status else None
        finally:
            store.close()

        handle = self.load_handle(run_id)
        alive = bool(handle and self.is_alive(handle))
        heartbeat_age = info.heartbeat_age(time.time())

        verdict = self._verdict(info, status, handle, alive, heartbeat_age)
        return RunObservation(
            run_id=run_id,
            verdict=verdict,
            alive=alive,
            pid=handle.pid if handle else None,
            heartbeat_age=heartbeat_age,
            info=info,
            status=status,
        )

    def _verdict(
        self,
        info: RunInfo,
        status: RunStatus | None,
        handle: RunHandle | None,
        alive: bool,
        heartbeat_age: float | None,
    ) -> RunVerdict:
        # Terminal facts first: a finished run stays finished whether or not a
        # process is still winding down, and whether or not anyone was watching.
        if info.state is RunState.COMPLETE or (status is not None and status.complete):
            return RunVerdict.COMPLETE
        if info.state is RunState.CANCELLED:
            return RunVerdict.CANCELLED
        if handle is None:
            return RunVerdict.QUEUED
        if not alive:
            return RunVerdict.CRASHED
        if heartbeat_age is None:
            # Never checked in: starting up, or died before it could.
            age = time.time() - handle.started_at
            return (
                RunVerdict.STARTING
                if age <= self.stale_after
                else RunVerdict.UNRESPONSIVE
            )
        if heartbeat_age > self.stale_after:
            return RunVerdict.UNRESPONSIVE
        return RunVerdict.RUNNING

    # ------------------------------------------------------------------
    # Stopping
    # ------------------------------------------------------------------

    def cancel(self, run_id: str, grace_seconds: float = DEFAULT_GRACE_SECONDS) -> bool:
        """Ask a run to stop, and make sure it does.

        SIGTERM lets the runner finish its tick and release its workers, which
        matters because those workers are Slurm allocations that would
        otherwise linger. A runner that will not stop is killed; its leases
        then expire on their own.

        Cancelling is a *command*, so unlike observation it may write: once the
        process is gone the run is recorded as cancelled here if the runner did
        not manage it itself. Otherwise a runner killed before it could write
        would leave the run looking crashed, when in fact someone asked for it
        to stop and it did.

        Returns:
            Whether a process was signalled.
        """
        handle = self.load_handle(run_id)
        signalled = handle is not None and self.is_alive(handle)

        if handle is not None and signalled:
            os.kill(handle.pid, signal.SIGTERM)
            deadline = time.monotonic() + grace_seconds
            while time.monotonic() < deadline and self.is_alive(handle):
                time.sleep(0.05)
            if self.is_alive(handle):
                logger.warning(
                    "Run %s: runner pid=%d ignored SIGTERM, killing",
                    run_id,
                    handle.pid,
                )
                try:
                    os.kill(handle.pid, signal.SIGKILL)
                except ProcessLookupError:  # pragma: no cover - raced with exit
                    pass
                # Wait for it to actually leave, so the state we write below is
                # not immediately overwritten by a runner still winding down.
                deadline = time.monotonic() + 5.0
                while time.monotonic() < deadline and self.is_alive(handle):
                    time.sleep(0.05)

        self._record_cancelled(run_id)
        return signalled

    def _record_cancelled(self, run_id: str) -> None:
        """Mark a run cancelled, unless it had already settled on its own."""
        store = self.open_store(run_id)
        try:
            info = store.run_info(run_id)
            if info.state is RunState.RUNNING:
                store.set_run_state(run_id, RunState.CANCELLED)
        except KeyError:  # pragma: no cover - run deleted underneath us
            pass
        finally:
            store.close()

    # ------------------------------------------------------------------
    # Logs
    # ------------------------------------------------------------------

    def tail_log(self, run_id: str, lines: int = 200) -> list[str]:
        """Last ``lines`` of the runner's output, for a UI panel."""
        path = self.paths(run_id).log
        if not path.exists():
            return []
        with open(path, errors="replace") as handle:
            return handle.read().splitlines()[-lines:]


def _create_time(pid: int) -> float | None:
    """The process's start time, or ``None`` if there is no such process."""
    try:
        return float(psutil.Process(pid).create_time())
    except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
        return None


def _is_zombie(pid: int) -> bool:
    """Whether the process has exited but not yet been reaped."""
    try:
        return bool(psutil.Process(pid).status() == psutil.STATUS_ZOMBIE)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def _reap(pid: int) -> None:
    """Collect an exited child, if it is ours to collect.

    Best-effort: once the launcher has been replaced the runner is an orphan
    and init reaps it, so ``ChildProcessError`` here means "not mine", not
    "something is wrong".
    """
    try:
        os.waitpid(pid, os.WNOHANG)
    except (ChildProcessError, OSError):
        pass
