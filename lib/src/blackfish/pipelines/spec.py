"""Pipeline specification: jobs, cardinalities, and the DAG that connects them.

A :class:`Pipeline` is a directed acyclic graph of :class:`JobSpec` nodes. Each
node describes *what* to run (an importable function), *how many* outputs it
produces per input (:class:`Cardinality`), *how many* inputs it wants per call
(``batch_size``), and *where* it runs (:class:`Placement`).

Cardinality and batching are orthogonal, and conflating them is the most common
source of confusion:

- **Cardinality** is semantic. It says how the input and output *streams*
  relate: one output per input (``1:1``), many outputs per input (``1:N``), or
  one output for the whole stream (``N:1``).
- **Batching** is a performance knob. It says how many queued tasks a worker
  hands to the function in a single call so that a GPU round trip is amortized
  over more work. A ``1:1`` job with ``batch_size=8`` is handed 8 inputs and
  must return 8 outputs; it is still ``1:1``.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterator

# The default visibility timeout for a leased task, in seconds. A task whose
# lease expires is returned to the queue and handed to another worker, so this
# must exceed the wall-clock time of a single batch call.
DEFAULT_LEASE_SECONDS = 300

# The default number of times a task is attempted before it is dead-lettered.
DEFAULT_MAX_ATTEMPTS = 3


class Cardinality(StrEnum):
    """How a job's output stream relates to its input stream."""

    ONE_TO_ONE = "1:1"
    """Each input task produces exactly one output task.

    The function is called as ``fn(batch)`` and must return a sequence of the
    same length as ``batch``, aligned element-wise.
    """

    ONE_TO_MANY = "1:N"
    """Each input task produces zero or more output tasks (fan-out).

    The function is called as ``fn(batch)`` and must return a sequence of
    sequences: one (possibly empty) group of outputs per input, in order. The
    nesting is not decoration -- it is what lets a retried task replace exactly
    its own outputs instead of duplicating the batch's.
    """

    MANY_TO_ONE = "N:1"
    """The whole input stream is folded into a single output task (reduce).

    The function is called as ``fn(batch)`` with two or more values and must
    return a single value *of the same type*, which is pushed back onto the
    job's own queue as a partial result. Workers keep folding partials until
    one value remains and every upstream job has finished, at which point that
    value is emitted downstream.

    This makes the reduce a tree, so it scales out and streams instead of
    waiting for the whole upstream to land. The price is a constraint on the
    function: it must be a commutative, associative fold over a list of its own
    output type. "Collect everything into one list" satisfies this (it is list
    concatenation) and is the common case.
    """


class Placement(StrEnum):
    """Where a job's workers run."""

    LOGIN = "login"
    """In a process on the coordinator's own node.

    For cheap, IO-bound work -- calling a hosted API, moving files, writing a
    manifest -- where a Slurm allocation would cost more in queue time than the
    work costs to run.
    """

    COMPUTE = "compute"
    """In a Slurm allocation, one worker per allocated task slot.

    For anything that needs a GPU or a serious CPU/memory footprint.
    """


@dataclass(frozen=True, slots=True)
class JobSpec:
    """One node of a pipeline.

    Args:
        name: Unique within the pipeline. Used as the queue name and as the
            job's identity in every log line and API path.
        fn: Import path of the work function, ``"package.module:attribute"``.
            Workers run in separate processes (and on separate nodes), so a
            job is addressed by import path rather than by object reference.
        setup: Import path of an optional zero-argument callable run **once per
            worker process**, before the first batch. Its return value is
            passed to ``fn`` as a second positional argument. This is where a
            model gets loaded: the cost is paid once per allocation and then
            amortized over every task the worker handles.
        cardinality: How outputs relate to inputs. See :class:`Cardinality`.
        batch_size: Maximum number of tasks handed to ``fn`` in one call. A
            worker takes fewer when fewer are queued, so this is a ceiling, not
            a barrier -- a half-full batch is never held back waiting for work.
        min_workers: Lower bound the autoscaler will not scale below. ``0``
            means the job releases its allocation entirely when idle.
        max_workers: Upper bound the autoscaler will not scale above.
        placement: Login node or Slurm allocation. See :class:`Placement`.
        resources: Slurm resources for a ``COMPUTE`` job (``cpus``, ``mem``,
            ``gpus``, ``time``, ``partition``, ...). Ignored for ``LOGIN``.
        max_attempts: Attempts before a task is dead-lettered.
        lease_seconds: Visibility timeout for a leased batch. Must exceed the
            wall-clock duration of a single ``fn`` call, or a slow worker's
            tasks will be handed to a second worker while it is still running
            them.
    """

    name: str
    fn: str
    setup: str | None = None
    cardinality: Cardinality = Cardinality.ONE_TO_ONE
    batch_size: int = 1
    min_workers: int = 0
    max_workers: int = 1
    placement: Placement = Placement.COMPUTE
    resources: dict[str, Any] = field(default_factory=dict)
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    lease_seconds: int = DEFAULT_LEASE_SECONDS

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Job name must be non-empty")
        if ":" not in self.fn:
            raise ValueError(
                f"Job '{self.name}': fn must be an import path of the form"
                f" 'module:attribute', got {self.fn!r}"
            )
        if self.setup is not None and ":" not in self.setup:
            raise ValueError(
                f"Job '{self.name}': setup must be an import path of the form"
                f" 'module:attribute', got {self.setup!r}"
            )
        if self.batch_size < 1:
            raise ValueError(f"Job '{self.name}': batch_size must be >= 1")
        if self.cardinality is Cardinality.MANY_TO_ONE and self.batch_size < 2:
            # Folding a one-element batch returns one value, which goes back on
            # the queue unchanged: the reduce would never shrink its own input.
            raise ValueError(
                f"Job '{self.name}': an N:1 job needs batch_size >= 2, because a"
                " fold over a single value makes no progress"
            )
        if self.min_workers < 0:
            raise ValueError(f"Job '{self.name}': min_workers must be >= 0")
        if self.max_workers < 1:
            raise ValueError(f"Job '{self.name}': max_workers must be >= 1")
        if self.min_workers > self.max_workers:
            raise ValueError(
                f"Job '{self.name}': min_workers ({self.min_workers}) exceeds"
                f" max_workers ({self.max_workers})"
            )
        if self.max_attempts < 1:
            raise ValueError(f"Job '{self.name}': max_attempts must be >= 1")
        if self.lease_seconds < 1:
            raise ValueError(f"Job '{self.name}': lease_seconds must be >= 1")


@dataclass(frozen=True, slots=True)
class Pipeline:
    """A directed acyclic graph of jobs.

    Args:
        name: Human-readable pipeline name.
        jobs: The nodes.
        edges: ``(upstream, downstream)`` job-name pairs. Every output of the
            upstream job is delivered to *each* of its downstream jobs.
    """

    name: str
    jobs: tuple[JobSpec, ...]
    edges: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.jobs:
            raise ValueError(f"Pipeline '{self.name}' has no jobs")

        names = [job.name for job in self.jobs]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise ValueError(
                f"Pipeline '{self.name}' has duplicate job names:"
                f" {', '.join(duplicates)}"
            )

        known = set(names)
        for upstream, downstream in self.edges:
            for endpoint in (upstream, downstream):
                if endpoint not in known:
                    raise ValueError(
                        f"Pipeline '{self.name}': edge ({upstream}, {downstream})"
                        f" references unknown job '{endpoint}'"
                    )
            if upstream == downstream:
                raise ValueError(
                    f"Pipeline '{self.name}': job '{upstream}' cannot depend on itself"
                )

        if len(set(self.edges)) != len(self.edges):
            raise ValueError(f"Pipeline '{self.name}' has duplicate edges")

        # Kahn's algorithm: if any node is left unvisited, it sits on a cycle.
        indegree = {name: 0 for name in known}
        for _, downstream in self.edges:
            indegree[downstream] += 1
        queue = deque(sorted(n for n, d in indegree.items() if d == 0))
        visited = 0
        while queue:
            node = queue.popleft()
            visited += 1
            for child in sorted(self.downstream(node)):
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)
        if visited != len(known):
            unresolved = sorted(n for n, d in indegree.items() if d > 0)
            raise ValueError(
                f"Pipeline '{self.name}' is cyclic; jobs on the cycle:"
                f" {', '.join(unresolved)}"
            )

    def job(self, name: str) -> JobSpec:
        """Return the job named ``name``.

        Raises:
            KeyError: If no such job exists.
        """
        for spec in self.jobs:
            if spec.name == name:
                return spec
        raise KeyError(f"Pipeline '{self.name}' has no job named '{name}'")

    def upstream(self, name: str) -> tuple[str, ...]:
        """Names of the jobs feeding ``name``, in declaration order."""
        return tuple(u for u, d in self.edges if d == name)

    def downstream(self, name: str) -> tuple[str, ...]:
        """Names of the jobs fed by ``name``, in declaration order."""
        return tuple(d for u, d in self.edges if u == name)

    @property
    def sources(self) -> tuple[JobSpec, ...]:
        """Jobs with no upstream. These are the ones a run submits inputs to."""
        return tuple(job for job in self.jobs if not self.upstream(job.name))

    @property
    def sinks(self) -> tuple[JobSpec, ...]:
        """Jobs with no downstream. Their outputs are recorded as run results."""
        return tuple(job for job in self.jobs if not self.downstream(job.name))

    def toposorted(self) -> tuple[JobSpec, ...]:
        """Jobs in a deterministic topological order (upstream first)."""
        indegree = {job.name: 0 for job in self.jobs}
        for _, downstream in self.edges:
            indegree[downstream] += 1
        queue = deque(sorted(n for n, d in indegree.items() if d == 0))
        order: list[JobSpec] = []
        while queue:
            node = queue.popleft()
            order.append(self.job(node))
            for child in sorted(self.downstream(node)):
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)
        return tuple(order)

    def __iter__(self) -> Iterator[JobSpec]:
        return iter(self.jobs)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain data, for storage alongside a run."""
        return {
            "name": self.name,
            "jobs": [
                {
                    "name": job.name,
                    "fn": job.fn,
                    "setup": job.setup,
                    "cardinality": str(job.cardinality),
                    "batch_size": job.batch_size,
                    "min_workers": job.min_workers,
                    "max_workers": job.max_workers,
                    "placement": str(job.placement),
                    "resources": job.resources,
                    "max_attempts": job.max_attempts,
                    "lease_seconds": job.lease_seconds,
                }
                for job in self.jobs
            ],
            "edges": [list(edge) for edge in self.edges],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Pipeline":
        """Rebuild a pipeline from :meth:`to_dict` output."""
        jobs = tuple(
            JobSpec(
                name=job["name"],
                fn=job["fn"],
                setup=job.get("setup"),
                cardinality=Cardinality(job.get("cardinality", "1:1")),
                batch_size=job.get("batch_size", 1),
                min_workers=job.get("min_workers", 0),
                max_workers=job.get("max_workers", 1),
                placement=Placement(job.get("placement", "compute")),
                resources=job.get("resources") or {},
                max_attempts=job.get("max_attempts", DEFAULT_MAX_ATTEMPTS),
                lease_seconds=job.get("lease_seconds", DEFAULT_LEASE_SECONDS),
            )
            for job in data["jobs"]
        )
        edges = tuple((edge[0], edge[1]) for edge in data.get("edges", []))
        return cls(name=data["name"], jobs=jobs, edges=edges)
