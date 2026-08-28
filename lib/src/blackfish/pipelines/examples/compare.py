"""A worked example: score every document with two models and compare them.

                    ┌─► score_fast (1:1) ─┐
    prepare (1:1) ──┤                     ├─► compare (N:1)
                    └─► score_slow (1:1) ─┘

A diamond, with branches of deliberately different speed. Three things this
shape teaches that a linear pipeline does not:

**Fan-out is a copy, not a split.** Every output of ``prepare`` is delivered to
*each* downstream job. The two branches are independent consumers of the same
stream, not two halves of it, so both see every document.

**The branches scale independently.** They are separate queues with separate
worker counts, so the slow branch accumulates backlog and is given more workers
while the fast branch drains and releases its own. Nothing coordinates them --
that falls out of scaling each job on its own queue depth.

**There is no built-in keyed join, and there is deliberately no barrier.** The
join is a reduce, and a reduce gives you "everything in one place"; matching a
document's two scores is something the fold does, by keying on the document ID
that both branches carry through. This is the honest shape of the primitive: if
you want a relational join you build it in the fold, and the values you fold
must be keyed before they arrive.

Which is why both branches emit ``{doc_id: {...}}`` rather than a bare score.
A reduce queue holds a mix of upstream outputs and its own partial results, so
the fold has to be closed over its own output type -- the same constraint the
embedding example runs into, showing up here as "key it upstream, not in the
join".
"""

from __future__ import annotations

import hashlib
import time
from typing import Any


def prepare_documents(documents: list[str]) -> list[dict[str, Any]]:
    """1:1 -- give each document a stable ID both branches will carry.

    The ID is the join key. Deriving it from the content rather than from a
    counter means it survives retries, reordering and a restart, none of which
    a positional index does.
    """
    prepared = []
    for document in documents:
        doc_id = hashlib.sha256(document.encode("utf-8")).hexdigest()[:12]
        prepared.append({"id": doc_id, "text": document})
    return prepared


def score_fast(
    documents: list[dict[str, Any]], config: dict[str, Any]
) -> list[dict[str, dict[str, Any]]]:
    """1:1 -- a cheap heuristic. Keyed by document ID, ready to fold."""
    label = str(config.get("label", "fast"))
    return [
        {doc["id"]: {label: round(len(doc["text"]) / 100.0, 4)}} for doc in documents
    ]


def score_slow(
    documents: list[dict[str, Any]], config: dict[str, Any]
) -> list[dict[str, dict[str, Any]]]:
    """1:1 -- the expensive model, stubbed.

    ``delay_seconds`` stands in for a GPU forward pass, so the branch is
    genuinely slower and the backlog it accumulates is real rather than
    hypothetical.
    """
    label = str(config.get("label", "slow"))
    delay = float(config.get("delay_seconds", 0.0))
    scored = []
    for doc in documents:
        if delay:
            time.sleep(delay)
        digest = hashlib.sha256(doc["text"].encode("utf-8")).digest()
        scored.append({doc["id"]: {label: round(digest[0] / 255.0, 4)}})
    return scored


def merge_scores(
    partials: list[dict[str, dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    """N:1 -- fold per-document scores into one table.

    Commutative and associative because the two branches write different keys
    under each document ID, so no fold ever has to choose between two values.
    If they could collide, this function would need a rule -- and picking one
    inside a fold whose grouping is nondeterministic is how a pipeline starts
    producing different answers on different runs.
    """
    merged: dict[str, dict[str, Any]] = {}
    for partial in partials:
        for doc_id, scores in partial.items():
            merged.setdefault(doc_id, {}).update(scores)
    return merged


def build_pipeline(
    slow_delay: float = 0.0,
    fast_workers: int = 2,
    slow_workers: int = 4,
) -> Any:
    """Assemble the two-model comparison.

    Args:
        slow_delay: Seconds the slow branch spends per document.
        fast_workers: Ceiling on the cheap branch.
        slow_workers: Ceiling on the expensive branch. Higher than the fast
            branch on purpose: the autoscaler will use it, because that is the
            queue that actually backs up.
    """
    from blackfish.pipelines.spec import Cardinality, JobSpec, Pipeline, Placement

    module = "blackfish.pipelines.examples.compare"
    return Pipeline(
        name="compare-models",
        jobs=(
            JobSpec(
                name="prepare",
                fn=f"{module}:prepare_documents",
                batch_size=8,
                placement=Placement.LOGIN,
                max_workers=1,
            ),
            JobSpec(
                name="score_fast",
                fn=f"{module}:score_fast",
                params={"label": "fast"},
                batch_size=8,
                max_workers=fast_workers,
                placement=Placement.LOGIN,
            ),
            JobSpec(
                name="score_slow",
                fn=f"{module}:score_slow",
                params={"label": "slow", "delay_seconds": slow_delay},
                batch_size=2,
                max_workers=slow_workers,
                resources={"gpus": 1, "cpus": 8, "mem": 64},
            ),
            JobSpec(
                name="compare",
                fn=f"{module}:merge_scores",
                cardinality=Cardinality.MANY_TO_ONE,
                batch_size=8,
                placement=Placement.LOGIN,
            ),
        ),
        edges=(
            ("prepare", "score_fast"),
            ("prepare", "score_slow"),
            ("score_fast", "compare"),
            ("score_slow", "compare"),
        ),
    )
