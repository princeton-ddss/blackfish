"""A worked example: a standing run over a directory that keeps growing.

    transform (1:1)   a file  ->  a converted file

The pipeline itself is the least interesting part. What this example is about
is the two kinds of continuity a long-lived pipeline needs, which are different
problems with different answers:

**Surviving a restart.** Nothing about a run lives in the coordinator's memory.
The queues, the attempt counts and the completion barriers are all in the task
store, so a coordinator that dies is restarted by reopening the same file and
ticking again -- work already finished is not redone, and work that was in
flight comes back through lease expiry. There is no checkpoint to write and no
resume protocol to get right; durability is the store's job, and the
coordinator is stateless on purpose.

**Picking up new inputs.** Re-scanning the directory and submitting everything
would reprocess the whole thing. Passing each file's path as its ``key`` makes
submission idempotent within the run, so a re-scan enqueues only what is new.
The pipeline therefore needs no manifest, no "last seen" marker and no
bookkeeping of its own -- the queue already knows what it has seen.

The trade-off to understand: this is idempotent *within a run*. Task IDs are
derived from the run, so the same key in a **new** run is new work. That is
deliberate -- a fresh run over the same directory is usually exactly what
someone means by re-running -- but it means "process this directory forever"
is one long-lived unsealed run, not a series of runs.
"""

from __future__ import annotations

import glob
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from blackfish.pipelines.coordinator import Coordinator

DEFAULT_PATTERN = "*.txt"


def scan_directory(directory: str, pattern: str = DEFAULT_PATTERN) -> list[str]:
    """Return matching files, sorted, so submission order is reproducible."""
    return sorted(glob.glob(os.path.join(directory, pattern)))


def submit_directory(
    coordinator: "Coordinator",
    run_id: str,
    job: str,
    directory: str,
    pattern: str = DEFAULT_PATTERN,
) -> int:
    """Enqueue every matching file, keyed by path, and report what was new.

    Safe to call on a timer. Files already submitted to this run are ignored,
    so the return value is the count of genuinely new inputs.
    """
    paths = scan_directory(directory, pattern)
    return coordinator.submit(run_id, job, paths, keys=paths)


def open_output(output_dir: str, audit_log: str) -> dict[str, Any]:
    """Worker setup: make sure the output directory exists.

    A real job loads a model here. This one only has somewhere to write, which
    is still worth doing once per worker rather than once per file.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    Path(audit_log).parent.mkdir(parents=True, exist_ok=True)
    return {"output_dir": output_dir, "audit_log": audit_log}


def transform_file(paths: list[str], settings: dict[str, Any]) -> list[dict[str, Any]]:
    """1:1 -- convert one file into one output file.

    Writes an audit line per file processed. That is not decoration: on a
    pipeline that runs for weeks over a growing directory, "was this file
    handled, and when" is the question people actually ask, and at-least-once
    delivery means the answer can legitimately be "twice".
    """
    records = []
    for path in paths:
        text = Path(path).read_text()
        output = Path(settings["output_dir"]) / (Path(path).stem + ".out")
        output.write_text(text.upper())
        # One small append per file. A single write under PIPE_BUF is atomic on
        # POSIX, so concurrent workers interleave lines rather than corrupt them.
        with open(settings["audit_log"], "a") as handle:
            handle.write(f"{path}\n")
        records.append({"input": path, "output": str(output)})
    return records


def build_pipeline(output_dir: str, audit_log: str, max_workers: int = 3) -> Any:
    """Assemble the directory-processing pipeline."""
    from blackfish.pipelines.spec import JobSpec, Pipeline, Placement

    return Pipeline(
        name="transform-directory",
        jobs=(
            JobSpec(
                name="transform",
                fn="blackfish.pipelines.examples.resumable:transform_file",
                setup="blackfish.pipelines.examples.resumable:open_output",
                params={"output_dir": output_dir, "audit_log": audit_log},
                batch_size=4,
                min_workers=0,
                max_workers=max_workers,
                placement=Placement.LOGIN,
            ),
        ),
    )
