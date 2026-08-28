"""A worked example pipeline, small enough to read and real enough to run.

Counts words across a set of documents:

    read (1:N)  ->  count (1:1)  ->  merge (N:1)

``read`` fans one document out into its lines, ``count`` maps each line to a
per-word tally, and ``merge`` folds those tallies into one. All three
cardinalities appear, and ``count`` carries a ``setup`` so the shape of a job
that loads a model is visible without needing a GPU to run it.

Workers import these functions by path, so they must live in an importable
module -- a closure defined in a notebook will not do.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

_WORD = re.compile(r"[a-z']+")


def split_lines(documents: list[str]) -> list[list[str]]:
    """1:N -- one document becomes its non-empty lines.

    Returns one group per input, which is what lets a retried document replace
    exactly its own lines instead of duplicating the batch's.
    """
    return [
        [line for line in document.splitlines() if line.strip()]
        for document in documents
    ]


def load_stopwords() -> set[str]:
    """Stand-in for an expensive per-worker setup, run once per process."""
    return {"the", "a", "an", "and", "or", "of", "to", "in", "is", "it"}


def count_words(lines: list[str], stopwords: set[str]) -> list[dict[str, int]]:
    """1:1 -- one tally per line, using the context built by :func:`load_stopwords`.

    The batch is handed over whole so a real implementation can do the work in
    one vectorized call; the contract is only that the outputs line up with the
    inputs.
    """
    tallies: list[dict[str, int]] = []
    for line in lines:
        counter = Counter(
            word for word in _WORD.findall(line.lower()) if word not in stopwords
        )
        tallies.append(dict(counter))
    return tallies


def merge_counts(tallies: list[dict[str, int]]) -> dict[str, int]:
    """N:1 -- fold tallies into one.

    Commutative and associative, so it is safe to apply to partial results in
    any grouping and any order -- which is exactly what the tree reduce does.
    """
    total: Counter[str] = Counter()
    for tally in tallies:
        total.update(tally)
    return dict(total)


def build_pipeline(**overrides: Any) -> Any:
    """Assemble the example pipeline.

    Args:
        **overrides: Passed to every job, e.g. ``max_workers=4``.
    """
    from blackfish.pipelines.spec import Cardinality, JobSpec, Pipeline, Placement

    common: dict[str, Any] = {"placement": Placement.LOGIN, **overrides}
    return Pipeline(
        name="word-count",
        jobs=(
            JobSpec(
                name="read",
                fn="blackfish.pipelines.example:split_lines",
                cardinality=Cardinality.ONE_TO_MANY,
                batch_size=2,
                **common,
            ),
            JobSpec(
                name="count",
                fn="blackfish.pipelines.example:count_words",
                setup="blackfish.pipelines.example:load_stopwords",
                cardinality=Cardinality.ONE_TO_ONE,
                batch_size=8,
                **common,
            ),
            JobSpec(
                name="merge",
                fn="blackfish.pipelines.example:merge_counts",
                cardinality=Cardinality.MANY_TO_ONE,
                batch_size=4,
                **common,
            ),
        ),
        edges=(("read", "count"), ("count", "merge")),
    )
