"""How a worker reaches the queues.

Two implementations satisfy :class:`QueueClient`:

- :class:`~blackfish.pipelines.store.TaskStore` itself, when the worker runs on
  the coordinator's node (a ``LOGIN``-placed job, or a whole pipeline running on
  one machine for development).
- :class:`HttpQueueClient`, when the worker runs inside a Slurm allocation and
  can only dial out.

The split is deliberate: the SQLite file is opened by exactly one process, so a
worker on a compute node never has to lock a database over a parallel
filesystem, which is the failure mode that makes "just put the queue on the
shared FS" quietly lose tasks.
"""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

import httpx

from blackfish.pipelines.spec import Pipeline
from blackfish.pipelines.store import JobStatus, RunState, RunStatus, Task

# Workers keep polling across a coordinator restart or a transient network
# blip rather than dying and losing their loaded model.
DEFAULT_MAX_RETRIES = 5
DEFAULT_BACKOFF_SECONDS = 1.0
DEFAULT_MAX_BACKOFF_SECONDS = 30.0
DEFAULT_TIMEOUT_SECONDS = 30.0


class QueueUnavailable(RuntimeError):
    """The coordinator could not be reached.

    Distinct from every other error a queue call can raise, because the right
    response is different: a worker that cannot reach the coordinator should
    *wait*, holding the model it has already paid to load, rather than treat
    the outage as a failure of the work. A login node reboots; a laptop lid
    closes. Neither should cost a cluster's worth of warm workers.
    """


class QueueClient(Protocol):
    """The queue operations a worker performs."""

    def get_pipeline(self, run_id: str) -> Pipeline: ...

    def lease(
        self,
        run_id: str,
        job: str,
        max_tasks: int,
        lease_seconds: int,
        owner: str,
    ) -> tuple[Task, ...]: ...

    def complete_batch(
        self,
        run_id: str,
        job: str,
        outputs: Mapping[str, Sequence[str]],
        downstream: Sequence[str],
        record_results: bool = False,
    ) -> int: ...

    def fold_batch(
        self, run_id: str, job: str, task_ids: Sequence[str], partial: str
    ) -> int: ...

    def release(self, run_id: str, job: str, task_ids: Sequence[str]) -> None: ...

    def fail_batch(
        self,
        run_id: str,
        job: str,
        task_ids: Sequence[str],
        error: str,
        max_attempts: int,
        retry_backoff: float = 0.0,
    ) -> tuple[int, int]: ...

    def finalize_reduce(
        self,
        run_id: str,
        job: str,
        task_id: str,
        downstream: Sequence[str],
        record_results: bool = False,
    ) -> bool: ...


class StoreClient(QueueClient, Protocol):
    """Everything the *coordinator* needs from the store.

    A superset of :class:`QueueClient`, which is what a worker needs. Splitting
    them this way is what lets the two halves of the coordinator live in
    different places: the queue service must be always up and reachable from
    compute nodes, while the control plane -- owning the DAG, deciding worker
    counts, submitting allocations -- can tolerate being away for minutes.

    :class:`~blackfish.pipelines.store.TaskStore` satisfies this directly, and
    :class:`HttpStoreClient` satisfies it over the wire, so where the control
    plane runs is a configuration rather than a rewrite.
    """

    def create_run(self, pipeline: Pipeline, run_id: str | None = None) -> str: ...

    def submit(
        self,
        run_id: str,
        job: str,
        payloads: Sequence[str],
        keys: Sequence[str] | None = None,
    ) -> int: ...

    def seal(self, run_id: str, job: str) -> None: ...

    def reclaim_expired(self, run_id: str | None = None) -> int: ...

    def run_status(self, run_id: str) -> RunStatus: ...

    def set_run_state(self, run_id: str, state: RunState) -> None: ...

    def results(self, run_id: str, job: str | None = None) -> tuple[str, ...]: ...

    def dead_letters(self, run_id: str) -> tuple[tuple[str, str, str], ...]: ...


class HttpQueueClient:
    """A :class:`QueueClient` that talks to the coordinator over HTTP.

    Every call is retried on transport errors and 5xx responses. Retrying is
    safe because the store's mutating operations are idempotent: settling an
    already-settled batch is a no-op, and derived task IDs make a repeated emit
    land on the rows it landed on the first time.

    Args:
        base_url: Root URL of the Blackfish coordinator.
        token: Optional bearer token, when the coordinator requires auth.
        timeout: Per-request timeout in seconds.
        max_retries: Attempts per call before giving up.
    """

    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            headers=headers,
            transport=transport,
        )
        self.max_retries = max_retries

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HttpQueueClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Perform one call, retrying only what is worth retrying.

        Transport failures and 5xx responses are the coordinator being away,
        and are retried. A 4xx is this caller asking for something wrong -- an
        unknown run, a malformed body -- and retrying it four more times only
        delays the error, so it is raised immediately.
        """
        last: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self._client.request(method, path, **kwargs)
            except httpx.TransportError as exc:
                last = exc
            else:
                if response.status_code < 500:
                    response.raise_for_status()
                    return response.json()
                last = httpx.HTTPStatusError(
                    f"{response.status_code} from {path}",
                    request=response.request,
                    response=response,
                )
            if attempt == self.max_retries - 1:
                break
            time.sleep(
                min(
                    DEFAULT_BACKOFF_SECONDS * (2**attempt),
                    DEFAULT_MAX_BACKOFF_SECONDS,
                )
            )
        raise QueueUnavailable(
            f"Coordinator unreachable after {self.max_retries} attempts: {last}"
        ) from last

    def _job_path(self, run_id: str, job: str, action: str) -> str:
        return f"/pipelines/runs/{run_id}/jobs/{job}/{action}"

    # ------------------------------------------------------------------

    def get_pipeline(self, run_id: str) -> Pipeline:
        data = self._request("GET", f"/pipelines/runs/{run_id}/spec")
        return Pipeline.from_dict(data)

    def lease(
        self,
        run_id: str,
        job: str,
        max_tasks: int,
        lease_seconds: int,
        owner: str,
    ) -> tuple[Task, ...]:
        data = self._request(
            "POST",
            self._job_path(run_id, job, "lease"),
            json={
                "max_tasks": max_tasks,
                "lease_seconds": lease_seconds,
                "owner": owner,
            },
        )
        return tuple(
            Task(
                run_id=run_id,
                job=job,
                task_id=item["task_id"],
                payload=item["payload"],
                attempts=item["attempts"],
            )
            for item in data["tasks"]
        )

    def complete_batch(
        self,
        run_id: str,
        job: str,
        outputs: Mapping[str, Sequence[str]],
        downstream: Sequence[str],
        record_results: bool = False,
    ) -> int:
        data = self._request(
            "POST",
            self._job_path(run_id, job, "complete"),
            json={
                "outputs": {key: list(value) for key, value in outputs.items()},
                "downstream": list(downstream),
                "record_results": record_results,
            },
        )
        return int(data["settled"])

    def fold_batch(
        self, run_id: str, job: str, task_ids: Sequence[str], partial: str
    ) -> int:
        data = self._request(
            "POST",
            self._job_path(run_id, job, "fold"),
            json={"task_ids": list(task_ids), "partial": partial},
        )
        return int(data["settled"])

    def release(self, run_id: str, job: str, task_ids: Sequence[str]) -> None:
        self._request(
            "POST",
            self._job_path(run_id, job, "release"),
            json={"task_ids": list(task_ids)},
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
        data = self._request(
            "POST",
            self._job_path(run_id, job, "fail"),
            json={
                "task_ids": list(task_ids),
                "error": error,
                "max_attempts": max_attempts,
                "retry_backoff": retry_backoff,
            },
        )
        return int(data["retried"]), int(data["dead_lettered"])

    def finalize_reduce(
        self,
        run_id: str,
        job: str,
        task_id: str,
        downstream: Sequence[str],
        record_results: bool = False,
    ) -> bool:
        data = self._request(
            "POST",
            self._job_path(run_id, job, "finalize"),
            json={
                "task_id": task_id,
                "downstream": list(downstream),
                "record_results": record_results,
            },
        )
        return bool(data["finalized"])


class HttpStoreClient(HttpQueueClient):
    """A :class:`StoreClient` over HTTP: a coordinator driving a remote store.

    This is what a control plane running away from the cluster uses -- on a
    workstation, in a container, at the far end of an SSH tunnel. It carries
    only references and counts, never payload bytes, so the process using it
    needs no access to the cluster's filesystem *provided* every payload stays
    inline. Pair it with
    ``PayloadStore(allow_spill=False)``, which turns the moment that assumption
    breaks into an error at submit time rather than a file no worker can read.
    """

    def create_run(self, pipeline: Pipeline, run_id: str | None = None) -> str:
        data = self._request(
            "POST",
            "/pipelines/runs",
            json={"pipeline": pipeline.to_dict(), "run_id": run_id},
        )
        return str(data["run_id"])

    def submit(
        self,
        run_id: str,
        job: str,
        payloads: Sequence[str],
        keys: Sequence[str] | None = None,
    ) -> int:
        data = self._request(
            "POST",
            self._job_path(run_id, job, "submit"),
            json={
                "payloads": list(payloads),
                "keys": list(keys) if keys is not None else None,
            },
        )
        return int(data["enqueued"])

    def seal(self, run_id: str, job: str) -> None:
        self._request("POST", self._job_path(run_id, job, "seal"), json={})

    def reclaim_expired(self, run_id: str | None = None) -> int:
        path = (
            "/pipelines/reclaim"
            if run_id is None
            else f"/pipelines/runs/{run_id}/reclaim"
        )
        data = self._request("POST", path, json={})
        return int(data["reclaimed"])

    def run_status(self, run_id: str) -> RunStatus:
        data = self._request("GET", f"/pipelines/runs/{run_id}/status")
        return RunStatus(
            run_id=data["run_id"],
            pipeline=data["pipeline"],
            state=RunState(data["state"]),
            jobs=tuple(
                JobStatus(
                    job=job["job"],
                    ready=job["ready"],
                    leased=job["leased"],
                    done=job["done"],
                    failed=job["failed"],
                    seen=job["seen"],
                    sealed=job["sealed"],
                    upstream_complete=job["upstream_complete"],
                    complete=job["complete"],
                    delayed=job["delayed"],
                )
                for job in data["jobs"]
            ),
        )

    def set_run_state(self, run_id: str, state: RunState) -> None:
        self._request(
            "POST", f"/pipelines/runs/{run_id}/state", json={"state": str(state)}
        )

    def results(self, run_id: str, job: str | None = None) -> tuple[str, ...]:
        params = {"job": job} if job is not None else None
        data = self._request("GET", f"/pipelines/runs/{run_id}/results", params=params)
        return tuple(data["payloads"])

    def dead_letters(self, run_id: str) -> tuple[tuple[str, str, str], ...]:
        data = self._request("GET", f"/pipelines/runs/{run_id}/dead-letters")
        return tuple(
            (item["job"], item["task_id"], item["error"])
            for item in data["dead_letters"]
        )
