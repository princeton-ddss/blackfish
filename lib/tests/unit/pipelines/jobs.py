"""Job functions for the pipeline tests.

Workers resolve jobs by import path, so test functions have to live in a real
module rather than in a fixture or a closure.
"""

from __future__ import annotations

from typing import Any

SETUP_CALLS = 0
BATCH_SIZES: list[int] = []
FAILURES: dict[str, int] = {}


def reset() -> None:
    global SETUP_CALLS
    SETUP_CALLS = 0
    BATCH_SIZES.clear()
    FAILURES.clear()
    SETUP_KWARGS.clear()
    SEEN_CONTEXT.clear()


def load_model() -> dict[str, Any]:
    """Stands in for loading weights: expensive, and paid once per worker."""
    global SETUP_CALLS
    SETUP_CALLS += 1
    return {"scale": 10, "loaded": SETUP_CALLS}


def double(values: list[int]) -> list[int]:
    BATCH_SIZES.append(len(values))
    return [value * 2 for value in values]


def scale(values: list[int], model: dict[str, Any]) -> list[int]:
    BATCH_SIZES.append(len(values))
    return [value * model["scale"] for value in values]


def explode(values: list[int]) -> list[int]:
    raise RuntimeError("model went sideways")


def flaky(values: list[int]) -> list[int]:
    """Fails the first time it sees a value, succeeds afterwards."""
    for value in values:
        key = str(value)
        FAILURES[key] = FAILURES.get(key, 0) + 1
        if FAILURES[key] == 1:
            raise RuntimeError(f"transient failure on {value}")
    return values


def wrong_length(values: list[int]) -> list[int]:
    return values[:-1]


def not_a_sequence(values: list[int]) -> int:
    return 42


def fan_out(values: list[int]) -> list[list[int]]:
    return [list(range(value)) for value in values]


def flat_instead_of_nested(values: list[int]) -> list[int]:
    return [value for value in values]


def total(values: list[int]) -> int:
    BATCH_SIZES.append(len(values))
    return sum(values)


SETUP_KWARGS: dict[str, Any] = {}
SEEN_CONTEXT: list[Any] = []


def build_context(scale: int = 1, label: str = "default") -> dict[str, Any]:
    """Setup that records the keywords it was configured with."""
    SETUP_KWARGS.clear()
    SETUP_KWARGS.update({"scale": scale, "label": label})
    return {"scale": scale, "label": label}


def multiply(values: list[int], context: dict[str, Any]) -> list[int]:
    SEEN_CONTEXT.append(context)
    return [value * int(context["scale"]) for value in values]
