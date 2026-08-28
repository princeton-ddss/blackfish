# Pipelines (prototype)

!!! warning "Status: prototype"

    `blackfish.pipelines` is a working prototype, not a shipped feature. The
    core — DAG semantics, queues, workers, autoscaling — runs and is covered by
    tests. The Ray-on-Slurm backend is written against Ray's and Slurm's APIs
    but **has not been run on a cluster**; see
    [What is not verified](#what-is-not-verified). Nothing here is wired into
    the Blackfish server, CLI or UI yet.

A **pipeline** is a directed acyclic graph of jobs connected by durable task
queues. Each job runs its expensive setup once per worker and then serves many
tasks, so a model's weights are loaded per *allocation* rather than per item.

That single property is why this is not a thin wrapper over the existing batch
job feature, and why the workflow engines surveyed below do not fit: almost all
of them assume a worker is cheap to start.

```
             ┌──────────── login node ────────────┐
             │  coordinator                       │
  inputs ───►│   • owns the DAG                   │
             │   • owns the queues (SQLite)       │
             │   • decides worker counts          │
             │   • submits/cancels allocations    │
             └───────┬──────────────────▲─────────┘
                     │ sbatch           │ HTTP (workers dial out)
             ┌───────▼──────────────────┴─────────┐
             │  Slurm allocations                 │
             │   worker: setup() once, then       │
             │           lease → call → emit      │
             └────────────────────────────────────┘
```

## The job model

### Cardinality is semantics; batching is performance

Conflating the two is the most common source of confusion, so they are separate
fields on `JobSpec`.

| Cardinality | Meaning | The function returns |
|---|---|---|
| `1:1` | one output per input | a sequence as long as the batch |
| `1:N` | fan-out: zero or more outputs per input | one group of outputs per input |
| `N:1` | reduce: the whole stream folds to one output | a single value of its own type |

`batch_size` is orthogonal. It is how many queued tasks a worker hands to the
function in one call, so a GPU round trip is amortized over more work. A `1:1`
job with `batch_size=8` is handed 8 inputs and must return 8 outputs; it is
still `1:1`. A worker takes fewer when fewer are queued — a half-full batch is
never held back waiting for work.

`1:N` returns a *nested* sequence, one group per input, which is not decoration:
it is what lets a redelivered task replace exactly its own outputs rather than
duplicating the whole batch's.

### Setup runs once per worker

```python
JobSpec(
    name="transcribe",
    fn="my.jobs:transcribe",          # called with each batch
    setup="my.jobs:load_whisper",     # called once, result passed to fn
    batch_size=8,
    min_workers=0, max_workers=4,
    resources={"gpus": 1, "cpus": 8, "mem": 64},
)
```

Jobs are addressed by import path (`module:attribute`) rather than by object
reference, because a worker is a different process on a different node. A
closure defined in a notebook cannot be a job.

## The four open questions, answered

The design discussion left four questions open. Here is what the prototype
settles, and why.

### 1. Queue substrate

**Answer: SQLite in WAL mode, opened by exactly one process — the coordinator —
and reached by compute nodes over HTTP.**

The requirements were durable queues, at-least-once delivery, and transactional
writes across several queues at once. Postgres and Redis provide all three and
cost a service to run, which on a shared cluster is the expensive part: the user
may not be able to open a port, keep a daemon alive, or get a database
provisioned. SQLite provides the same guarantees inside one file, and the
coordinator is already a long-running process that can own it.

The important decision is not SQLite; it is **who opens the file**. The
tempting design — put the database on the shared filesystem and let every worker
open it — is wrong. SQLite's locking depends on POSIX advisory locks that NFS
and GPFS implement partially or not at all, and the failure mode is silent
corruption rather than an error. It is also unnecessary: a compute node can dial
*out* to the login node but nothing can dial *in*, so workers already have to
poll. They poll the coordinator's HTTP API
([`blackfish.pipelines.api`][api]) instead of a database file.

A worker that shares a host with the coordinator (a `LOGIN`-placed job, or a
whole pipeline running on a laptop) talks to the same store directly. Both paths
satisfy one `QueueClient` protocol, so the worker loop does not know which it
has.

### 2. Task payload size

**Answer: content-addressed spill to shared storage above a configurable
threshold.**

A queue is an index, not a data store. Payloads at or below `inline_max_bytes`
(4 KiB by default — comfortably more than a file path, a prompt or a row of
metadata) ride in the queue row; anything larger is written once to the payload
directory and the queue carries a reference.

Spilled payloads are named by the SHA-256 of their contents, which makes a
retried write a no-op instead of a race: a task that recomputes the same output
writes the same path with the same bytes. Writes go through a temp file and
`os.replace`, so a reader never sees a partial file.

Tensors and audio are not meant to travel through the queue at all. Write them
to the shared filesystem and pass the *path*; the store deliberately encodes
JSON only, so this constraint is visible rather than something you discover at
scale.

### 3. Failure semantics

**Answer: leases with a visibility timeout, at-least-once delivery, bounded
retries, dead letters that do not block completion — and derived task IDs, so
the *plumbing* is idempotent even when the user's function is not.**

A worker leases a batch for `lease_seconds`. If it dies — preempted, out of
walltime, OOM-killed — the lease expires and the coordinator returns the tasks
to the queue on its next tick. The attempt count survives reclamation, so a task
that kills its worker every time is eventually dead-lettered instead of
retrying forever.

The one failure a worker genuinely cannot diagnose is a commit whose reply was
lost: it does not know whether its outputs landed. So it retries, and the store
makes that safe. Every task ID is a UUIDv5 derived from the run, the job, the
parent task and the output's index within it. A repeated emit lands on the rows
it landed on the first time; a repeated acknowledgement settles nothing and
reports zero. Only the user's *side effects* need to be idempotent, which is a
much smaller ask than "your function must be idempotent".

Dead-lettered tasks count as settled. A poison input must not hold the DAG open
forever; the run completes and reports the dead letters.

### 4. N:1 fan-in correctness

**This was flagged as the place DAG-on-queue systems get complicated, and it is
the part of the design worth reading closely.** No sentinels, no watermarks, no
run-window tagging.

Make one thing atomic: **acknowledging a task and enqueuing the tasks it
produced happen in the same transaction.** There is then no instant at which an
upstream job looks finished while its outputs are still in flight, and this
recursive rule is exact:

```
complete(job) = every upstream is complete, and no tasks are outstanding
complete(source) = the source is sealed, and no tasks are outstanding
```

`sealed` is an explicit "no more inputs are coming" flag on a source. It is
required, and its absence is not an oversight: an empty queue and a slow
producer are indistinguishable from the outside, so a run whose source is never
sealed never completes — by design.

Everything else follows. A join waits for both branches of a diamond because
each branch is an upstream. A downstream job with an empty queue is *not*
complete while its upstream still holds work. A task returned by lease expiry is
outstanding again, so the upstream un-completes, which is correct.

#### The reduce is a tree

An `N:1` job folds. Workers take two or more values, combine them, and push the
partial result back onto the job's own queue; when one value remains and every
upstream has finished, that value is emitted downstream. So a reduce streams and
scales out instead of waiting for the whole upstream to land.

The price is a constraint on the function: it must be a **commutative,
associative fold over a list of its own output type**. "Collect everything into
one list" satisfies this — it is list concatenation — and is the common case;
with payload spilling, a list of references stays small.

Two hazards, both handled:

- A fold over a *single* value returns it unchanged, so the queue would never
  shrink. `JobSpec` rejects `N:1` with `batch_size < 2`.
- A worker that leases one partial while others are still in flight would spin.
  It puts the task back *without* spending an attempt and backs off.

Finalization checks "upstream complete **and** exactly one task outstanding" in
the same transaction that emits, while the caller holds that task's lease — so a
partial still being folded elsewhere blocks finalization rather than racing it.

## Autoscaling

Scaling is a pure function of queue depth
([`blackfish.pipelines.scaler`][scaler]), testable without a cluster. Two
asymmetries, both from Slurm rather than from queueing theory:

- **Scale up now, scale down slowly.** A new worker costs a trip through the
  Slurm queue. Releasing one that is about to be needed again is far more
  expensive than holding it, so growth is immediate and shrinking waits for
  several consecutive idle ticks.
- **Never scale on backlog alone.** Workers consume tasks `batch_size` at a
  time, so a 100-task backlog at `batch_size=32` needs four workers, not a
  hundred.

## Build vs. buy: what the Ray-on-Slurm deep dive found

The survey ruled out Nextflow and Snakemake (no in-allocation worker reuse:
they cannot express "load the weights once"), Airflow, Prefect and Dagster (they
assume cheap workers, not Slurm allocations), Celery, RQ and Dramatiq (task
queues, not actor systems — stateful workers mean fighting the framework), and
Dask (weaker for GPU actor workloads). Ray was the strongest remaining
candidate, so Ray is what was prototyped.

### What Ray genuinely adds

Placing a **stateful** worker on a specific GPU, restarting it in place, and
resizing the pool in seconds rather than in another trip through the Slurm
queue. That is real, and it is exactly the gap `sbatch` leaves: Slurm can give
you a node, but it has no notion of "the process on that node that already has
Whisper resident".

### What it does not solve

Everything above. Ray has no opinion on DAG cardinality, no durable queue that
survives a preempted allocation, and no autoscaling signal that matches this
workload — Ray Serve's autoscaler reacts to request rate on a Serve deployment,
whereas work here lives in a queue that has to outlive the workers draining it.
The DAG layer, the fan-in rule, the queue substrate and the scaling policy all
had to be built regardless of the execution layer, and they are the bulk of what
this prototype is.

That leads to the division of labour the backend settles on:

| Concern | Owner |
|---|---|
| Capacity (nodes, GPUs, walltime) | Slurm — `sbatch` an allocation that runs `ray start --address=<head>` |
| Worker lifecycle (setup once, place on a GPU, resize) | Ray actors |
| Work, ordering, durability, completion | Blackfish — the task store |

### Concrete gotchas found while building it

These are the things that would have cost days on a cluster, and they are worth
recording whether or not Ray is adopted:

- **A blocking actor method starves its own control plane.** An actor whose
  `run` loop occupies its single execution thread will not answer `stop`. The
  actor is created with `max_concurrency=2` so a stop request is serviced while
  the loop runs; without it the only way to stop a worker is `ray.kill`, which
  drops the batch in flight and forces a model reload on the replacement.
- **Ray reads the whole physical node, not the allocation.** Unless
  `ray start` is passed `--num-cpus`/`--num-gpus` matching what Slurm granted, a
  shared node is oversubscribed and every actor on it slows down. Nothing
  errors.
- **Scaling is two-tier with very different latencies.** Growing the actor pool
  inside existing allocations takes seconds; growing the allocation pool is
  Slurm queue time. The backend asks Slurm for capacity as soon as demand
  appears and lets actors follow as nodes join, rather than waiting for a node
  before admitting demand.
- **Ray's object store spills to `/dev/shm`,** which is small on many compute
  nodes. The node script points `--temp-dir` at node-local scratch.
- **Ray adds a second failure domain.** A dead head node takes down every actor
  in the run. The queue is unaffected — it lives in the coordinator's SQLite,
  not in Ray — so recovery is "reconnect and re-place actors", which is only
  true *because* durability was kept out of Ray.

### Recommendation

Keep the backend pluggable and treat Ray as an optimization rather than a
foundation. The queue-centric design means workers are ordinary polling
processes, so the `SubprocessBackend` path already works, and a Slurm-native
backend (one allocation per worker group, no Ray) is a smaller operational
surface for the common case. Ray earns its complexity when a pipeline needs
fast pool resizing over already-held allocations, or fine-grained GPU placement
of several jobs onto one node — both real, neither universal.

Covalent was the other candidate. It was not prototyped: the two are alternative
*execution layers*, and picking one to evaluate properly was more useful than
half-evaluating both. If Ray-on-Slurm proves awkward in practice, the backend
protocol is three methods (`scale`, `count`, `shutdown`), so a Covalent
assessment is a contained piece of work rather than a rewrite.

## Trying it

```python
import asyncio
from blackfish.pipelines import run_local
from blackfish.pipelines.example import build_pipeline

documents = ["the quick brown fox\njumps over the lazy dog", ...]
status, results = asyncio.run(run_local(build_pipeline(max_workers=3), documents))
```

`blackfish.pipelines.example` is a word-count pipeline —
`read (1:N) → count (1:1) → merge (N:1)` — small enough to read and exercising
all three cardinalities. `run_local` runs workers as threads; the semantics are
identical to a cluster run, only the backend differs.

For a closer rehearsal of cluster behaviour, use `SubprocessBackend`: real
processes, real polling, setup paid per worker, workers killable.

## What is not verified

Stated plainly, because the difference matters:

- **Covered by tests:** DAG validation, cardinality semantics, queue leases and
  expiry, at-least-once delivery, idempotent replay, fan-in completion
  (including a diamond join), the tree reduce and its finalization gate, dead
  letters, autoscaling policy, the worker loop, the HTTP queue API and its
  client, and end-to-end runs on both local backends.
- **Not run on a cluster:** the Ray actor lifecycle, `sbatch`/`scancel` against
  a real scheduler, Apptainer image bring-up on compute nodes, and the HTTP path
  under real network conditions. The sizing arithmetic and the rendered sbatch
  script are unit-tested; the parts that need a scheduler and a GPU are not.
- **Not built:** persistence of runs in the Blackfish database, REST routes on
  the main app, CLI commands, and any UI. `create_pipeline_router` exists and is
  tested standalone but is not mounted, because the store is process state and
  the coordinator's lifecycle in the server is a design decision of its own.

## Next steps

1. Run the Ray backend on a real cluster and settle the two-tier scaling
   latency question with measurements rather than reasoning.
2. Decide whether a Slurm-native backend (no Ray) covers enough cases to be the
   default.
3. Persist runs in the Blackfish database and mount the queue router, so a
   pipeline survives a coordinator restart the way a batch job survives one.
4. CLI and UI, following the existing batch job surfaces.

[api]: https://github.com/princeton-ddss/blackfish/blob/main/lib/src/blackfish/pipelines/api.py
[scaler]: https://github.com/princeton-ddss/blackfish/blob/main/lib/src/blackfish/pipelines/scaler.py
