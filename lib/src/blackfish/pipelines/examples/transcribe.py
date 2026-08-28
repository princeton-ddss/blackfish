"""A worked example: a multi-stage chain whose stages exchange files.

    transcribe (1:1)  ->  diarize (1:1)  ->  align (1:1)

Three GPU stages, each loading a different model, each producing an artifact
too large to put in a queue. The two ideas worth taking from it:

**Establish an item key at ingestion, then carry it.** ``transcribe`` derives a
stable ``key`` from the input and every stage writes its artifact under
``<output_dir>/<key>/``. So an item's outputs are co-located and predictable,
a partial run can be inspected by key, and a retried stage overwrites its own
artifact rather than creating a second one. Deriving the key from content
rather than from arrival order means it survives retries, reordering and a
restart.

**The payload is a record that grows.** Each stage adds a field and passes the
*whole* record on. That is not stylistic: there is no way to reach back to an
earlier stage's output, because a task only ever sees what its immediate
upstream emitted. Anything a later stage needs has to be carried forward, so
``align`` -- which needs the audio, the transcript and the speakers -- gets
them because ``diarize`` passed all three along.

The corollary is worth knowing before designing a long chain: a stage that
drops a field silently starves every stage after it, and nothing in the type
system will say so. Keep the record additive.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _artifact(output_dir: str, key: str, name: str) -> Path:
    return Path(output_dir) / key / name


def _write_json(path: Path, payload: Any) -> None:
    from blackfish.pipelines.payload import write_atomic

    write_atomic(path, json.dumps(payload, indent=2).encode("utf-8"))


# ---------------------------------------------------------------------------
# transcribe
# ---------------------------------------------------------------------------


def load_asr(output_dir: str, model: str = "whisper-stub") -> dict[str, Any]:
    """Worker setup: in real code, weights onto the GPU."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    return {"output_dir": output_dir, "model": model}


def transcribe(inputs: list[str], asr: dict[str, Any]) -> list[dict[str, Any]]:
    """1:1 -- audio path in, a record with the transcript artifact out."""
    records = []
    for audio in inputs:
        key = hashlib.sha256(audio.encode("utf-8")).hexdigest()[:16]
        words = Path(audio).read_text().split()
        path = _artifact(asr["output_dir"], key, "transcript.json")
        _write_json(path, {"model": asr["model"], "words": words})
        records.append(
            {
                "key": key,
                "audio": audio,
                "transcript": str(path),
            }
        )
    return records


# ---------------------------------------------------------------------------
# diarize
# ---------------------------------------------------------------------------


def load_diarizer(output_dir: str, speakers: int = 2) -> dict[str, Any]:
    return {"output_dir": output_dir, "speakers": speakers}


def diarize(
    records: list[dict[str, Any]], diarizer: dict[str, Any]
) -> list[dict[str, Any]]:
    """1:1 -- assign a speaker per word, and pass the whole record on.

    Note what is returned: the incoming record plus one field. Dropping
    ``audio`` here would work fine until ``align`` needed it.
    """
    out = []
    for record in records:
        words = json.loads(Path(record["transcript"]).read_text())["words"]
        turns = [index % diarizer["speakers"] for index, _ in enumerate(words)]
        path = _artifact(diarizer["output_dir"], record["key"], "speakers.json")
        _write_json(path, {"speakers": diarizer["speakers"], "turns": turns})
        out.append({**record, "speakers": str(path)})
    return out


# ---------------------------------------------------------------------------
# align
# ---------------------------------------------------------------------------


def load_aligner(output_dir: str) -> dict[str, Any]:
    return {"output_dir": output_dir}


def align(
    records: list[dict[str, Any]], aligner: dict[str, Any]
) -> list[dict[str, Any]]:
    """1:1 -- combine two upstream artifacts into a third.

    This is the stage that shows why the record has to be additive: it needs
    ``transcript`` from two stages back and ``speakers`` from one, and the only
    reason it has both is that ``diarize`` carried the first one forward.
    """
    out = []
    for record in records:
        words = json.loads(Path(record["transcript"]).read_text())["words"]
        turns = json.loads(Path(record["speakers"]).read_text())["turns"]
        segments = [
            {"word": word, "speaker": f"SPEAKER_{turn:02d}"}
            for word, turn in zip(words, turns, strict=True)
        ]
        path = _artifact(aligner["output_dir"], record["key"], "aligned.json")
        _write_json(path, {"source": record["audio"], "segments": segments})
        out.append({**record, "aligned": str(path), "words": len(segments)})
    return out


def build_pipeline(output_dir: str, speakers: int = 2, max_workers: int = 2) -> Any:
    """Assemble the three-stage chain.

    Each stage declares its own resources: ASR wants a full GPU, diarization is
    lighter, alignment is pure CPU. They are separate jobs precisely so they
    can be sized -- and scaled -- separately.
    """
    from blackfish.pipelines.spec import JobSpec, Pipeline, Placement

    module = "blackfish.pipelines.examples.transcribe"
    return Pipeline(
        name="transcribe-diarize-align",
        jobs=(
            JobSpec(
                name="transcribe",
                fn=f"{module}:transcribe",
                setup=f"{module}:load_asr",
                params={"output_dir": output_dir},
                batch_size=4,
                max_workers=max_workers,
                resources={"gpus": 1, "cpus": 8, "mem": 64},
            ),
            JobSpec(
                name="diarize",
                fn=f"{module}:diarize",
                setup=f"{module}:load_diarizer",
                params={"output_dir": output_dir, "speakers": speakers},
                batch_size=4,
                max_workers=max_workers,
                resources={"gpus": 1, "cpus": 4, "mem": 32},
            ),
            JobSpec(
                name="align",
                fn=f"{module}:align",
                setup=f"{module}:load_aligner",
                params={"output_dir": output_dir},
                batch_size=8,
                max_workers=max_workers,
                placement=Placement.LOGIN,
            ),
        ),
        edges=(("transcribe", "diarize"), ("diarize", "align")),
    )
