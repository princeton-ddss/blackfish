"""End-to-end runs: the DAG, the queues, the workers and the autoscaler together."""

import pytest

from blackfish.pipelines import run_local
from blackfish.pipelines.backends.local import ThreadBackend
from blackfish.pipelines.coordinator import Coordinator
from blackfish.pipelines.example import build_pipeline
from blackfish.pipelines.payload import PayloadStore
from blackfish.pipelines.spec import Cardinality, JobSpec, Pipeline
from blackfish.pipelines.store import TaskStore

from . import jobs

JOBS = "tests.unit.pipelines.jobs"

pytestmark = pytest.mark.anyio

DOCUMENTS = [
    "the quick brown fox\njumps over the lazy dog",
    "a brown dog\nand a quick fox",
    "the fox is quick\n\nthe dog is lazy",
]


@pytest.fixture(autouse=True)
def _reset_job_state():
    jobs.reset()
    yield
    jobs.reset()


class TestWorkedExample:
    async def test_the_example_pipeline_produces_the_right_counts(self, tmp_path):
        status, results = await run_local(
            build_pipeline(max_workers=3), DOCUMENTS, root=tmp_path, timeout=30
        )
        assert status.complete
        assert results == [
            {
                "quick": 3,
                "brown": 2,
                "fox": 3,
                "jumps": 1,
                "over": 1,
                "lazy": 2,
                "dog": 3,
            }
        ]

    async def test_all_three_cardinalities_move_the_expected_task_counts(
        self, tmp_path
    ):
        status, _ = await run_local(
            build_pipeline(max_workers=2), DOCUMENTS, root=tmp_path, timeout=30
        )
        assert status.job("read").done == 3, "one task per document"
        assert status.job("count").done == 6, "one task per non-empty line"
        assert status.job("merge").seen == 9, "six lines plus the folded partials"
        assert status.dead_letters == 0

    async def test_a_single_worker_gives_the_same_answer(self, tmp_path):
        """Concurrency must not change the result of a commutative fold."""
        _, parallel = await run_local(
            build_pipeline(max_workers=4), DOCUMENTS, root=tmp_path / "p", timeout=30
        )
        _, serial = await run_local(
            build_pipeline(max_workers=1), DOCUMENTS, root=tmp_path / "s", timeout=30
        )
        assert parallel == serial

    async def test_an_empty_input_completes_without_output(self, tmp_path):
        status, results = await run_local(
            build_pipeline(), [], root=tmp_path, timeout=30
        )
        assert status.complete
        assert results == []


class TestFanIn:
    async def test_a_diamond_joins_both_branches(self, tmp_path):
        """Both branches must land before the join can be considered finished."""
        pipeline = Pipeline(
            name="diamond",
            jobs=(
                JobSpec(name="src", fn=f"{JOBS}:double", batch_size=2, max_workers=2),
                JobSpec(name="left", fn=f"{JOBS}:double", max_workers=2),
                JobSpec(name="right", fn=f"{JOBS}:double", max_workers=2),
                JobSpec(
                    name="join",
                    fn=f"{JOBS}:total",
                    cardinality=Cardinality.MANY_TO_ONE,
                    batch_size=4,
                    max_workers=2,
                ),
            ),
            edges=(
                ("src", "left"),
                ("src", "right"),
                ("left", "join"),
                ("right", "join"),
            ),
        )
        status, results = await run_local(
            pipeline, [1, 2, 3], root=tmp_path, timeout=30
        )
        assert status.complete
        # Each input is doubled by src, then again by each branch, and both
        # branches feed the join: 2 * (4 + 8 + 12) = 48.
        assert results == [48]


class TestUnsealedSources:
    async def test_a_run_with_an_unsealed_source_does_not_complete(self, tmp_path):
        """An empty queue and a slow producer are indistinguishable."""
        pipeline = Pipeline(
            name="stream", jobs=(JobSpec(name="a", fn=f"{JOBS}:double"),)
        )
        store = TaskStore(tmp_path / "p.db")
        payloads = PayloadStore(tmp_path / "payloads")
        backend = ThreadBackend(store, payloads, pipeline)
        coordinator = Coordinator(store, payloads, backend, tick_seconds=0.01)
        run_id = coordinator.start_run(pipeline, [1], seal=False)
        try:
            with pytest.raises(TimeoutError, match="did not complete"):
                await coordinator.run_until_complete(run_id, timeout=0.5)
        finally:
            await backend.shutdown(run_id)
            store.close()

    async def test_inputs_can_arrive_after_the_run_starts(self, tmp_path):
        pipeline = Pipeline(
            name="stream",
            jobs=(JobSpec(name="a", fn=f"{JOBS}:double", max_workers=2),),
        )
        store = TaskStore(tmp_path / "p.db")
        payloads = PayloadStore(tmp_path / "payloads")
        backend = ThreadBackend(store, payloads, pipeline)
        coordinator = Coordinator(store, payloads, backend, tick_seconds=0.01)
        run_id = coordinator.start_run(pipeline, [1], seal=False)
        try:
            await coordinator.tick(run_id)
            coordinator.submit(run_id, "a", [2, 3])
            coordinator.seal(run_id, "a")
            status = await coordinator.run_until_complete(run_id, timeout=30)
            assert status.complete
            assert sorted(coordinator.results(run_id)) == [2, 4, 6]
        finally:
            await backend.shutdown(run_id)
            store.close()


class TestRecovery:
    async def test_work_lost_to_a_dead_worker_is_redelivered(self, tmp_path):
        """A preempted allocation leaves tasks leased; nothing else recovers them."""
        pipeline = Pipeline(
            name="p",
            jobs=(JobSpec(name="a", fn=f"{JOBS}:double", lease_seconds=1),),
        )
        now = {"t": 1000.0}
        store = TaskStore(tmp_path / "p.db", clock=lambda: now["t"])
        payloads = PayloadStore(tmp_path / "payloads")
        backend = ThreadBackend(store, payloads, pipeline)
        coordinator = Coordinator(store, payloads, backend, tick_seconds=0.01)
        run_id = coordinator.start_run(pipeline, [1, 2])

        # A worker that never comes back: it holds the lease and vanishes.
        store.lease(run_id, "a", 2, 1, "doomed-worker")
        assert store.job_status(run_id, "a").leased == 2

        try:
            now["t"] += 60
            status = await coordinator.run_until_complete(run_id, timeout=30)
            assert status.complete
            assert sorted(coordinator.results(run_id)) == [2, 4]
        finally:
            await backend.shutdown(run_id)
            store.close()

    async def test_a_poison_task_is_dead_lettered_and_the_run_still_finishes(
        self, tmp_path
    ):
        pipeline = Pipeline(
            name="p",
            jobs=(JobSpec(name="a", fn=f"{JOBS}:explode", max_attempts=2),),
        )
        store = TaskStore(tmp_path / "p.db")
        payloads = PayloadStore(tmp_path / "payloads")
        backend = ThreadBackend(store, payloads, pipeline)
        coordinator = Coordinator(store, payloads, backend, tick_seconds=0.01)
        run_id = coordinator.start_run(pipeline, [1])
        try:
            status = await coordinator.run_until_complete(run_id, timeout=30)
            assert status.complete
            assert status.dead_letters == 1
            assert "model went sideways" in coordinator.dead_letters(run_id)[0][2]
        finally:
            await backend.shutdown(run_id)
            store.close()


class TestCoordinator:
    async def test_a_completed_run_releases_every_worker(self, tmp_path):
        pipeline = Pipeline(
            name="p",
            jobs=(JobSpec(name="a", fn=f"{JOBS}:double", max_workers=3),),
        )
        store = TaskStore(tmp_path / "p.db")
        payloads = PayloadStore(tmp_path / "payloads")
        backend = ThreadBackend(store, payloads, pipeline)
        coordinator = Coordinator(store, payloads, backend, tick_seconds=0.01)
        run_id = coordinator.start_run(pipeline, [1, 2, 3])
        await coordinator.run_until_complete(run_id, timeout=30)
        assert await backend.count(run_id, "a") == 0
        store.close()

    async def test_cancelling_stops_workers_but_keeps_the_work_done(self, tmp_path):
        pipeline = Pipeline(name="p", jobs=(JobSpec(name="a", fn=f"{JOBS}:double"),))
        store = TaskStore(tmp_path / "p.db")
        payloads = PayloadStore(tmp_path / "payloads")
        backend = ThreadBackend(store, payloads, pipeline)
        coordinator = Coordinator(store, payloads, backend, tick_seconds=0.01)
        run_id = coordinator.start_run(pipeline, [1, 2, 3])
        await coordinator.cancel(run_id)
        assert await backend.count(run_id, "a") == 0
        assert store.run_status(run_id).state == "cancelled"
        store.close()

    async def test_inputs_for_a_non_source_job_are_rejected(self, tmp_path):
        pipeline = Pipeline(
            name="p",
            jobs=(
                JobSpec(name="a", fn=f"{JOBS}:double"),
                JobSpec(name="b", fn=f"{JOBS}:double"),
            ),
            edges=(("a", "b"),),
        )
        store = TaskStore(":memory:")
        coordinator = Coordinator(
            store,
            PayloadStore(tmp_path),
            ThreadBackend(store, PayloadStore(tmp_path), pipeline),
        )
        with pytest.raises(ValueError, match="non-source job"):
            coordinator.start_run(pipeline, {"b": [1]})
        store.close()

    async def test_a_multi_source_pipeline_needs_inputs_per_job(self, tmp_path):
        pipeline = Pipeline(
            name="p",
            jobs=(
                JobSpec(name="a", fn=f"{JOBS}:double"),
                JobSpec(name="b", fn=f"{JOBS}:double"),
                JobSpec(name="c", fn=f"{JOBS}:double"),
            ),
            edges=(("a", "c"), ("b", "c")),
        )
        store = TaskStore(":memory:")
        coordinator = Coordinator(
            store,
            PayloadStore(tmp_path),
            ThreadBackend(store, PayloadStore(tmp_path), pipeline),
        )
        with pytest.raises(ValueError, match="2 source jobs"):
            coordinator.start_run(pipeline, [1, 2])
        store.close()
