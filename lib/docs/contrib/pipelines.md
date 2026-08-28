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

### Configuration goes in `params`

Because a job is a path rather than a callable, there is nowhere to bind
arguments — so `params` is how a job is configured, and it decides how the
function is called:

| | `fn` receives |
|---|---|
| `setup` set | `fn(batch, setup(**params))` |
| no `setup`, `params` non-empty | `fn(batch, params)` |
| neither | `fn(batch)` |

Params reach `setup` as keywords rather than as a dict on purpose: a misspelled
key is a `TypeError` when the worker starts, not a `KeyError` an hour into the
run. The alternative — module constants or environment variables — does not
survive a second pipeline using the same function with different settings.

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

A store can also be told it may not spill at all (`allow_spill=False`), which
is how a process with no view of the cluster filesystem declares that fact. It
then needs no root directory, and an oversized payload raises `PayloadTooLarge`
at submit time instead of being written somewhere no worker can read. See
[Where the pieces can run](#where-the-pieces-can-run).

### 3. Failure semantics

**Answer: leases with a visibility timeout, at-least-once delivery, bounded
retries, dead letters that do not block completion — and derived task IDs, so
the *plumbing* is idempotent even when the user's function is not.**

A worker leases a batch for `lease_seconds`. If it dies — preempted, out of
walltime, OOM-killed — the lease expires and the coordinator returns the tasks
to the queue on its next tick. The attempt count survives reclamation, so a task
that kills its worker every time is eventually dead-lettered instead of
retrying forever.

A failed batch is held for `retry_backoff * 2 ** (attempts - 1)` seconds, capped
at five minutes, before it can be leased again. The default is non-zero on
purpose: retrying instantly spends a task's whole attempt budget in
milliseconds, which gives a transient condition no chance to clear and hammers
whatever just failed. Tasks serving a backoff still count as outstanding — a
job holding one is emphatically not complete — but are excluded from the
backlog the autoscaler reacts to, so a queue of nothing but waiting retries
does not hold workers that have nothing to do.

**The batch is the unit of retry.** If the fifth item in a batch of eight
fails, all eight are retried. For pure work that is wasted time; against a
metered API it costs quota, and against a non-idempotent write it is a bug. So
`batch_size` is a throughput knob for cheap-to-repeat work and a *blast radius*
for everything else.

**An unreachable coordinator is not a failure of the work.** Queue calls raise
`QueueUnavailable`, distinct from every other error, and a worker that sees one
*waits* — holding the model it has already paid to load — with escalating
backoff, until either the coordinator returns or `max_outage` elapses. Tasks it
had leased are redelivered by lease expiry, so waiting costs nothing but time.
Treating an outage as fatal would mean a login-node reboot costs a cluster's
worth of warm workers, which is a far worse trade than idling through it. A 4xx
is handled the opposite way: that is this worker asking for something wrong, so
it is raised immediately rather than retried.

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

## Where the pieces can run

The coordinator does two jobs, and they have different availability
requirements — which is the whole basis for deciding what can go where.

| | Must be | Tolerates |
|---|---|---|
| **Queue service** — serving leases and acknowledgements | always up, reachable from compute nodes | nothing; workers block on it |
| **Control plane** — owning the DAG, scaling, submitting allocations | live-ish | being away for minutes |

`QueueAPI` is the first and `Coordinator` is the second, and they are separate
classes that happen to share a process. The `QueueClient` protocol is what a
worker needs; `StoreClient` extends it with what a coordinator needs
(`create_run`, `submit`, `seal`, `reclaim_expired`, `run_status`,
`set_run_state`, `results`, `dead_letters`). `TaskStore` satisfies both
directly and `HttpStoreClient` satisfies `StoreClient` over the wire, so **the
control plane's location is a configuration rather than a rewrite**. There is a
test that drives a complete run with the coordinator reaching the queue only
over HTTP.

### Running the control plane off the cluster

This makes a workstation-hosted control plane workable — which is the only way
to get a database that a cluster will not let you run as a daemon. Three things
have to be true:

1. **Workers must reach the queue service.** They only dial out, and most sites
   firewall compute nodes off the public internet, so the queue service belongs
   on the login node regardless. Reaching it from a workstation is an SSH
   tunnel; reaching a *workstation* from compute nodes generally is not
   possible, and a reverse tunnel needs `GatewayPorts yes` on the login node,
   which many sites will not enable.
2. **The control plane must not need the shared filesystem.** It encodes
   submitted inputs and decodes results, so it touches the payload store. Use
   `PayloadStore(allow_spill=False)`: paths and metadata stay inline and travel
   in the queue row, and anything larger is refused loudly.
3. **Workers must survive the control plane being away** — which they now do,
   per the failure semantics above.

The trade to weigh: durable state for a multi-day run then lives on a machine
that goes in a bag, rather than on cluster storage that is backed up. Splitting
along the queue/control line keeps the *queue* on the cluster and moves only the
decisions, which is the configuration worth reaching for.

### On swapping the database

Worth separating from the location question, because the two are less coupled
than they look. `TaskStore` is behind a narrow interface, and porting it to
Postgres is mostly dialect — `INSERT OR IGNORE` becomes `ON CONFLICT DO
NOTHING`, `rowid` becomes a sequence column. The prize is `SELECT … FOR UPDATE
SKIP LOCKED`, which would make leases genuinely concurrent instead of
serialized behind this design's single writer. That benefit is available
wherever the store runs; what moving the control plane off the cluster buys is
not capability but *permission* to run a daemon at all.

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

## Worked examples

Six, in `blackfish.pipelines.examples`. Each runs anywhere — no GPU, no model
download, no scheduler — because the expensive part is stubbed and everything
around it is what real code does. They are documentation that executes: each is
covered by tests, so a change to the core that breaks an idiom breaks a build.

| Example | Shape | What it is for |
|---|---|---|
| `word_count` | `1:N → 1:1 → N:1` | the smallest pipeline using all three cardinalities |
| `embed` | `plan → embed → manifest` | running a model over one very large file |
| `resumable` | `1:1`, standing run | a growing directory, surviving a restart |
| `compare` | diamond | two models of different speeds, joined per document |
| `transcribe` | three-stage chain | stages exchanging artifacts on disk |
| `summarize` | `LOGIN → COMPUTE` | cheap IO feeding expensive GPU work |

Each earns its place by teaching something the others do not.

### `word_count` — the three cardinalities

`read (1:N) → count (1:1) → merge (N:1)`, small enough to read in one sitting.

```python
from blackfish.pipelines import run_local
from blackfish.pipelines.examples.word_count import build_pipeline

status, results = await run_local(build_pipeline(max_workers=3), documents)
```

### `embed` — a model over one large file

**A task is a chunk, not a line.** The queue is an index, not an array: every
task carries a UUID, a state, an attempt counter and timestamps, so one task per
line spends a few hundred bytes of bookkeeping on a sentence — and the GPU wants
a batch anyway. The chunk *is* the batch, which is why `embed` runs with
`batch_size=1`. (Rule of thumb, not measured: under ~100k items, one task each
is fine and simpler.)

**Chunks are byte ranges found in one pass.** `plan` scans the file once,
recording offsets; workers `seek()` straight to their range. A descriptor saying
"skip 4096 lines, take 512" makes every worker re-read from the top, which is
quadratic.

**Output goes to disk; the queue gets a path.** A few hundred thousand
individual vector payloads would be a few hundred thousand tiny files, which is
an abusive access pattern on a parallel filesystem.

**Side effects need their own idempotency.** Shards are named by a hash of the
chunk descriptor, so a redelivered chunk rewrites the same path with the same
bytes. The queue makes its own bookkeeping idempotent; what a job writes is the
job's to protect — `payload.write_atomic` is exported for exactly this.

### `resumable` — a standing run over a growing directory

Two kinds of continuity, which are different problems with different answers.

**Surviving a restart** is free, and deliberately so. Nothing about a run lives
in the coordinator's memory: reopen the store, tick again. Finished work is not
redone; work that was in flight comes back through lease expiry. There is no
checkpoint to write and no resume protocol to get right.

**Picking up new inputs** is what `keys` is for. Passing each file's path as its
key makes submission idempotent within the run, so re-scanning the directory
enqueues only what is new and the pipeline needs no manifest of its own.

The trade-off: this is idempotent *within a run*. Task IDs are derived from the
run, so the same key in a new run is new work — which is usually what someone
means by re-running, but it makes "process this directory forever" one
long-lived unsealed run rather than a series of runs.

### `compare` — a diamond with asymmetric branches

**Fan-out is a copy, not a split.** Both branches see every document.

**Branches scale independently.** Separate queues, separate worker counts, so
the slow branch accumulates backlog and gets more workers while the fast one
drains and releases its own. Nothing coordinates them; it falls out of scaling
each job on its own queue depth.

**There is no built-in keyed join.** A reduce gives you "everything in one
place"; matching a document's two scores is something the fold does, keyed on an
ID both branches carry. If you want a relational join, you build it in the fold
— and the values must be keyed *before* they arrive, which is why both branches
emit `{doc_id: {...}}` rather than a bare score.

### `transcribe` — a chain that exchanges artifacts

**Establish an item key at ingestion, then carry it.** Every stage writes under
`<output_dir>/<key>/`, so an item's outputs are co-located and predictable and a
retried stage overwrites its own artifact.

**The payload is a record that grows.** A task only ever sees what its immediate
upstream emitted, so anything a later stage needs must be carried forward. The
corollary matters on a long chain: a stage that drops a field silently starves
every stage after it, and nothing in the type system will say so.

### `summarize` — login-node IO feeding GPU work

Two jobs with opposite economics, which is why they are two jobs: many cheap
`LOGIN` workers waiting on a network service, feeding one expensive `COMPUTE`
worker per GPU. A single job doing both would have to size for the worse of the
two, leaving the GPU idle on HTTP.

It is also the example that motivated `retry_backoff`, and the one that shows
the batch-as-blast-radius rule above with a measurement: with `fail_once`
enabled, a batch of two costs three fetches for two documents.

### Running them for real

`run_local` runs workers as threads; the semantics are identical to a cluster
run, only the backend differs. For a closer rehearsal, use `SubprocessBackend`:
real processes, real polling, setup paid per worker, workers killable.

## What is not verified

Stated plainly, because the difference matters:

- **Covered by tests:** DAG validation, cardinality semantics, job params and
  the call convention, queue leases and expiry, at-least-once delivery,
  idempotent replay, retry backoff and its effect on the backlog, fan-in
  completion (including a diamond join), the tree reduce and its finalization
  gate, dead letters, autoscaling policy, the worker loop, the HTTP queue API
  and its client, worker tolerance of an unreachable coordinator, a complete
  run driven by a coordinator that reaches the queue only over HTTP,
  coordinator restart over a durable store, and end-to-end runs of all six
  worked examples.
- **Not run on a cluster:** the Ray actor lifecycle, `sbatch`/`scancel` against
  a real scheduler, Apptainer image bring-up on compute nodes, and the HTTP path
  under real network conditions. The sizing arithmetic and the rendered sbatch
  script are unit-tested; the parts that need a scheduler and a GPU are not.
- **Not built:** persistence of runs in the Blackfish database, CLI commands,
  and any UI. `create_pipeline_router` now serves both the worker-facing queue
  API and the control-plane API, and is tested standalone, but it is not
  mounted on the main app: the store is process state, the coordinator's
  lifecycle in the server is a design decision of its own, and the router has
  no auth yet.

### Known limitations

- **No streaming emit.** A `1:N` job returns all of its outputs from one call,
  and they are inserted in a single transaction. Chunked fan-out keeps that
  bounded — which is what the `embed` example's `plan` job does — but a fan-out
  producing millions of outputs from one call would be one enormous
  transaction with the whole list in memory. Another chunking level is the
  workaround; streaming would be the fix.
- **No payload garbage collection.** Spilled payloads accumulate for the life
  of the payload directory; a completed run's intermediates are never
  reclaimed. Content addressing makes refcounting awkward, so this needs a
  design rather than a patch.
- **No directory-scanning source.** `BatchJob` takes an `input_dir` and walks
  it; a pipeline takes a list of values. A built-in `1:N` source that fans a
  directory out into paths is expressible today and simply is not written.
- **The shared-filesystem assumption is only half checked.** A control plane
  can now declare it has no shared filesystem (`allow_spill=False`) and get an
  error at submit time. But a *worker* whose `payload_dir` or `shard_dir` is
  not actually visible still finds out mid-run. A coordinator pre-flight
  belongs here.
- **The queue API has no authentication.** `create_pipeline_router` installs no
  guards, and `HttpQueueClient` will send a bearer token that nothing checks.
  On a shared login node that means any other user who can reach the port can
  lease, acknowledge or inject work. This must be closed before the router is
  mounted anywhere real.

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
