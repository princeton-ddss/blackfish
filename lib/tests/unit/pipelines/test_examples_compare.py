"""The diamond example: fan-out, independent scaling, and a keyed join."""

import pytest

from blackfish.pipelines import run_local
from blackfish.pipelines.backends.local import ThreadBackend
from blackfish.pipelines.coordinator import Coordinator
from blackfish.pipelines.examples.compare import (
    build_pipeline,
    merge_scores,
    prepare_documents,
    score_fast,
    score_slow,
)
from blackfish.pipelines.payload import PayloadStore
from blackfish.pipelines.store import TaskStore

pytestmark = pytest.mark.anyio

DOCUMENTS = [f"document number {i} with some text" for i in range(12)]


class TestKeying:
    def test_ids_are_derived_from_content(self):
        """A positional index would not survive a retry or a reorder."""
        first = prepare_documents(["a", "b"])
        second = prepare_documents(["b", "a"])
        assert first[0]["id"] == second[1]["id"]

    def test_different_documents_get_different_ids(self):
        prepared = prepare_documents(["a", "b"])
        assert prepared[0]["id"] != prepared[1]["id"]

    def test_both_branches_key_their_output_by_document(self):
        docs = prepare_documents(["hello"])
        fast = score_fast(docs, {"label": "fast"})[0]
        slow = score_slow(docs, {"label": "slow"})[0]
        assert set(fast) == set(slow) == {docs[0]["id"]}


class TestFold:
    def test_the_two_branches_merge_per_document(self):
        merged = merge_scores([{"d1": {"fast": 1.0}}, {"d1": {"slow": 2.0}}])
        assert merged == {"d1": {"fast": 1.0, "slow": 2.0}}

    def test_documents_stay_separate(self):
        merged = merge_scores([{"d1": {"fast": 1.0}}, {"d2": {"fast": 3.0}}])
        assert merged == {"d1": {"fast": 1.0}, "d2": {"fast": 3.0}}

    def test_the_fold_is_closed_over_its_own_output(self):
        once = merge_scores([{"d1": {"fast": 1.0}}])
        twice = merge_scores([once, {"d1": {"slow": 2.0}}])
        assert twice == {"d1": {"fast": 1.0, "slow": 2.0}}

    def test_the_fold_is_commutative(self):
        left, right = {"d1": {"fast": 1.0}}, {"d1": {"slow": 2.0}}
        assert merge_scores([left, right]) == merge_scores([right, left])

    def test_the_fold_is_associative(self):
        a, b, c = {"x": {"1": 1}}, {"y": {"2": 2}}, {"x": {"3": 3}}
        assert merge_scores([merge_scores([a, b]), c]) == merge_scores(
            [a, merge_scores([b, c])]
        )


class TestEndToEnd:
    async def test_every_document_is_scored_by_both_branches(self, tmp_path):
        status, results = await run_local(
            build_pipeline(), DOCUMENTS, root=tmp_path, timeout=60
        )
        assert status.complete
        table = results[0]
        assert len(table) == len(DOCUMENTS)
        assert all(set(scores) == {"fast", "slow"} for scores in table.values())

    async def test_fan_out_delivers_every_document_to_both_branches(self, tmp_path):
        """Fan-out copies the stream; it does not split it."""
        status, _ = await run_local(
            build_pipeline(), DOCUMENTS, root=tmp_path, timeout=60
        )
        assert status.job("score_fast").done == len(DOCUMENTS)
        assert status.job("score_slow").done == len(DOCUMENTS)

    async def test_the_slow_branch_does_not_change_the_answer(self, tmp_path):
        _, quick = await run_local(
            build_pipeline(), DOCUMENTS, root=tmp_path / "a", timeout=60
        )
        _, delayed = await run_local(
            build_pipeline(slow_delay=0.005),
            DOCUMENTS,
            root=tmp_path / "b",
            timeout=60,
        )
        assert quick == delayed


class TestJoinWaitsForBothBranches:
    async def test_the_join_never_completes_before_the_slow_branch(self, tmp_path):
        """Checked as an invariant on every tick, not sampled once."""
        pipeline = build_pipeline(slow_delay=0.002)
        store = TaskStore(tmp_path / "p.db")
        payloads = PayloadStore(tmp_path / "payloads")
        backend = ThreadBackend(store, payloads, pipeline)
        coordinator = Coordinator(store, payloads, backend, tick_seconds=0.005)
        run_id = coordinator.start_run(pipeline, DOCUMENTS)

        observed_incomplete_slow = False
        try:
            for _ in range(2000):
                status = await coordinator.tick(run_id)
                if not status.job("score_slow").complete:
                    observed_incomplete_slow = True
                    assert not status.job("compare").complete, (
                        "the join finished while the slow branch was still live"
                    )
                if status.complete:
                    break
            assert status.complete
            assert observed_incomplete_slow, "the slow branch was never observed live"
        finally:
            await backend.shutdown(run_id)
            store.close()

    async def test_the_join_waits_even_when_one_branch_finishes_first(self, tmp_path):
        pipeline = build_pipeline(slow_delay=0.002)
        store = TaskStore(tmp_path / "p.db")
        payloads = PayloadStore(tmp_path / "payloads")
        backend = ThreadBackend(store, payloads, pipeline)
        coordinator = Coordinator(store, payloads, backend, tick_seconds=0.005)
        run_id = coordinator.start_run(pipeline, DOCUMENTS)
        try:
            saw_asymmetry = False
            for _ in range(2000):
                status = await coordinator.tick(run_id)
                fast_done = status.job("score_fast").complete
                slow_done = status.job("score_slow").complete
                if fast_done and not slow_done:
                    saw_asymmetry = True
                    assert not status.job("compare").complete
                if status.complete:
                    break
            assert status.complete
            assert saw_asymmetry, "branches never diverged; raise slow_delay"
        finally:
            await backend.shutdown(run_id)
            store.close()
