"""The queue API workers poll.

A worker inside a Slurm allocation can open an outbound connection to the login
node and nothing can open one back to it, so every interaction is a request the
worker makes. These are those requests.

The handlers are deliberately thin: :class:`QueueAPI` turns the wire format into
:class:`~blackfish.pipelines.store.TaskStore` calls and back, and the Litestar
handlers below do nothing but route to it. That keeps the transport swappable --
the same API is what :class:`~blackfish.pipelines.client.HttpQueueClient` speaks
-- and keeps the interesting behaviour in one testable place.

Every mutating endpoint is idempotent, because a worker that loses a response
has no way to tell a lost request from a lost reply and must be free to retry.
"""

from __future__ import annotations

from typing import Any

from litestar import Router, get, post
from litestar.di import Provide
from litestar.exceptions import NotFoundException

from blackfish.pipelines.store import TaskStore


class QueueAPI:
    """Wire-format adapter over a :class:`TaskStore`."""

    def __init__(self, store: TaskStore) -> None:
        self.store = store

    def spec(self, run_id: str) -> dict[str, Any]:
        try:
            return self.store.get_pipeline(run_id).to_dict()
        except KeyError:
            raise NotFoundException(detail=f"No such run: {run_id}") from None

    def status(self, run_id: str) -> dict[str, Any]:
        try:
            status = self.store.run_status(run_id)
        except KeyError:
            raise NotFoundException(detail=f"No such run: {run_id}") from None
        return {
            "run_id": status.run_id,
            "pipeline": status.pipeline,
            "state": str(status.state),
            "complete": status.complete,
            "dead_letters": status.dead_letters,
            "jobs": [
                {
                    "job": job.job,
                    "ready": job.ready,
                    "leased": job.leased,
                    "done": job.done,
                    "failed": job.failed,
                    "seen": job.seen,
                    "sealed": job.sealed,
                    "complete": job.complete,
                }
                for job in status.jobs
            ],
        }

    def lease(self, run_id: str, job: str, data: dict[str, Any]) -> dict[str, Any]:
        tasks = self.store.lease(
            run_id,
            job,
            int(data["max_tasks"]),
            int(data["lease_seconds"]),
            str(data["owner"]),
        )
        return {
            "tasks": [
                {
                    "task_id": task.task_id,
                    "payload": task.payload,
                    "attempts": task.attempts,
                }
                for task in tasks
            ]
        }

    def complete(self, run_id: str, job: str, data: dict[str, Any]) -> dict[str, Any]:
        settled = self.store.complete_batch(
            run_id,
            job,
            {key: list(value) for key, value in data["outputs"].items()},
            list(data.get("downstream", [])),
            record_results=bool(data.get("record_results", False)),
        )
        return {"settled": settled}

    def fold(self, run_id: str, job: str, data: dict[str, Any]) -> dict[str, Any]:
        settled = self.store.fold_batch(
            run_id, job, list(data["task_ids"]), str(data["partial"])
        )
        return {"settled": settled}

    def release(self, run_id: str, job: str, data: dict[str, Any]) -> dict[str, Any]:
        self.store.release(run_id, job, list(data["task_ids"]))
        return {"released": len(data["task_ids"])}

    def fail(self, run_id: str, job: str, data: dict[str, Any]) -> dict[str, Any]:
        retried, dead = self.store.fail_batch(
            run_id,
            job,
            list(data["task_ids"]),
            str(data["error"]),
            int(data["max_attempts"]),
        )
        return {"retried": retried, "dead_lettered": dead}

    def finalize(self, run_id: str, job: str, data: dict[str, Any]) -> dict[str, Any]:
        finalized = self.store.finalize_reduce(
            run_id,
            job,
            str(data["task_id"]),
            list(data.get("downstream", [])),
            record_results=bool(data.get("record_results", False)),
        )
        return {"finalized": finalized}


@get("/runs/{run_id:str}/spec")
async def get_run_spec(run_id: str, queue: QueueAPI) -> dict[str, Any]:
    return queue.spec(run_id)


@get("/runs/{run_id:str}/status")
async def get_run_status(run_id: str, queue: QueueAPI) -> dict[str, Any]:
    return queue.status(run_id)


@post("/runs/{run_id:str}/jobs/{job:str}/lease")
async def lease_tasks(
    run_id: str, job: str, data: dict[str, Any], queue: QueueAPI
) -> dict[str, Any]:
    return queue.lease(run_id, job, data)


@post("/runs/{run_id:str}/jobs/{job:str}/complete")
async def complete_tasks(
    run_id: str, job: str, data: dict[str, Any], queue: QueueAPI
) -> dict[str, Any]:
    return queue.complete(run_id, job, data)


@post("/runs/{run_id:str}/jobs/{job:str}/fold")
async def fold_tasks(
    run_id: str, job: str, data: dict[str, Any], queue: QueueAPI
) -> dict[str, Any]:
    return queue.fold(run_id, job, data)


@post("/runs/{run_id:str}/jobs/{job:str}/release")
async def release_tasks(
    run_id: str, job: str, data: dict[str, Any], queue: QueueAPI
) -> dict[str, Any]:
    return queue.release(run_id, job, data)


@post("/runs/{run_id:str}/jobs/{job:str}/fail")
async def fail_tasks(
    run_id: str, job: str, data: dict[str, Any], queue: QueueAPI
) -> dict[str, Any]:
    return queue.fail(run_id, job, data)


@post("/runs/{run_id:str}/jobs/{job:str}/finalize")
async def finalize_reduce(
    run_id: str, job: str, data: dict[str, Any], queue: QueueAPI
) -> dict[str, Any]:
    return queue.finalize(run_id, job, data)


def create_pipeline_router(store: TaskStore, path: str = "/pipelines") -> Router:
    """Build the router workers poll, backed by ``store``.

    Mount this on the Blackfish app once the coordinator owns a store. It is
    kept as a factory rather than a module-level router because the store is
    process state: exactly one process may open it, and that process is the one
    building the app.
    """
    api = QueueAPI(store)

    async def provide_queue() -> QueueAPI:
        return api

    return Router(
        path=path,
        route_handlers=[
            get_run_spec,
            get_run_status,
            lease_tasks,
            complete_tasks,
            fold_tasks,
            release_tasks,
            fail_tasks,
            finalize_reduce,
        ],
        dependencies={"queue": Provide(provide_queue)},
    )


__all__ = ["QueueAPI", "create_pipeline_router"]
