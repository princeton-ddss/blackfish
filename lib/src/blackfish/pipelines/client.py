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
from blackfish.pipelines.store import Task

# Workers keep polling across a coordinator restart or a transient network
# blip rather than dying and losing their loaded model.
DEFAULT_MAX_RETRIES = 5
DEFAULT_BACKOFF_SECONDS = 1.0
DEFAULT_TIMEOUT_SECONDS = 30.0


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
    ) -> tuple[int, int]: ...

    def finalize_reduce(
        self,
        run_id: str,
        job: str,
        task_id: str,
        downstream: Sequence[str],
        record_results: bool = False,
    ) -> bool: ...


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
        last: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self._client.request(method, path, **kwargs)
                if response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"{response.status_code} from {path}",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                return response.json()
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                last = exc
                if attempt == self.max_retries - 1:
                    break
                time.sleep(DEFAULT_BACKOFF_SECONDS * (2**attempt))
        assert last is not None
        raise last

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
    ) -> tuple[int, int]:
        data = self._request(
            "POST",
            self._job_path(run_id, job, "fail"),
            json={
                "task_ids": list(task_ids),
                "error": error,
                "max_attempts": max_attempts,
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
