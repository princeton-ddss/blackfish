"""Ray-on-Slurm backend: Ray actors for worker lifecycle, Slurm for capacity.

This is the backend the design discussion set out to evaluate. The division of
labour it settles on:

- **Slurm owns capacity.** Ray cannot allocate a GPU node; only ``sbatch`` can.
  So the coordinator submits allocations, each of which joins the Ray cluster
  with ``ray start --address=<head>`` and then blocks for its walltime.
- **Ray owns worker lifecycle.** Inside that borrowed capacity, a worker is a
  Ray actor. The actor's ``__init__`` runs the job's ``setup`` -- the model load
  -- and its ``run`` method then serves batches for the life of the actor. This
  is what Ray genuinely adds over bare processes: placing a stateful worker on a
  specific GPU, restarting it in place, and resizing the pool in seconds rather
  than in another trip through the Slurm queue.
- **Blackfish owns the queue.** Ray Serve's autoscaler reacts to request rate on
  a Serve deployment; our work lives in a durable queue that has to survive a
  preempted allocation, so the scaling signal is queue depth
  (:mod:`blackfish.pipelines.scaler`) and the durability is SQLite's.

Two consequences of running Ray this way are worth knowing before you commit:

1. **Scaling is two-tier, and the tiers have very different latencies.**
   Growing the actor pool within existing allocations is fast; growing the
   allocation pool is Slurm queue time. :meth:`RaySlurmBackend.scale` therefore
   asks for allocations as soon as demand appears, and lets actors follow as
   nodes join, rather than waiting for a node before admitting demand.
2. **A blocking actor method starves its own control plane.** An actor whose
   ``run`` loop occupies its single execution thread will not answer ``stop``.
   The actor is created with ``max_concurrency=2`` so that a stop request is
   serviced while the loop is running; without it the only way to stop a worker
   is ``ray.kill``, which drops the batch in flight and forces the model to be
   reloaded on the replacement.

Ray is imported lazily, so importing this module (and the rest of Blackfish)
does not require Ray to be installed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from math import ceil
from typing import Any

from jinja2 import Environment, PackageLoader

from blackfish.pipelines.spec import JobSpec, Pipeline
from blackfish.server import remote
from blackfish.server.logger import logger

# Ray's default GCS port. Workers join at ``<head_host>:<port>``.
DEFAULT_RAY_PORT = 6379

# Resources assumed for a Ray node allocation when the job does not say.
DEFAULT_NODE_RESOURCES: dict[str, Any] = {
    "cpus": 8,
    "mem": 64,
    "gpus": 1,
    "time": "04:00:00",
}


class RayNotAvailable(RuntimeError):
    """Raised when the Ray backend is used without Ray installed."""


def _import_ray() -> Any:
    try:
        import ray
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RayNotAvailable(
            "The Ray backend requires the 'ray' package. Install it in the"
            " coordinator environment and in the container the Slurm nodes run."
        ) from exc
    return ray


@dataclass(frozen=True, slots=True)
class RayClusterConfig:
    """How to reach the Ray cluster and how to grow it.

    Args:
        head_address: ``host:port`` of the running Ray head, which the
            coordinator starts on the login node.
        coordinator_url: Base URL workers use to reach the queue API. Actors
            run on compute nodes and cannot be dialled, so they poll this.
        payload_dir: Payload store directory, on a filesystem every node sees.
        image: Apptainer image (``.sif``) the Slurm nodes run, or ``None`` to
            run on the node's own Python environment.
        node_resources: sbatch resources for each Ray node allocation.
        profile_home: Blackfish home directory on the cluster, where scripts
            are staged.
        account: Slurm account, if the site requires one.
        token: Bearer token for the coordinator API, if it requires auth.
    """

    head_address: str
    coordinator_url: str
    payload_dir: str
    image: str | None = None
    node_resources: dict[str, Any] = field(default_factory=dict)
    profile_home: str = "~/.blackfish"
    account: str | None = None
    token: str | None = None

    def resources(self) -> dict[str, Any]:
        return {**DEFAULT_NODE_RESOURCES, **self.node_resources}


def actors_per_node(job: JobSpec, node_resources: dict[str, Any]) -> int:
    """How many workers of ``job`` fit on one Ray node allocation.

    A job that asks for no GPU is CPU-bound and packs by CPU; a job that asks
    for GPUs packs by GPU, because that is the resource it will actually
    contend on. Either way the answer is at least one: a node too small for the
    job is a configuration error the scheduler will report far more clearly
    than a silent zero here.
    """
    per_worker_gpus = int(job.resources.get("gpus", 0))
    if per_worker_gpus > 0:
        node_gpus = int(node_resources.get("gpus", 0))
        return max(1, node_gpus // per_worker_gpus)
    per_worker_cpus = max(1, int(job.resources.get("cpus", 1)))
    node_cpus = int(node_resources.get("cpus", 1))
    return max(1, node_cpus // per_worker_cpus)


def nodes_required(desired_workers: int, per_node: int) -> int:
    """Number of Ray node allocations needed to host ``desired_workers``."""
    if desired_workers <= 0:
        return 0
    return ceil(desired_workers / max(1, per_node))


def render_node_script(
    config: RayClusterConfig,
    name: str,
    resources: dict[str, Any] | None = None,
) -> str:
    """Render the sbatch script for one Ray node allocation.

    The script joins the existing Ray cluster and blocks; it deliberately does
    not start any work of its own. Everything that runs on the node is placed
    there by the coordinator as an actor, which is what allows a single
    allocation to serve several jobs of the pipeline over its lifetime instead
    of being pinned to the one it was requested for.
    """
    merged = {**config.resources(), **(resources or {})}
    env = Environment(
        loader=PackageLoader("blackfish.pipelines", "templates"),
        keep_trailing_newline=True,
    )
    template = env.get_template("ray_node_slurm.sh")
    return template.render(
        name=name,
        head_address=config.head_address,
        image=config.image,
        payload_dir=config.payload_dir,
        account=config.account or merged.get("account"),
        resources=merged,
    )


class SlurmRayNodePool:
    """Keeps a target number of Slurm allocations joined to the Ray cluster.

    Allocations are fungible: any actor can be placed on any node with room, so
    the pool tracks a single count rather than a per-job assignment.
    """

    def __init__(self, config: RayClusterConfig, run_id: str) -> None:
        self.config = config
        self.run_id = run_id
        self.job_ids: list[str] = []
        self._submitted = 0

    async def ensure(self, nodes: int) -> None:
        """Submit or cancel allocations so the pool holds ``nodes`` of them."""
        while len(self.job_ids) < nodes:
            job_id = await self._submit()
            self.job_ids.append(job_id)
        while len(self.job_ids) > nodes:
            await self._cancel(self.job_ids.pop())

    def script_dir(self) -> str:
        """Where this run's node scripts are staged."""
        return os.path.join(
            os.path.expanduser(self.config.profile_home), "pipelines", self.run_id
        )

    async def _submit(self) -> str:
        name = f"bf-ray-{self.run_id[:8]}"
        script = render_node_script(self.config, name)
        directory = self.script_dir()
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, f"ray-node-{self._submitted}.sh")
        self._submitted += 1
        with open(path, "w") as handle:
            handle.write(script)

        result = await remote.run(["sbatch", "--parsable", "--chdir", directory, path])
        job_id = result.stdout.decode("utf-8").strip().split(";")[0]
        logger.info("Submitted Ray node allocation %s for run %s", job_id, self.run_id)
        return job_id

    async def _cancel(self, job_id: str) -> None:
        logger.info("Cancelling Ray node allocation %s", job_id)
        await remote.run(["scancel", job_id])

    async def cancel_all(self) -> None:
        while self.job_ids:
            await self._cancel(self.job_ids.pop())


def build_actor_class() -> Any:
    """Define the Ray actor that hosts one worker.

    Defined inside a function so that importing this module does not require
    Ray, and decorated at call time so the class is registered with whatever
    Ray runtime is live.
    """
    ray = _import_ray()

    @ray.remote
    class PipelineWorkerActor:
        """A worker pinned to one Ray node, holding its model across batches."""

        def __init__(
            self,
            run_id: str,
            spec: dict[str, Any],
            job_name: str,
            coordinator_url: str,
            payload_dir: str,
            token: str | None = None,
        ) -> None:
            import threading

            from blackfish.pipelines.client import HttpQueueClient
            from blackfish.pipelines.payload import PayloadStore
            from blackfish.pipelines.spec import Pipeline as _Pipeline
            from blackfish.pipelines.worker import Worker

            pipeline = _Pipeline.from_dict(spec)
            self._stop = threading.Event()
            self._worker = Worker(
                run_id=run_id,
                pipeline=pipeline,
                job=pipeline.job(job_name),
                client=HttpQueueClient(coordinator_url, token=token),
                payloads=PayloadStore(payload_dir),
                idle_timeout=None,
            )
            # Pay the setup cost here, while the actor is being created, so a
            # pool resize surfaces model-load time as actor start-up rather
            # than as a mysteriously slow first batch.
            self._worker.start()

        def run(self) -> None:
            self._worker.run(self._stop)

        def stop(self) -> None:
            self._stop.set()

        def stats(self) -> dict[str, int]:
            return {
                "batches": self._worker.batches,
                "tasks": self._worker.tasks_processed,
            }

    return PipelineWorkerActor


class RaySlurmBackend:
    """A :class:`~blackfish.pipelines.backends.WorkerBackend` over Ray on Slurm.

    Args:
        pipeline: The pipeline being run, serialized to each actor.
        config: How to reach and grow the Ray cluster.
    """

    def __init__(self, pipeline: Pipeline, config: RayClusterConfig) -> None:
        self.pipeline = pipeline
        self.config = config
        self._pools: dict[str, SlurmRayNodePool] = {}
        self._actors: dict[tuple[str, str], list[Any]] = {}
        self._actor_cls: Any = None
        self._connected = False

    def connect(self) -> None:
        """Attach to the running Ray head. Idempotent."""
        if self._connected:
            return
        ray = _import_ray()
        if not ray.is_initialized():
            ray.init(address=self.config.head_address, ignore_reinit_error=True)
        self._actor_cls = build_actor_class()
        self._connected = True

    async def scale(self, run_id: str, job: JobSpec, desired: int) -> None:
        self.connect()
        pool = self._pools.setdefault(run_id, SlurmRayNodePool(self.config, run_id))
        per_node = actors_per_node(job, self.config.resources())

        # Ask Slurm for capacity first: allocations take minutes, actors take
        # seconds, so the slow request should be in flight while the fast one
        # is still being decided.
        await pool.ensure(nodes_required(desired, per_node))

        key = (run_id, job.name)
        actors = self._actors.setdefault(key, [])
        if desired > len(actors):
            for _ in range(desired - len(actors)):
                actors.append(self._start_actor(run_id, job))
        elif desired < len(actors):
            for _ in range(len(actors) - desired):
                await self._stop_actor(actors.pop())

    def _start_actor(self, run_id: str, job: JobSpec) -> Any:
        options: dict[str, Any] = {
            "num_cpus": int(job.resources.get("cpus", 1)),
            # Two slots: one for the batch loop, one so `stop` is answered
            # while the loop is running.
            "max_concurrency": 2,
        }
        gpus = int(job.resources.get("gpus", 0))
        if gpus:
            options["num_gpus"] = gpus
        actor = self._actor_cls.options(**options).remote(
            run_id,
            self.pipeline.to_dict(),
            job.name,
            self.config.coordinator_url,
            self.config.payload_dir,
            self.config.token,
        )
        actor.run.remote()
        return actor

    async def _stop_actor(self, actor: Any) -> None:
        ray = _import_ray()
        try:
            actor.stop.remote()
        finally:
            # The worker exits its loop after the batch in flight; killing the
            # actor afterwards reclaims the GPU without waiting on the loop.
            ray.kill(actor, no_restart=True)

    async def count(self, run_id: str, job: str) -> int:
        return len(self._actors.get((run_id, job), []))

    async def shutdown(self, run_id: str) -> None:
        for (rid, job), actors in list(self._actors.items()):
            if rid != run_id:
                continue
            for actor in actors:
                await self._stop_actor(actor)
            self._actors.pop((rid, job), None)
        pool = self._pools.pop(run_id, None)
        if pool is not None:
            await pool.cancel_all()


__all__ = [
    "RayClusterConfig",
    "RayNotAvailable",
    "RaySlurmBackend",
    "SlurmRayNodePool",
    "actors_per_node",
    "nodes_required",
    "render_node_script",
]
