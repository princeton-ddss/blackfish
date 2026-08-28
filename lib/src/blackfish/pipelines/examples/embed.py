"""A worked example: embedding every line of one large file.

    plan (1:N)      corpus.txt        ->  chunk descriptors
    embed (1:1)     chunk descriptor  ->  a shard of vectors on disk
    manifest (N:1)  shard records     ->  one manifest

This is the shape most "run a model over a big pile of data" jobs want, and it
differs from the naive one in three ways that are each worth understanding.

**A task is a chunk, not a line.** The queue is an index, not an array. Every
task carries a UUID, a state, an attempt counter and timestamps, so making a
task per line spends a few hundred bytes of bookkeeping on a sentence -- and
the GPU wants a batch anyway, so you would be splitting the data apart only to
have workers glue it back together. The chunk *is* the batch: ``embed`` runs
with ``batch_size=1`` because one task already holds a batch's worth of lines.

**Chunks are byte ranges, found in one pass.** ``plan`` scans the file once,
sequentially, recording offsets; each ``embed`` worker then seeks straight to
its range. The obvious alternative -- a descriptor saying "skip 4096 lines,
take 512" -- makes every worker re-read the file from the top, which is
quadratic and will quietly ruin a large run.

**Vectors go to disk; the queue gets a path.** A few hundred thousand
individual vector payloads would be a few hundred thousand tiny files, which is
an abusive access pattern on a parallel filesystem. Each chunk writes one shard
and emits a reference to it.

The encoder here is a deterministic stand-in so the example runs anywhere,
without a GPU or a model download. Everything around it -- the chunking, the
shard writes, the manifest fold -- is what real code does; replacing
:func:`load_encoder` with one that loads a real model is the whole diff.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from blackfish.pipelines.payload import write_atomic

# Lines per chunk. A chunk should be about one GPU batch: large enough to
# amortize the model call, small enough that losing one to a preempted
# allocation is cheap to redo.
DEFAULT_CHUNK_LINES = 512


# ---------------------------------------------------------------------------
# plan (1:N)
# ---------------------------------------------------------------------------


def plan_chunks(paths: list[str], config: dict[str, Any]) -> list[list[dict[str, Any]]]:
    """Fan each file out into chunk descriptors, one group per input file.

    Cheap and IO-bound, so this job belongs on the login node: a Slurm
    allocation would spend longer in the queue than the scan takes.

    Args:
        paths: Files to plan. One group of chunks is returned per file, in
            order, because a ``1:N`` job's outputs are attributed to the input
            that produced them.
        config: The job's ``params``. Reads ``chunk_lines``.
    """
    chunk_lines = int(config.get("chunk_lines", DEFAULT_CHUNK_LINES))
    if chunk_lines < 1:
        raise ValueError("chunk_lines must be >= 1")

    groups: list[list[dict[str, Any]]] = []
    for path in paths:
        chunks: list[dict[str, Any]] = []
        start = offset = count = index = 0
        # Binary mode: offsets have to be byte offsets for seek() to be exact,
        # and text mode's decoding makes them meaningless.
        with open(path, "rb") as handle:
            for line in handle:
                offset += len(line)
                count += 1
                if count == chunk_lines:
                    chunks.append(_descriptor(path, start, offset, index, count))
                    start, count, index = offset, 0, index + 1
            if count:
                chunks.append(_descriptor(path, start, offset, index, count))
        groups.append(chunks)
    return groups


def _descriptor(
    path: str, start: int, end: int, index: int, lines: int
) -> dict[str, Any]:
    return {"path": path, "start": start, "end": end, "index": index, "lines": lines}


# ---------------------------------------------------------------------------
# embed (1:1)
# ---------------------------------------------------------------------------


def load_encoder(
    shard_dir: str, model: str = "sha256-stub", dim: int = 8
) -> dict[str, Any]:
    """Build the worker's context, once per process.

    In real code this is where the weights land on the GPU:

        from sentence_transformers import SentenceTransformer
        return {"model": SentenceTransformer(model, device="cuda"), ...}

    Called as ``setup(**params)``, so a misspelled key is a ``TypeError`` when
    the worker starts rather than a ``KeyError`` an hour into the run.
    """
    Path(shard_dir).mkdir(parents=True, exist_ok=True)
    return {"shard_dir": shard_dir, "model": model, "dim": dim}


def embed_chunk(
    chunks: list[dict[str, Any]], encoder: dict[str, Any]
) -> list[dict[str, Any]]:
    """Embed each chunk into its own shard, returning one record per chunk.

    The return value is shaped for the reduce downstream, not for readability:
    see :func:`merge_manifests`.
    """
    records = []
    for chunk in chunks:
        lines = read_chunk(chunk)
        vectors = [encode(line, encoder["dim"]) for line in lines]
        shard = shard_path(encoder["shard_dir"], chunk)
        write_atomic(
            shard,
            json.dumps(
                {
                    "source": chunk["path"],
                    "index": chunk["index"],
                    "model": encoder["model"],
                    "vectors": vectors,
                }
            ).encode("utf-8"),
        )
        records.append(
            {
                "shards": [
                    {
                        "path": str(shard),
                        # ``index`` restarts at zero for each input file, so a
                        # run over several files needs both to order shards.
                        "source": chunk["path"],
                        "index": chunk["index"],
                        "rows": len(lines),
                    }
                ],
                "rows": len(lines),
            }
        )
    return records


def read_chunk(chunk: dict[str, Any]) -> list[str]:
    """Read exactly the lines a descriptor covers."""
    with open(chunk["path"], "rb") as handle:
        handle.seek(chunk["start"])
        raw = handle.read(chunk["end"] - chunk["start"])
    return raw.decode("utf-8").splitlines()


def shard_path(shard_dir: str, chunk: dict[str, Any]) -> Path:
    """Name a shard after the chunk it holds.

    Deterministic naming is what makes the write safe under at-least-once
    delivery: a redelivered chunk rewrites the same path with the same bytes
    instead of leaving a second, divergent shard behind. The queue makes its
    own bookkeeping idempotent; a job's side effects are its own to protect,
    and this is how.
    """
    digest = hashlib.sha256(
        json.dumps(chunk, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    return Path(shard_dir) / f"shard-{digest}.json"


def encode(text: str, dim: int) -> list[float]:
    """A stand-in embedding: deterministic, and stable across processes.

    Python's built-in ``hash()`` is salted per interpreter, so two workers would
    produce different vectors for the same line and nobody would notice until
    the results were compared. Anything a pipeline reproduces across workers has
    to come from a stable digest.
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [digest[i % len(digest)] / 255.0 for i in range(dim)]


# ---------------------------------------------------------------------------
# manifest (N:1)
# ---------------------------------------------------------------------------


def merge_manifests(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Fold shard records into one manifest.

    Two constraints of the tree reduce show up here, and both shape the types
    upstream:

    1. **The fold's input and output type must match.** A reduce queue holds a
       mix of upstream outputs and its own partial results, so the function has
       to accept either. That is why :func:`embed_chunk` emits
       ``{"shards": [one], "rows": n}`` rather than a bare shard record -- it
       emits a manifest of one shard, so folding manifests is closed.
    2. **A commutative fold cannot preserve order.** Partials are combined in
       whatever grouping the workers happen to lease, so each shard records
       where it came from; sort by ``(source, index)`` when reading the results
       back. ``index`` alone is not enough once a run covers several files.
    """
    shards: list[dict[str, Any]] = []
    rows = 0
    for record in records:
        shards.extend(record["shards"])
        rows += record["rows"]
    return {"shards": shards, "rows": rows}


# ---------------------------------------------------------------------------
# The pipeline
# ---------------------------------------------------------------------------


def build_pipeline(
    shard_dir: str,
    chunk_lines: int = DEFAULT_CHUNK_LINES,
    dim: int = 8,
    max_workers: int = 4,
) -> Any:
    """Assemble the embedding pipeline.

    Args:
        shard_dir: Where shards are written. Must be visible to every worker.
        chunk_lines: Lines per chunk, i.e. the GPU batch size.
        dim: Embedding dimension.
        max_workers: Ceiling on concurrent ``embed`` workers.
    """
    from blackfish.pipelines.spec import Cardinality, JobSpec, Pipeline, Placement

    return Pipeline(
        name="embed-corpus",
        jobs=(
            JobSpec(
                name="plan",
                fn="blackfish.pipelines.examples.embed:plan_chunks",
                params={"chunk_lines": chunk_lines},
                cardinality=Cardinality.ONE_TO_MANY,
                placement=Placement.LOGIN,
                max_workers=1,
            ),
            JobSpec(
                name="embed",
                fn="blackfish.pipelines.examples.embed:embed_chunk",
                setup="blackfish.pipelines.examples.embed:load_encoder",
                params={"shard_dir": shard_dir, "dim": dim},
                # One task already holds a batch of lines, so a worker takes
                # one task per call. Raising this batches *chunks*, which only
                # helps if chunks are smaller than the GPU can saturate.
                batch_size=1,
                min_workers=0,
                max_workers=max_workers,
                resources={"gpus": 1, "cpus": 8, "mem": 64},
            ),
            JobSpec(
                name="manifest",
                fn="blackfish.pipelines.examples.embed:merge_manifests",
                cardinality=Cardinality.MANY_TO_ONE,
                batch_size=32,
                placement=Placement.LOGIN,
            ),
        ),
        edges=(("plan", "embed"), ("embed", "manifest")),
    )
