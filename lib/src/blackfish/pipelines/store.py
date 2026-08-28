"""The queue substrate: a SQLite-backed task store with leases and barriers.

Design notes
------------

**Why SQLite.** A pipeline needs durable queues, at-least-once delivery and
transactional multi-queue writes. Postgres and Redis give you all three and cost
you a service to run -- which, on a shared cluster where the user may not be
able to open a port or keep a daemon alive, is the expensive part. SQLite in WAL
mode gives the same guarantees inside a single file, and the coordinator is
already a long-running process that can own it.

**Who opens the file.** Exactly one process: the coordinator. SQLite's locking
degrades badly over NFS and GPFS, which is precisely where a worker on a compute
node would have to reach it, so workers never open the database. They talk to
the coordinator (see :mod:`blackfish.pipelines.client`), which is also the only
arrangement compute nodes can support: an allocation can dial out to the login
node, but nothing can dial in.

**Why fan-in is not a special case.** The hard part of running a DAG on queues
is knowing when a job has seen everything it is ever going to see. This store
answers it without sentinels, watermarks or run windows, by making one thing
atomic: *acknowledging a task and enqueuing the tasks it produced happen in the
same transaction* (:meth:`TaskStore.complete_batch`). There is therefore no
instant at which an upstream job looks finished while its outputs are still in
flight, and the recursive definition

    complete(job) = all upstreams complete and no tasks outstanding

is exact. Sources bottom out on an explicit :meth:`TaskStore.seal`.

**Why retries do not duplicate work.** Task IDs are derived (UUIDv5) from the
parent task and the output's index within it, so re-running a batch produces the
same IDs and the insert is ignored. This matters for the one failure a worker
cannot distinguish on its own: a commit that succeeded but whose acknowledgement
was lost. The worker retries, the store no-ops, and the pipeline stays correct
without asking the user's function to be idempotent -- only its side effects
need that.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from blackfish.pipelines.spec import Cardinality, Pipeline

# Namespace for derived task IDs. Fixed for all time: changing it would make a
# resumed run re-emit every downstream task under new IDs.
_TASK_NAMESPACE = uuid.UUID("6f1f1d3a-6a54-5a5f-9c0e-1b6a8c2f0e21")

# Ceiling on the exponential retry delay. Past a few minutes a longer wait
# stops being backoff and starts being an outage nobody is watching.
MAX_RETRY_BACKOFF = 300.0

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id     TEXT PRIMARY KEY,
    pipeline   TEXT NOT NULL,
    spec       TEXT NOT NULL,
    state      TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    run_id           TEXT NOT NULL,
    job              TEXT NOT NULL,
    task_id          TEXT NOT NULL,
    payload          TEXT NOT NULL,
    state            TEXT NOT NULL,
    attempts         INTEGER NOT NULL DEFAULT 0,
    available_at     REAL NOT NULL DEFAULT 0,
    lease_expires_at REAL,
    lease_owner      TEXT,
    last_error       TEXT,
    created_at       REAL NOT NULL,
    updated_at       REAL NOT NULL,
    PRIMARY KEY (run_id, job, task_id)
);

CREATE INDEX IF NOT EXISTS tasks_by_state
    ON tasks (run_id, job, state, available_at, created_at);

CREATE INDEX IF NOT EXISTS tasks_by_lease
    ON tasks (state, lease_expires_at);

CREATE TABLE IF NOT EXISTS barriers (
    run_id TEXT NOT NULL,
    job    TEXT NOT NULL,
    sealed INTEGER NOT NULL DEFAULT 0,
    seen   INTEGER NOT NULL DEFAULT 0,
    done   INTEGER NOT NULL DEFAULT 0,
    failed INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (run_id, job)
);

CREATE TABLE IF NOT EXISTS results (
    run_id     TEXT NOT NULL,
    job        TEXT NOT NULL,
    task_id    TEXT NOT NULL,
    payload    TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY (run_id, job, task_id)
);
"""


class TaskState(StrEnum):
    """Lifecycle of a single task."""

    READY = "ready"
    LEASED = "leased"
    DONE = "done"
    FAILED = "failed"
    """Dead-lettered: attempts exhausted. Counted as settled so it cannot block
    the run from ever completing, and reported at the end."""


class RunState(StrEnum):
    """Lifecycle of a pipeline run."""

    RUNNING = "running"
    COMPLETE = "complete"
    """Every job drained. Check ``dead_letters`` before trusting the output."""
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class Task:
    """A leased unit of work."""

    run_id: str
    job: str
    task_id: str
    payload: str
    """The payload *reference*, to be resolved through a
    :class:`~blackfish.pipelines.payload.PayloadStore`."""
    attempts: int


@dataclass(frozen=True, slots=True)
class JobStatus:
    """Queue depth and completion state for one job of one run."""

    job: str
    ready: int
    leased: int
    done: int
    failed: int
    seen: int
    sealed: bool
    upstream_complete: bool
    complete: bool
    delayed: int = 0
    """Ready tasks still serving a retry backoff. Counted inside ``ready``, and
    therefore inside ``outstanding``: a task waiting to be retried is emphati-
    cally not finished, and a job holding one must not read as complete."""

    @property
    def outstanding(self) -> int:
        """Tasks accepted but not yet settled (ready, delayed or leased)."""
        return self.ready + self.leased

    @property
    def backlog(self) -> int:
        """Work a worker could pick up right now. What the autoscaler reacts to.

        Excludes tasks serving a backoff, so a job whose queue is entirely
        rate-limited retries does not hold workers that have nothing to do.
        """
        return self.ready - self.delayed


@dataclass(frozen=True, slots=True)
class RunStatus:
    """Completion state of a whole run."""

    run_id: str
    pipeline: str
    state: RunState
    jobs: tuple[JobStatus, ...]

    def job(self, name: str) -> JobStatus:
        for status in self.jobs:
            if status.job == name:
                return status
        raise KeyError(f"Run {self.run_id} has no job named '{name}'")

    @property
    def complete(self) -> bool:
        return all(job.complete for job in self.jobs)

    @property
    def dead_letters(self) -> int:
        return sum(job.failed for job in self.jobs)


class TaskStore:
    """Durable queues, leases and completion barriers for pipeline runs.

    One process owns the database file. Every mutating method runs in a single
    ``BEGIN IMMEDIATE`` transaction, so a crash mid-method leaves the store in
    the state it had before the call.

    Args:
        path: Database file. Use ``":memory:"`` for tests.
        clock: Time source, injectable so lease expiry can be tested without
            sleeping.
    """

    def __init__(
        self,
        path: str | Path = ":memory:",
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.path = str(path)
        self._clock = clock
        # One connection, serialized by a lock. The coordinator's own
        # concurrency is cooperative (asyncio), and worker traffic arrives over
        # HTTP, so a single writer is not the bottleneck -- and it sidesteps
        # SQLite's write-lock contention entirely.
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.isolation_level = None  # explicit transactions only
        if self.path != ":memory:":
            self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.executescript(_SCHEMA)
        self._migrate()

    def _migrate(self) -> None:
        """Add columns introduced after a store may already have been created.

        The prototype ships no Alembic migrations, and a developer with an
        existing database should get a working store rather than an opaque
        "no such column" on the next lease.
        """
        columns = {
            row["name"] for row in self._conn.execute("PRAGMA table_info(tasks)")
        }
        if "available_at" not in columns:
            self._conn.execute(
                "ALTER TABLE tasks ADD COLUMN available_at REAL NOT NULL DEFAULT 0"
            )

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __enter__(self) -> "TaskStore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    class _Transaction:
        def __init__(self, store: "TaskStore") -> None:
            self._store = store

        def __enter__(self) -> sqlite3.Connection:
            self._store._lock.acquire()
            self._store._conn.execute("BEGIN IMMEDIATE")
            return self._store._conn

        def __exit__(self, exc_type: object, *_: object) -> None:
            try:
                if exc_type is None:
                    self._store._conn.execute("COMMIT")
                else:
                    self._store._conn.execute("ROLLBACK")
            finally:
                self._store._lock.release()

    def _tx(self) -> "TaskStore._Transaction":
        return TaskStore._Transaction(self)

    # ------------------------------------------------------------------
    # Runs
    # ------------------------------------------------------------------

    def create_run(self, pipeline: Pipeline, run_id: str | None = None) -> str:
        """Register a run of ``pipeline`` and return its ID."""
        rid = run_id or uuid.uuid4().hex
        now = self._clock()
        with self._tx() as conn:
            conn.execute(
                "INSERT INTO runs (run_id, pipeline, spec, state, created_at,"
                " updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    rid,
                    pipeline.name,
                    json.dumps(pipeline.to_dict()),
                    str(RunState.RUNNING),
                    now,
                    now,
                ),
            )
            conn.executemany(
                "INSERT INTO barriers (run_id, job) VALUES (?, ?)",
                [(rid, job.name) for job in pipeline.jobs],
            )
        return rid

    def get_pipeline(self, run_id: str) -> Pipeline:
        """Return the pipeline a run was created from.

        Raises:
            KeyError: If the run does not exist.
        """
        with self._lock:
            row = self._conn.execute(
                "SELECT spec FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"No such run: {run_id}")
        spec: dict[str, Any] = json.loads(row["spec"])
        return Pipeline.from_dict(spec)

    def set_run_state(self, run_id: str, state: RunState) -> None:
        with self._tx() as conn:
            conn.execute(
                "UPDATE runs SET state = ?, updated_at = ? WHERE run_id = ?",
                (str(state), self._clock(), run_id),
            )

    def list_runs(self) -> tuple[tuple[str, str, RunState], ...]:
        """Return ``(run_id, pipeline, state)`` for every run, newest first."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT run_id, pipeline, state FROM runs ORDER BY created_at DESC"
            ).fetchall()
        return tuple(
            (row["run_id"], row["pipeline"], RunState(row["state"])) for row in rows
        )

    # ------------------------------------------------------------------
    # Producing work
    # ------------------------------------------------------------------

    def submit(
        self,
        run_id: str,
        job: str,
        payloads: Sequence[str],
        keys: Sequence[str] | None = None,
    ) -> int:
        """Enqueue inputs for a source job.

        Args:
            run_id: The run.
            job: A source job of the run's pipeline.
            payloads: Payload references (see
                :class:`~blackfish.pipelines.payload.PayloadStore`).
            keys: Optional stable identity per payload. Supplying one makes the
                submission idempotent -- re-submitting the same key is ignored
                -- which is what you want when the inputs are files on disk and
                the run may be resumed.

        Returns:
            The number of tasks actually enqueued (duplicates are skipped).
        """
        if keys is not None and len(keys) != len(payloads):
            raise ValueError("keys and payloads must be the same length")
        task_ids = [
            derive_task_id(run_id, job, "input", keys[i] if keys else uuid.uuid4().hex)
            for i in range(len(payloads))
        ]
        with self._tx() as conn:
            inserted = self._insert_tasks(conn, run_id, job, task_ids, payloads)
        return inserted

    def seal(self, run_id: str, job: str) -> None:
        """Declare that no further inputs will be submitted to a source job.

        Until a source is sealed the run can never complete: an empty queue is
        indistinguishable from a queue whose producer is merely slow.
        """
        with self._tx() as conn:
            conn.execute(
                "UPDATE barriers SET sealed = 1 WHERE run_id = ? AND job = ?",
                (run_id, job),
            )

    # ------------------------------------------------------------------
    # Consuming work
    # ------------------------------------------------------------------

    def lease(
        self,
        run_id: str,
        job: str,
        max_tasks: int,
        lease_seconds: int,
        owner: str,
    ) -> tuple[Task, ...]:
        """Claim up to ``max_tasks`` ready tasks for ``lease_seconds``.

        Claiming is exclusive: a leased task is invisible to other workers until
        it is settled or its lease expires. Returns fewer tasks than asked for
        when fewer are queued -- a half-full batch is never held back.

        A task still serving its retry backoff is skipped, so a job whose
        downstream service is rate-limiting it does not spin.
        """
        if max_tasks < 1:
            raise ValueError("max_tasks must be >= 1")
        now = self._clock()
        with self._tx() as conn:
            # ``rowid`` breaks ties within a timestamp, which is what makes
            # this FIFO: several tasks enqueued in one transaction share a
            # ``created_at``, and ordering them by ID would shuffle them.
            rows = conn.execute(
                "SELECT task_id, payload, attempts FROM tasks"
                " WHERE run_id = ? AND job = ? AND state = ? AND available_at <= ?"
                " ORDER BY created_at, rowid LIMIT ?",
                (run_id, job, str(TaskState.READY), now, max_tasks),
            ).fetchall()
            if not rows:
                return ()
            expiry = now + lease_seconds
            conn.executemany(
                "UPDATE tasks SET state = ?, attempts = attempts + 1,"
                " lease_expires_at = ?, lease_owner = ?, updated_at = ?"
                " WHERE run_id = ? AND job = ? AND task_id = ?",
                [
                    (
                        str(TaskState.LEASED),
                        expiry,
                        owner,
                        now,
                        run_id,
                        job,
                        row["task_id"],
                    )
                    for row in rows
                ],
            )
        return tuple(
            Task(
                run_id=run_id,
                job=job,
                task_id=row["task_id"],
                payload=row["payload"],
                attempts=row["attempts"] + 1,
            )
            for row in rows
        )

    def complete_batch(
        self,
        run_id: str,
        job: str,
        outputs: Mapping[str, Sequence[str]],
        downstream: Sequence[str],
        record_results: bool = False,
    ) -> int:
        """Acknowledge tasks and enqueue what they produced, atomically.

        This single transaction is what makes the completion rule exact: an
        upstream job's tasks never read as settled before the tasks they
        produced are visible to the downstream queues.

        Args:
            run_id: The run.
            job: The job whose tasks are being acknowledged.
            outputs: Payload references produced by each acknowledged task,
                keyed by task ID. A ``1:1`` task maps to exactly one reference,
                a ``1:N`` task to zero or more.
            downstream: Jobs to deliver every output to. Each downstream job
                receives its own copy of the task.
            record_results: Whether to also record the outputs as run results.
                Set for sink jobs, whose outputs have nowhere else to go.

        Returns:
            The number of tasks that actually transitioned to ``done``. Zero
            means the batch had already been acknowledged -- a retry after a
            lost response, not an error.
        """
        now = self._clock()
        with self._tx() as conn:
            settled = 0
            for task_id in outputs:
                cursor = conn.execute(
                    "UPDATE tasks SET state = ?, lease_expires_at = NULL,"
                    " lease_owner = NULL, updated_at = ?"
                    " WHERE run_id = ? AND job = ? AND task_id = ? AND state = ?",
                    (
                        str(TaskState.DONE),
                        now,
                        run_id,
                        job,
                        task_id,
                        str(TaskState.LEASED),
                    ),
                )
                settled += cursor.rowcount

            for parent_id, refs in outputs.items():
                for child_job in downstream:
                    child_ids = [
                        derive_task_id(run_id, child_job, parent_id, str(index))
                        for index in range(len(refs))
                    ]
                    self._insert_tasks(conn, run_id, child_job, child_ids, refs)
                if record_results:
                    conn.executemany(
                        "INSERT OR IGNORE INTO results"
                        " (run_id, job, task_id, payload, created_at)"
                        " VALUES (?, ?, ?, ?, ?)",
                        [
                            (
                                run_id,
                                job,
                                derive_task_id(run_id, job, parent_id, str(index)),
                                ref,
                                now,
                            )
                            for index, ref in enumerate(refs)
                        ],
                    )

            if settled:
                conn.execute(
                    "UPDATE barriers SET done = done + ? WHERE run_id = ? AND job = ?",
                    (settled, run_id, job),
                )
        return settled

    def fold_batch(
        self,
        run_id: str,
        job: str,
        task_ids: Sequence[str],
        partial: str,
    ) -> int:
        """Acknowledge a reduce batch and push its combined value back.

        The partial's ID is derived from the IDs it combines, so a retried fold
        lands on the same row instead of adding a second partial that would
        double-count the reduce.
        """
        now = self._clock()
        partial_id = derive_task_id(run_id, job, "fold", "|".join(sorted(task_ids)))
        with self._tx() as conn:
            settled = 0
            for task_id in task_ids:
                cursor = conn.execute(
                    "UPDATE tasks SET state = ?, lease_expires_at = NULL,"
                    " lease_owner = NULL, updated_at = ?"
                    " WHERE run_id = ? AND job = ? AND task_id = ? AND state = ?",
                    (
                        str(TaskState.DONE),
                        now,
                        run_id,
                        job,
                        task_id,
                        str(TaskState.LEASED),
                    ),
                )
                settled += cursor.rowcount
            if settled:
                self._insert_tasks(conn, run_id, job, [partial_id], [partial])
                conn.execute(
                    "UPDATE barriers SET done = done + ? WHERE run_id = ? AND job = ?",
                    (settled, run_id, job),
                )
        return settled

    def release(self, run_id: str, job: str, task_ids: Sequence[str]) -> None:
        """Return leased tasks to the queue *without* counting an attempt.

        Used when a worker declines work it cannot usefully do yet -- a reduce
        worker that leased a single partial while more are still in flight --
        so that backing off never spends a task's retry budget.
        """
        now = self._clock()
        with self._tx() as conn:
            conn.executemany(
                "UPDATE tasks SET state = ?, attempts = MAX(attempts - 1, 0),"
                " available_at = ?, lease_expires_at = NULL, lease_owner = NULL,"
                " updated_at = ?"
                " WHERE run_id = ? AND job = ? AND task_id = ? AND state = ?",
                [
                    (
                        str(TaskState.READY),
                        now,
                        now,
                        run_id,
                        job,
                        tid,
                        str(TaskState.LEASED),
                    )
                    for tid in task_ids
                ],
            )

    def fail_batch(
        self,
        run_id: str,
        job: str,
        task_ids: Sequence[str],
        error: str,
        max_attempts: int,
        retry_backoff: float = 0.0,
    ) -> tuple[int, int]:
        """Record a failed batch, retrying or dead-lettering each task.

        A retried task is held for ``retry_backoff * 2 ** (attempts - 1)``
        seconds, capped at :data:`MAX_RETRY_BACKOFF`. Without that, a batch
        failing against a rate-limited service is re-leased immediately by the
        same worker, which spends the task's whole attempt budget in
        milliseconds and hammers whatever failed.

        Returns:
            ``(retried, dead_lettered)``.
        """
        now = self._clock()
        retried = 0
        dead = 0
        with self._tx() as conn:
            for task_id in task_ids:
                row = conn.execute(
                    "SELECT attempts FROM tasks"
                    " WHERE run_id = ? AND job = ? AND task_id = ? AND state = ?",
                    (run_id, job, task_id, str(TaskState.LEASED)),
                ).fetchone()
                if row is None:
                    continue
                if row["attempts"] >= max_attempts:
                    conn.execute(
                        "UPDATE tasks SET state = ?, last_error = ?,"
                        " lease_expires_at = NULL, lease_owner = NULL,"
                        " updated_at = ? WHERE run_id = ? AND job = ? AND task_id = ?",
                        (str(TaskState.FAILED), error, now, run_id, job, task_id),
                    )
                    dead += 1
                else:
                    delay = min(
                        retry_backoff * (2 ** (int(row["attempts"]) - 1)),
                        MAX_RETRY_BACKOFF,
                    )
                    conn.execute(
                        "UPDATE tasks SET state = ?, last_error = ?,"
                        " available_at = ?, lease_expires_at = NULL,"
                        " lease_owner = NULL,"
                        " updated_at = ? WHERE run_id = ? AND job = ? AND task_id = ?",
                        (
                            str(TaskState.READY),
                            error,
                            now + delay,
                            now,
                            run_id,
                            job,
                            task_id,
                        ),
                    )
                    retried += 1
            if dead:
                conn.execute(
                    "UPDATE barriers SET failed = failed + ?"
                    " WHERE run_id = ? AND job = ?",
                    (dead, run_id, job),
                )
        return retried, dead

    def reclaim_expired(self, run_id: str | None = None) -> int:
        """Return tasks whose lease has expired to the queue.

        A worker that dies mid-batch -- preempted, out of walltime, OOM-killed
        -- leaves its tasks leased. Nothing recovers them except this, so the
        coordinator calls it every tick.

        Returns:
            The number of tasks reclaimed.
        """
        now = self._clock()
        with self._tx() as conn:
            if run_id is None:
                cursor = conn.execute(
                    "UPDATE tasks SET state = ?, available_at = ?,"
                    " lease_expires_at = NULL, lease_owner = NULL, updated_at = ?"
                    " WHERE state = ? AND lease_expires_at <= ?",
                    (str(TaskState.READY), now, now, str(TaskState.LEASED), now),
                )
            else:
                cursor = conn.execute(
                    "UPDATE tasks SET state = ?, available_at = ?,"
                    " lease_expires_at = NULL, lease_owner = NULL, updated_at = ?"
                    " WHERE run_id = ? AND state = ? AND lease_expires_at <= ?",
                    (
                        str(TaskState.READY),
                        now,
                        now,
                        run_id,
                        str(TaskState.LEASED),
                        now,
                    ),
                )
            return cursor.rowcount

    # ------------------------------------------------------------------
    # Reduce finalization
    # ------------------------------------------------------------------

    def finalize_reduce(
        self,
        run_id: str,
        job: str,
        task_id: str,
        downstream: Sequence[str],
        record_results: bool = False,
    ) -> bool:
        """Emit the last surviving partial of a reduce, if it really is the last.

        The caller must hold the lease on ``task_id``. The check and the emit
        share a transaction, so a partial that is still being folded elsewhere,
        or an upstream job that has not finished, blocks finalization rather
        than racing it.

        Returns:
            ``True`` if the reduce was finalized.
        """
        with self._tx() as conn:
            if not self._upstream_complete(conn, run_id, job):
                return False
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM tasks WHERE run_id = ? AND job = ?"
                " AND state IN (?, ?)",
                (run_id, job, str(TaskState.READY), str(TaskState.LEASED)),
            ).fetchone()
            if row["n"] != 1:
                return False
            payload_row = conn.execute(
                "SELECT payload FROM tasks"
                " WHERE run_id = ? AND job = ? AND task_id = ? AND state = ?",
                (run_id, job, task_id, str(TaskState.LEASED)),
            ).fetchone()
            if payload_row is None:
                return False

            now = self._clock()
            conn.execute(
                "UPDATE tasks SET state = ?, lease_expires_at = NULL,"
                " lease_owner = NULL, updated_at = ?"
                " WHERE run_id = ? AND job = ? AND task_id = ?",
                (str(TaskState.DONE), now, run_id, job, task_id),
            )
            conn.execute(
                "UPDATE barriers SET done = done + 1 WHERE run_id = ? AND job = ?",
                (run_id, job),
            )
            ref = payload_row["payload"]
            for child_job in downstream:
                child_id = derive_task_id(run_id, child_job, task_id, "0")
                self._insert_tasks(conn, run_id, child_job, [child_id], [ref])
            if record_results:
                conn.execute(
                    "INSERT OR IGNORE INTO results"
                    " (run_id, job, task_id, payload, created_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (run_id, job, task_id, ref, now),
                )
        return True

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def job_status(self, run_id: str, job: str) -> JobStatus:
        with self._lock:
            return self._job_status(self._conn, run_id, job)

    def run_status(self, run_id: str) -> RunStatus:
        """Completion state of every job, evaluated upstream-first."""
        pipeline = self.get_pipeline(run_id)
        with self._lock:
            row = self._conn.execute(
                "SELECT pipeline, state FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"No such run: {run_id}")
            statuses: dict[str, JobStatus] = {}
            for spec in pipeline.toposorted():
                statuses[spec.name] = self._job_status(
                    self._conn, run_id, spec.name, statuses
                )
        return RunStatus(
            run_id=run_id,
            pipeline=row["pipeline"],
            state=RunState(row["state"]),
            jobs=tuple(statuses[spec.name] for spec in pipeline.jobs),
        )

    def results(self, run_id: str, job: str | None = None) -> tuple[str, ...]:
        """Payload references recorded by sink jobs, oldest first."""
        with self._lock:
            if job is None:
                rows = self._conn.execute(
                    "SELECT payload FROM results WHERE run_id = ?"
                    " ORDER BY created_at, rowid",
                    (run_id,),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT payload FROM results WHERE run_id = ? AND job = ?"
                    " ORDER BY created_at, rowid",
                    (run_id, job),
                ).fetchall()
        return tuple(row["payload"] for row in rows)

    def dead_letters(self, run_id: str) -> tuple[tuple[str, str, str], ...]:
        """``(job, task_id, last_error)`` for every dead-lettered task."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT job, task_id, last_error FROM tasks"
                " WHERE run_id = ? AND state = ? ORDER BY job, task_id",
                (run_id, str(TaskState.FAILED)),
            ).fetchall()
        return tuple(
            (row["job"], row["task_id"], row["last_error"] or "") for row in rows
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _insert_tasks(
        self,
        conn: sqlite3.Connection,
        run_id: str,
        job: str,
        task_ids: Sequence[str],
        payloads: Sequence[str],
    ) -> int:
        """Insert tasks, skipping IDs already present, and bump ``seen``."""
        now = self._clock()
        inserted = 0
        for task_id, payload in zip(task_ids, payloads, strict=True):
            cursor = conn.execute(
                "INSERT OR IGNORE INTO tasks (run_id, job, task_id, payload,"
                " state, available_at, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, job, task_id, payload, str(TaskState.READY), now, now, now),
            )
            inserted += cursor.rowcount
        if inserted:
            conn.execute(
                "UPDATE barriers SET seen = seen + ? WHERE run_id = ? AND job = ?",
                (inserted, run_id, job),
            )
        return inserted

    def _job_status(
        self,
        conn: sqlite3.Connection,
        run_id: str,
        job: str,
        known: Mapping[str, JobStatus] | None = None,
    ) -> JobStatus:
        counts = {state: 0 for state in TaskState}
        for row in conn.execute(
            "SELECT state, COUNT(*) AS n FROM tasks WHERE run_id = ? AND job = ?"
            " GROUP BY state",
            (run_id, job),
        ):
            counts[TaskState(row["state"])] = row["n"]
        delayed_row = conn.execute(
            "SELECT COUNT(*) AS n FROM tasks WHERE run_id = ? AND job = ?"
            " AND state = ? AND available_at > ?",
            (run_id, job, str(TaskState.READY), self._clock()),
        ).fetchone()
        barrier = conn.execute(
            "SELECT sealed, seen FROM barriers WHERE run_id = ? AND job = ?",
            (run_id, job),
        ).fetchone()
        sealed = bool(barrier["sealed"]) if barrier else False
        seen = barrier["seen"] if barrier else 0

        pipeline = self.get_pipeline(run_id)
        parents = pipeline.upstream(job)
        if not parents:
            upstream_complete = sealed
        elif known is not None and all(parent in known for parent in parents):
            # Evaluated in topological order, so every parent's verdict is
            # already computed: no need to re-walk the graph per job.
            upstream_complete = all(known[parent].complete for parent in parents)
        else:
            upstream_complete = self._upstream_complete(conn, run_id, job)

        outstanding = counts[TaskState.READY] + counts[TaskState.LEASED]
        return JobStatus(
            job=job,
            ready=counts[TaskState.READY],
            leased=counts[TaskState.LEASED],
            done=counts[TaskState.DONE],
            failed=counts[TaskState.FAILED],
            seen=seen,
            sealed=sealed,
            upstream_complete=upstream_complete,
            complete=upstream_complete and outstanding == 0,
            delayed=int(delayed_row["n"]),
        )

    def _upstream_complete(
        self, conn: sqlite3.Connection, run_id: str, job: str
    ) -> bool:
        """Whether ``job`` can still receive input.

        For a source that is its own ``sealed`` flag: an empty queue means
        nothing until someone says no more work is coming. For any other job it
        is whether every upstream has finished, where finished means the
        upstream can itself receive no more input and has drained what it had.
        The recursion terminates because the pipeline is acyclic.
        """
        pipeline = self.get_pipeline(run_id)

        def sealed(name: str) -> bool:
            barrier = conn.execute(
                "SELECT sealed FROM barriers WHERE run_id = ? AND job = ?",
                (run_id, name),
            ).fetchone()
            return barrier is not None and bool(barrier["sealed"])

        def drained(name: str) -> bool:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM tasks WHERE run_id = ? AND job = ?"
                " AND state IN (?, ?)",
                (run_id, name, str(TaskState.READY), str(TaskState.LEASED)),
            ).fetchone()
            return int(row["n"]) == 0

        def closed(name: str) -> bool:
            parents = pipeline.upstream(name)
            if not parents:
                return sealed(name)
            return all(closed(parent) and drained(parent) for parent in parents)

        return closed(job)


def derive_task_id(run_id: str, job: str, parent: str, index: str) -> str:
    """Derive the stable ID of a task from what produced it.

    Same parent, same position, same ID -- which is what makes re-running a
    batch after a lost acknowledgement a no-op instead of a duplicate.
    """
    return uuid.uuid5(_TASK_NAMESPACE, f"{run_id}|{job}|{parent}|{index}").hex


def cardinality_check(
    cardinality: Cardinality, inputs: Sequence[Any], outputs: Any
) -> list[list[Any]]:
    """Validate a function's return against its declared cardinality.

    Returns the outputs normalized to one list per input, so callers can treat
    every cardinality the same way afterwards.

    Raises:
        ValueError: If the shape does not match the declaration. This is a bug
            in the user's function, and it is worth catching at the boundary --
            a ``1:1`` job that quietly returns the wrong number of values
            misaligns every downstream task.
    """
    if cardinality is Cardinality.ONE_TO_ONE:
        if not isinstance(outputs, Sequence) or isinstance(outputs, (str, bytes)):
            raise ValueError(
                f"A {cardinality} job must return a sequence, got"
                f" {type(outputs).__name__}"
            )
        if len(outputs) != len(inputs):
            raise ValueError(
                f"A {cardinality} job must return one output per input:"
                f" got {len(outputs)} for {len(inputs)} inputs"
            )
        return [[item] for item in outputs]

    if cardinality is Cardinality.ONE_TO_MANY:
        if not isinstance(outputs, Sequence) or isinstance(outputs, (str, bytes)):
            raise ValueError(
                f"A {cardinality} job must return a sequence of sequences, got"
                f" {type(outputs).__name__}"
            )
        if len(outputs) != len(inputs):
            raise ValueError(
                f"A {cardinality} job must return one group of outputs per"
                f" input: got {len(outputs)} groups for {len(inputs)} inputs"
            )
        groups: list[list[Any]] = []
        for index, group in enumerate(outputs):
            if not isinstance(group, Sequence) or isinstance(group, (str, bytes)):
                raise ValueError(
                    f"A {cardinality} job must return a sequence of sequences;"
                    f" group {index} is {type(group).__name__}."
                    " Wrap single values in a list."
                )
            groups.append(list(group))
        return groups

    raise ValueError(f"{cardinality} outputs are not emitted per input")
