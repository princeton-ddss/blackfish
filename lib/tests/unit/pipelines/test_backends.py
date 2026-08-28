import pytest

from blackfish.pipelines.backends.local import SubprocessBackend, ThreadBackend
from blackfish.pipelines.coordinator import Coordinator
from blackfish.pipelines.payload import PayloadStore
from blackfish.pipelines.spec import JobSpec, Pipeline
from blackfish.pipelines.store import TaskStore

from . import jobs

JOBS = "tests.unit.pipelines.jobs"

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def _reset_job_state():
    jobs.reset()
    yield
    jobs.reset()


def one_job_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        name="p",
        jobs=(JobSpec(name="a", fn=f"{JOBS}:double", batch_size=2, **kwargs),),
    )


class TestThreadBackend:
    async def test_scaling_up_starts_workers(self, tmp_path):
        pipeline = one_job_pipeline(max_workers=3)
        store = TaskStore(":memory:")
        backend = ThreadBackend(store, PayloadStore(tmp_path), pipeline)
        run_id = store.create_run(pipeline)
        try:
            await backend.scale(run_id, pipeline.job("a"), 3)
            assert await backend.count(run_id, "a") == 3
        finally:
            await backend.shutdown(run_id)
            store.close()

    async def test_scaling_down_stops_workers(self, tmp_path):
        pipeline = one_job_pipeline(max_workers=3)
        store = TaskStore(":memory:")
        backend = ThreadBackend(store, PayloadStore(tmp_path), pipeline)
        run_id = store.create_run(pipeline)
        try:
            await backend.scale(run_id, pipeline.job("a"), 3)
            await backend.scale(run_id, pipeline.job("a"), 1)
            await backend.shutdown(run_id)
            assert await backend.count(run_id, "a") == 0
        finally:
            store.close()

    async def test_shutdown_is_idempotent(self, tmp_path):
        pipeline = one_job_pipeline()
        store = TaskStore(":memory:")
        backend = ThreadBackend(store, PayloadStore(tmp_path), pipeline)
        run_id = store.create_run(pipeline)
        await backend.scale(run_id, pipeline.job("a"), 1)
        await backend.shutdown(run_id)
        await backend.shutdown(run_id)
        assert await backend.count(run_id, "a") == 0
        store.close()

    async def test_workers_of_other_runs_are_left_alone(self, tmp_path):
        pipeline = one_job_pipeline()
        store = TaskStore(":memory:")
        backend = ThreadBackend(store, PayloadStore(tmp_path), pipeline)
        first = store.create_run(pipeline)
        second = store.create_run(pipeline)
        try:
            await backend.scale(first, pipeline.job("a"), 1)
            await backend.scale(second, pipeline.job("a"), 1)
            await backend.shutdown(first)
            assert await backend.count(second, "a") == 1
        finally:
            await backend.shutdown(second)
            store.close()


class TestSubprocessBackend:
    """The local rehearsal of cluster behaviour: real processes, real polling."""

    async def test_a_worker_process_drains_the_queue(self, tmp_path):
        pipeline = one_job_pipeline(max_workers=1)
        store_path = tmp_path / "pipeline.db"
        payload_dir = tmp_path / "payloads"
        store = TaskStore(store_path)
        payloads = PayloadStore(payload_dir)
        backend = SubprocessBackend(store_path, payload_dir, idle_timeout=2)
        coordinator = Coordinator(store, payloads, backend, tick_seconds=0.1)
        run_id = coordinator.start_run(pipeline, [1, 2, 3, 4])
        try:
            status = await coordinator.run_until_complete(run_id, timeout=60)
            assert status.complete
            assert sorted(coordinator.results(run_id)) == [2, 4, 6, 8]
        finally:
            await backend.shutdown(run_id)
            store.close()

    async def test_shutdown_stops_the_process(self, tmp_path):
        pipeline = one_job_pipeline()
        store_path = tmp_path / "pipeline.db"
        store = TaskStore(store_path)
        backend = SubprocessBackend(store_path, tmp_path / "payloads")
        run_id = store.create_run(pipeline)
        await backend.scale(run_id, pipeline.job("a"), 1)
        assert await backend.count(run_id, "a") == 1
        await backend.shutdown(run_id)
        assert await backend.count(run_id, "a") == 0
        store.close()
