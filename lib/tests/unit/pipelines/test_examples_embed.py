"""The embedding example: chunk planning, shard writes, and the manifest fold.

This exercises the shape a real "run a model over a big file" job takes, so the
tests are as much about the pattern as about the code -- particularly that a
chunk plan covers its file exactly, and that a redelivered chunk cannot leave a
second shard behind.
"""

import json

import pytest

from blackfish.pipelines import run_local
from blackfish.pipelines.examples.embed import (
    DEFAULT_CHUNK_LINES,
    build_pipeline,
    embed_chunk,
    encode,
    load_encoder,
    merge_manifests,
    plan_chunks,
    read_chunk,
    shard_path,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def corpus(tmp_path):
    def _write(lines: int, name: str = "corpus.txt"):
        path = tmp_path / name
        path.write_text("".join(f"line {i}\n" for i in range(lines)))
        return str(path)

    return _write


class TestPlanning:
    def test_a_full_file_splits_into_whole_chunks(self, corpus):
        chunks = plan_chunks([corpus(10)], {"chunk_lines": 5})[0]
        assert [c["lines"] for c in chunks] == [5, 5]
        assert [c["index"] for c in chunks] == [0, 1]

    def test_the_last_chunk_takes_the_remainder(self, corpus):
        chunks = plan_chunks([corpus(11)], {"chunk_lines": 5})[0]
        assert [c["lines"] for c in chunks] == [5, 5, 1]

    def test_chunks_tile_the_file_with_no_gaps_or_overlaps(self, corpus):
        path = corpus(23)
        chunks = plan_chunks([path], {"chunk_lines": 4})[0]
        assert chunks[0]["start"] == 0
        for earlier, later in zip(chunks, chunks[1:]):
            assert earlier["end"] == later["start"]
        with open(path, "rb") as handle:
            assert chunks[-1]["end"] == len(handle.read())

    def test_reading_every_chunk_reproduces_the_file(self, corpus):
        path = corpus(23)
        chunks = plan_chunks([path], {"chunk_lines": 4})[0]
        recovered = [line for chunk in chunks for line in read_chunk(chunk)]
        assert recovered == open(path).read().splitlines()

    def test_an_empty_file_plans_no_chunks(self, tmp_path):
        path = tmp_path / "empty.txt"
        path.write_text("")
        assert plan_chunks([str(path)], {"chunk_lines": 4}) == [[]]

    def test_a_file_shorter_than_one_chunk_still_plans_one(self, corpus):
        chunks = plan_chunks([corpus(2)], {"chunk_lines": 512})[0]
        assert len(chunks) == 1
        assert chunks[0]["lines"] == 2

    def test_each_file_gets_its_own_group(self, corpus):
        groups = plan_chunks(
            [corpus(4, "a.txt"), corpus(8, "b.txt")], {"chunk_lines": 4}
        )
        assert [len(group) for group in groups] == [1, 2]

    def test_the_chunk_size_defaults_when_unset(self, corpus):
        chunks = plan_chunks([corpus(3)], {})[0]
        assert chunks[0]["lines"] == 3
        assert DEFAULT_CHUNK_LINES > 1

    def test_rejects_a_nonsensical_chunk_size(self, corpus):
        with pytest.raises(ValueError, match="chunk_lines"):
            plan_chunks([corpus(3)], {"chunk_lines": 0})


class TestEncoding:
    def test_the_same_text_always_encodes_the_same(self):
        """Two workers must agree; a per-process salt would be invisible here."""
        assert encode("hello", 8) == encode("hello", 8)

    def test_different_text_encodes_differently(self):
        assert encode("hello", 8) != encode("world", 8)

    def test_the_dimension_is_honoured(self):
        assert len(encode("hello", 16)) == 16

    def test_components_are_normalized(self):
        assert all(0.0 <= value <= 1.0 for value in encode("hello", 32))


class TestShards:
    def test_a_shard_holds_one_vector_per_line(self, corpus, tmp_path):
        chunk = plan_chunks([corpus(6)], {"chunk_lines": 6})[0][0]
        encoder = load_encoder(str(tmp_path / "shards"), dim=4)
        record = embed_chunk([chunk], encoder)[0]
        payload = json.loads(open(record["shards"][0]["path"]).read())
        assert len(payload["vectors"]) == 6
        assert all(len(vector) == 4 for vector in payload["vectors"])

    def test_the_record_reports_the_row_count(self, corpus, tmp_path):
        chunk = plan_chunks([corpus(6)], {"chunk_lines": 4})[0][1]
        encoder = load_encoder(str(tmp_path / "shards"))
        assert embed_chunk([chunk], encoder)[0]["rows"] == 2

    def test_a_redelivered_chunk_rewrites_the_same_shard(self, corpus, tmp_path):
        """At-least-once delivery must not leave two divergent shards."""
        chunk = plan_chunks([corpus(6)], {"chunk_lines": 6})[0][0]
        shard_dir = tmp_path / "shards"
        encoder = load_encoder(str(shard_dir))
        first = embed_chunk([chunk], encoder)[0]
        second = embed_chunk([chunk], encoder)[0]
        assert first == second
        assert len(list(shard_dir.glob("shard-*.json"))) == 1

    def test_different_chunks_get_different_shards(self, corpus, tmp_path):
        chunks = plan_chunks([corpus(8)], {"chunk_lines": 4})[0]
        assert shard_path("/s", chunks[0]) != shard_path("/s", chunks[1])

    def test_the_shard_directory_is_created_by_setup(self, tmp_path):
        target = tmp_path / "deep" / "shards"
        load_encoder(str(target))
        assert target.is_dir()


class TestManifestFold:
    def test_folding_concatenates_shards_and_sums_rows(self):
        merged = merge_manifests(
            [
                {"shards": [{"path": "a", "index": 0, "rows": 3}], "rows": 3},
                {"shards": [{"path": "b", "index": 1, "rows": 2}], "rows": 2},
            ]
        )
        assert merged["rows"] == 5
        assert [s["path"] for s in merged["shards"]] == ["a", "b"]

    def test_the_fold_is_closed_over_its_own_output(self):
        """A reduce queue mixes upstream outputs with its own partials."""
        one = merge_manifests([{"shards": [{"path": "a"}], "rows": 1}])
        two = merge_manifests([one, {"shards": [{"path": "b"}], "rows": 1}])
        assert two["rows"] == 2
        assert len(two["shards"]) == 2

    def test_the_fold_is_commutative_in_its_totals(self):
        left = {"shards": [{"path": "a"}], "rows": 1}
        right = {"shards": [{"path": "b"}], "rows": 4}
        assert (
            merge_manifests([left, right])["rows"]
            == merge_manifests([right, left])["rows"]
        )


class TestEndToEnd:
    async def test_every_line_is_embedded_exactly_once(self, corpus, tmp_path):
        path = corpus(23)
        pipeline = build_pipeline(
            shard_dir=str(tmp_path / "shards"), chunk_lines=4, dim=4, max_workers=3
        )
        status, results = await run_local(
            pipeline, [path], root=tmp_path / "run", timeout=60
        )
        assert status.complete
        assert status.dead_letters == 0

        manifest = results[0]
        assert manifest["rows"] == 23
        assert len(manifest["shards"]) == 6  # 5 full chunks of 4, plus 3
        assert sorted(s["index"] for s in manifest["shards"]) == [0, 1, 2, 3, 4, 5]

    async def test_the_shards_reassemble_into_the_original_corpus(
        self, corpus, tmp_path
    ):
        path = corpus(23)
        status, results = await run_local(
            build_pipeline(str(tmp_path / "shards"), chunk_lines=4, dim=4),
            [path],
            root=tmp_path / "run",
            timeout=60,
        )
        assert status.complete

        vectors = []
        for shard in sorted(results[0]["shards"], key=lambda s: s["index"]):
            vectors.extend(json.loads(open(shard["path"]).read())["vectors"])

        expected = [encode(line, 4) for line in open(path).read().splitlines()]
        assert vectors == expected

    async def test_a_corpus_smaller_than_one_chunk_still_runs(self, corpus, tmp_path):
        status, results = await run_local(
            build_pipeline(str(tmp_path / "shards"), chunk_lines=512),
            [corpus(3)],
            root=tmp_path / "run",
            timeout=60,
        )
        assert status.complete
        assert results[0]["rows"] == 3

    async def test_an_empty_corpus_completes_with_no_shards(self, tmp_path):
        path = tmp_path / "empty.txt"
        path.write_text("")
        status, results = await run_local(
            build_pipeline(str(tmp_path / "shards")),
            [str(path)],
            root=tmp_path / "run",
            timeout=60,
        )
        assert status.complete
        # The plan job emitted nothing, so embed and manifest had no work and
        # the reduce produced no output at all.
        assert results == []

    async def test_several_files_share_one_run(self, corpus, tmp_path):
        status, results = await run_local(
            build_pipeline(str(tmp_path / "shards"), chunk_lines=4),
            [corpus(8, "a.txt"), corpus(6, "b.txt")],
            root=tmp_path / "run",
            timeout=60,
        )
        assert status.complete
        assert results[0]["rows"] == 14

    async def test_shards_from_several_files_stay_distinguishable(
        self, corpus, tmp_path
    ):
        """``index`` restarts per file, so ordering needs the source too."""
        first, second = corpus(8, "a.txt"), corpus(6, "b.txt")
        status, results = await run_local(
            build_pipeline(str(tmp_path / "shards"), chunk_lines=4, dim=4),
            [first, second],
            root=tmp_path / "run",
            timeout=60,
        )
        assert status.complete

        shards = results[0]["shards"]
        assert {s["source"] for s in shards} == {first, second}
        keys = [(s["source"], s["index"]) for s in shards]
        assert len(set(keys)) == len(keys), "every shard is uniquely addressable"

        for source in (first, second):
            vectors = []
            for shard in sorted(
                (s for s in shards if s["source"] == source),
                key=lambda s: s["index"],
            ):
                vectors.extend(json.loads(open(shard["path"]).read())["vectors"])
            assert vectors == [
                encode(line, 4) for line in open(source).read().splitlines()
            ]
