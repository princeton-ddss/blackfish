"""A worked example: cheap IO on the login node feeding expensive GPU work.

    fetch (1:1, LOGIN)  ->  summarize (1:1, COMPUTE)

Two jobs with opposite economics, which is exactly why they are two jobs:

**``fetch`` is IO-bound and cheap.** It waits on a network service, so it wants
many concurrent workers and no GPU, and a Slurm allocation would spend longer
in the queue than the work takes. ``Placement.LOGIN`` runs it in a process on
the coordinator's node.

**``summarize`` is GPU-bound and expensive.** One worker per GPU, a batch large
enough to be worth a forward pass, and an allocation that is released when the
queue drains.

Splitting them means the GPU is never idle waiting on HTTP, and the fetchers
are never holding a GPU they are not using. A single job doing both would have
to size for the worse of the two.

Two things this example is really about:

**A rate-limited service needs ``retry_backoff``.** Without it a failed batch
is re-leased immediately by the same worker, which spends the task's entire
attempt budget in milliseconds and hammers the service that just asked it to
slow down. The default is non-zero for this reason; a metered API usually wants
more.

**The batch is the unit of retry.** If the fifth document in a batch of eight
fails, all eight are retried -- the first four are fetched again. For an
idempotent read that is merely wasteful; against a metered API it costs quota,
and against a non-idempotent write it is a bug. So a job whose work is
expensive to repeat should use a *small* batch, and the batch size stops being
a pure throughput knob and starts being a blast radius. ``fetch`` uses
``batch_size=2`` for exactly this reason.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any


class RateLimited(RuntimeError):
    """What a service raises when it wants you to slow down."""


def open_session(
    corpus_dir: str,
    state_dir: str,
    audit_log: str,
    fail_once: bool = False,
) -> dict[str, Any]:
    """Worker setup: open the client once, not once per request.

    In real code this is a connection pool or an authenticated session --
    cheap next to a model, but still not something to rebuild per document.

    ``fail_once`` makes the stubbed service reject the first request for each
    document, so the retry path is exercised deterministically rather than
    hopefully.
    """
    Path(state_dir).mkdir(parents=True, exist_ok=True)
    Path(audit_log).parent.mkdir(parents=True, exist_ok=True)
    return {
        "corpus_dir": corpus_dir,
        "state_dir": state_dir,
        "audit_log": audit_log,
        "fail_once": fail_once,
    }


def fetch_documents(names: list[str], session: dict[str, Any]) -> list[dict[str, Any]]:
    """1:1 -- retrieve each document. Raises :class:`RateLimited` on refusal.

    The refusal is deliberately not caught here. A job that swallows a rate
    limit and returns a partial result turns a retryable condition into silent
    data loss; letting it propagate hands the task back to the queue, which
    knows how to wait.
    """
    fetched = []
    for name in names:
        if session["fail_once"] and _first_sight(session["state_dir"], name):
            raise RateLimited(f"429 Too Many Requests for {name}")
        text = (Path(session["corpus_dir"]) / name).read_text()
        with open(session["audit_log"], "a") as handle:
            handle.write(f"{name}\n")
        fetched.append({"name": name, "text": text})
    return fetched


def _first_sight(state_dir: str, name: str) -> bool:
    """Whether this is the first request for ``name``, across all workers.

    Uses an exclusive create rather than a check-then-write, so concurrent
    workers cannot both believe they are first.
    """
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:16]
    marker = Path(state_dir) / f"{digest}.seen"
    try:
        fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    os.close(fd)
    return True


def load_summarizer(max_words: int = 10, model: str = "stub") -> dict[str, Any]:
    """Worker setup: in real code, a model onto the GPU."""
    return {"max_words": max_words, "model": model}


def summarize(
    documents: list[dict[str, Any]], model: dict[str, Any]
) -> list[dict[str, Any]]:
    """1:1 -- one summary per document, over the whole batch at once."""
    summaries = []
    for document in documents:
        words = document["text"].split()
        summaries.append(
            {
                "name": document["name"],
                "summary": " ".join(words[: model["max_words"]]),
                "words": len(words),
                "model": model["model"],
            }
        )
    return summaries


def build_pipeline(
    corpus_dir: str,
    state_dir: str,
    audit_log: str,
    fail_once: bool = False,
    retry_backoff: float = 0.02,
    fetch_workers: int = 6,
) -> Any:
    """Assemble the fetch-then-summarize pipeline."""
    from blackfish.pipelines.spec import JobSpec, Pipeline, Placement

    module = "blackfish.pipelines.examples.summarize"
    return Pipeline(
        name="fetch-and-summarize",
        jobs=(
            JobSpec(
                name="fetch",
                fn=f"{module}:fetch_documents",
                setup=f"{module}:open_session",
                params={
                    "corpus_dir": corpus_dir,
                    "state_dir": state_dir,
                    "audit_log": audit_log,
                    "fail_once": fail_once,
                },
                # Small on purpose: a failure retries the whole batch, so this
                # is the blast radius of one refused request, not a throughput
                # knob.
                batch_size=2,
                max_attempts=8,
                retry_backoff=retry_backoff,
                # Cheap and IO-bound: many workers, no allocation, no GPU.
                placement=Placement.LOGIN,
                min_workers=1,
                max_workers=fetch_workers,
            ),
            JobSpec(
                name="summarize",
                fn=f"{module}:summarize",
                setup=f"{module}:load_summarizer",
                params={"max_words": 10},
                # Large on purpose: the forward pass is what costs, and the
                # work is a pure function of its input, so repeating a batch is
                # only wasted time.
                batch_size=8,
                min_workers=0,
                max_workers=2,
                resources={"gpus": 1, "cpus": 8, "mem": 64},
            ),
        ),
        edges=(("fetch", "summarize"),),
    )
