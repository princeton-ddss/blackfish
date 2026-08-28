"""The multi-stage chain: artifacts on disk and a record that grows."""

import json
from pathlib import Path

import pytest

from blackfish.pipelines import run_local
from blackfish.pipelines.examples.transcribe import (
    align,
    build_pipeline,
    diarize,
    load_asr,
    load_diarizer,
    load_aligner,
    transcribe,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def clips(tmp_path):
    def _make(count: int) -> list[str]:
        paths = []
        for index in range(count):
            path = tmp_path / "audio" / f"clip{index}.txt"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"hello world number {index}")
            paths.append(str(path))
        return paths

    return _make


class TestItemKey:
    def test_the_key_is_derived_from_the_input(self, clips, tmp_path):
        audio = clips(1)[0]
        first = transcribe([audio], load_asr(str(tmp_path / "out")))[0]
        second = transcribe([audio], load_asr(str(tmp_path / "out")))[0]
        assert first["key"] == second["key"]

    def test_artifacts_are_grouped_under_the_key(self, clips, tmp_path):
        out = str(tmp_path / "out")
        record = transcribe(clips(1), load_asr(out))[0]
        assert Path(record["transcript"]).parent.name == record["key"]

    def test_different_inputs_get_different_keys(self, clips, tmp_path):
        records = transcribe(clips(2), load_asr(str(tmp_path / "out")))
        assert records[0]["key"] != records[1]["key"]

    def test_a_replayed_stage_rewrites_its_own_artifact(self, clips, tmp_path):
        out = str(tmp_path / "out")
        audio = clips(1)
        first = transcribe(audio, load_asr(out))[0]
        second = transcribe(audio, load_asr(out))[0]
        assert first == second
        assert len(list(Path(out).rglob("transcript.json"))) == 1


class TestRecordGrowsAdditively:
    def test_each_stage_adds_a_field_and_keeps_the_rest(self, clips, tmp_path):
        out = str(tmp_path / "out")
        after_asr = transcribe(clips(1), load_asr(out))[0]
        after_diar = diarize([after_asr], load_diarizer(out))[0]
        after_align = align([after_diar], load_aligner(out))[0]

        assert set(after_asr) == {"key", "audio", "transcript"}
        assert set(after_diar) == set(after_asr) | {"speakers"}
        assert set(after_align) == set(after_diar) | {"aligned", "words"}

    def test_align_needs_an_artifact_from_two_stages_back(self, clips, tmp_path):
        """Carried forward, because a task only sees its immediate upstream."""
        out = str(tmp_path / "out")
        record = diarize(transcribe(clips(1), load_asr(out)), load_diarizer(out))[0]
        stripped = {k: v for k, v in record.items() if k != "transcript"}
        with pytest.raises(KeyError, match="transcript"):
            align([stripped], load_aligner(out))


class TestEndToEnd:
    async def test_every_clip_produces_all_three_artifacts(self, clips, tmp_path):
        paths = clips(5)
        status, results = await run_local(
            build_pipeline(str(tmp_path / "out")),
            paths,
            root=tmp_path / "run",
            timeout=60,
        )
        assert status.complete
        assert len(results) == 5
        for record in results:
            for stage in ("transcript", "speakers", "aligned"):
                assert Path(record[stage]).exists(), stage

    async def test_the_final_artifact_combines_both_upstreams(self, clips, tmp_path):
        paths = clips(1)
        _, results = await run_local(
            build_pipeline(str(tmp_path / "out"), speakers=2),
            paths,
            root=tmp_path / "run",
            timeout=60,
        )
        aligned = json.loads(Path(results[0]["aligned"]).read_text())
        assert aligned["source"] == paths[0]
        assert [s["word"] for s in aligned["segments"]] == [
            "hello",
            "world",
            "number",
            "0",
        ]
        assert [s["speaker"] for s in aligned["segments"]] == [
            "SPEAKER_00",
            "SPEAKER_01",
            "SPEAKER_00",
            "SPEAKER_01",
        ]

    async def test_the_record_carries_full_provenance(self, clips, tmp_path):
        _, results = await run_local(
            build_pipeline(str(tmp_path / "out")),
            clips(1),
            root=tmp_path / "run",
            timeout=60,
        )
        record = results[0]
        assert record["audio"].endswith("clip0.txt")
        assert record["words"] == 4
        assert record["key"] in record["aligned"]

    async def test_stages_run_in_order(self, clips, tmp_path):
        status, _ = await run_local(
            build_pipeline(str(tmp_path / "out")),
            clips(3),
            root=tmp_path / "run",
            timeout=60,
        )
        assert [job.done for job in status.jobs] == [3, 3, 3]
