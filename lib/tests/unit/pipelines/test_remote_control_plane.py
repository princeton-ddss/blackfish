"""Running the control plane away from the machine that holds the queue.

The coordinator does two jobs with different availability requirements: serving
leases to workers, which must be always up and reachable from compute nodes,
and owning the DAG and scaling decisions, which can tolerate being away. These
tests exercise the second half running over HTTP against the first --
a workstation driving a run whose queue and workers live on a cluster.
"""

import json

import httpx
import pytest

from blackfish.pipelines.api import QueueAPI
from blackfish.pipelines.backends.local import ThreadBackend
from blackfish.pipelines.client import HttpStoreClient
from blackfish.pipelines.coordinator import Coordinator
from blackfish.pipelines.payload import PayloadStore, PayloadTooLarge
from blackfish.pipelines.spec import Cardinality, JobSpec, Pipeline
from blackfish.pipelines.store import RunState, TaskStore

from . import jobs

JOBS = "tests.unit.pipelines.jobs"

pytestmark = pytest.mark.anyio


def api_transport(store: TaskStore) -> httpx.MockTransport:
    """Route HTTP calls onto a real :class:`QueueAPI`.

    Doubles as a statement of the wire protocol: everything the control plane
    needs is these eight paths.
    """
    api = QueueAPI(store)

    def handle(request: httpx.Request) -> httpx.Response:
        parts = request.url.path.strip("/").split("/")
        body = json.loads(request.content) if request.content else {}

        if parts == ["pipelines", "runs"]:
            return httpx.Response(201, json=api.create_run(body))
        if parts == ["pipelines", "reclaim"]:
            return httpx.Response(200, json=api.reclaim(None))

        run_id = parts[2]
        tail = parts[3:]
        if tail == ["spec"]:
            return httpx.Response(200, json=api.spec(run_id))
        if tail == ["status"]:
            return httpx.Response(200, json=api.status(run_id))
        if tail == ["results"]:
            return httpx.Response(
                200, json=api.results(run_id, request.url.params.get("job"))
            )
        if tail == ["dead-letters"]:
            return httpx.Response(200, json=api.dead_letters(run_id))
        if tail == ["reclaim"]:
            return httpx.Response(200, json=api.reclaim(run_id))
        if tail == ["state"]:
            return httpx.Response(200, json=api.set_state(run_id, body))

        job, action = tail[1], tail[2]
        dispatch = {
            "submit": lambda: api.submit(run_id, job, body),
            "seal": lambda: api.seal(run_id, job),
            "lease": lambda: api.lease(run_id, job, body),
            "complete": lambda: api.complete(run_id, job, body),
            "fold": lambda: api.fold(run_id, job, body),
            "release": lambda: api.release(run_id, job, body),
            "fail": lambda: api.fail(run_id, job, body),
            "finalize": lambda: api.finalize(run_id, job, body),
        }
        return httpx.Response(200, json=dispatch[action]())

    return httpx.MockTransport(handle)


def pipeline() -> Pipeline:
    return Pipeline(
        name="remote",
        jobs=(
            JobSpec(name="a", fn=f"{JOBS}:double", batch_size=2, max_workers=2),
            JobSpec(
                name="r",
                fn=f"{JOBS}:total",
                cardinality=Cardinality.MANY_TO_ONE,
                batch_size=4,
            ),
        ),
        edges=(("a", "r"),),
    )


@pytest.fixture(autouse=True)
def _reset_job_state():
    jobs.reset()
    yield
    jobs.reset()


@pytest.fixture
def store(tmp_path) -> TaskStore:
    with TaskStore(tmp_path / "p.db") as store:
        yield store


@pytest.fixture
def remote(store) -> HttpStoreClient:
    """A control plane that reaches the queue only over HTTP."""
    with HttpStoreClient(
        "http://login-node:8000", transport=api_transport(store)
    ) as client:
        yield client


class TestControlPlaneOperations:
    def test_a_run_can_be_created_remotely(self, remote, store):
        run_id = remote.create_run(pipeline())
        assert store.get_pipeline(run_id) == pipeline()

    def test_an_explicit_run_id_is_honoured(self, remote):
        assert remote.create_run(pipeline(), run_id="chosen") == "chosen"

    def test_inputs_can_be_submitted_remotely(self, remote, store):
        run_id = remote.create_run(pipeline())
        assert remote.submit(run_id, "a", ["inline:1", "inline:2"]) == 2
        assert store.job_status(run_id, "a").ready == 2

    def test_keys_still_dedupe_over_the_wire(self, remote):
        run_id = remote.create_run(pipeline())
        assert remote.submit(run_id, "a", ["inline:1"], keys=["/data/x"]) == 1
        assert remote.submit(run_id, "a", ["inline:1"], keys=["/data/x"]) == 0

    def test_sealing_works_remotely(self, remote, store):
        run_id = remote.create_run(pipeline())
        remote.seal(run_id, "a")
        assert store.job_status(run_id, "a").sealed

    def test_run_status_round_trips_every_field(self, remote, store):
        run_id = remote.create_run(pipeline())
        remote.submit(run_id, "a", ["inline:1"])
        remote_status = remote.run_status(run_id)
        assert remote_status == store.run_status(run_id)

    def test_reclaiming_expired_leases_works_remotely(self, tmp_path):
        """The one tick action that must keep happening for a run to progress."""
        now = {"t": 1000.0}
        with TaskStore(tmp_path / "p.db", clock=lambda: now["t"]) as store:
            with HttpStoreClient(
                "http://login-node", transport=api_transport(store)
            ) as remote:
                run_id = remote.create_run(pipeline())
                remote.submit(run_id, "a", ["inline:1"])
                store.lease(run_id, "a", 1, 60, "worker")
                now["t"] += 61
                assert remote.reclaim_expired(run_id) == 1

    def test_reclaim_can_sweep_every_run_remotely(self, tmp_path):
        now = {"t": 1000.0}
        with TaskStore(tmp_path / "p.db", clock=lambda: now["t"]) as store:
            with HttpStoreClient(
                "http://login-node", transport=api_transport(store)
            ) as remote:
                run_id = remote.create_run(pipeline())
                remote.submit(run_id, "a", ["inline:1"])
                store.lease(run_id, "a", 1, 60, "worker")
                now["t"] += 61
                assert remote.reclaim_expired() == 1

    def test_run_state_can_be_set_remotely(self, remote, store):
        run_id = remote.create_run(pipeline())
        remote.set_run_state(run_id, RunState.CANCELLED)
        assert store.run_status(run_id).state is RunState.CANCELLED

    def test_results_and_dead_letters_come_back(self, remote, store):
        run_id = remote.create_run(pipeline())
        store.submit(run_id, "a", ["inline:1", "inline:2"])
        first, second = store.lease(run_id, "a", 2, 60, "w")
        store.complete_batch(
            run_id, "a", {first.task_id: ["inline:out"]}, [], record_results=True
        )
        store.fail_batch(run_id, "a", [second.task_id], "boom", 1)

        assert remote.results(run_id) == ("inline:out",)
        assert remote.results(run_id, "a") == ("inline:out",)
        assert remote.dead_letters(run_id) == (("a", second.task_id, "boom"),)


class TestARunDrivenEntirelyOverHttp:
    """The whole point: control plane off the cluster, queue and workers on it."""

    async def test_a_complete_run_with_a_remote_coordinator(self, store, tmp_path):
        # The control plane sees no shared filesystem, so it may not spill.
        control_payloads = PayloadStore(allow_spill=False)
        # The workers do, and reach the queue directly.
        worker_payloads = PayloadStore(tmp_path / "payloads")

        spec = pipeline()
        backend = ThreadBackend(store, worker_payloads, spec)
        with HttpStoreClient(
            "http://login-node:8000", transport=api_transport(store)
        ) as remote:
            coordinator = Coordinator(
                remote, control_payloads, backend, tick_seconds=0.01
            )
            run_id = coordinator.start_run(spec, [1, 2, 3, 4])
            try:
                status = await coordinator.run_until_complete(run_id, timeout=60)
                assert status.complete
                assert status.dead_letters == 0
                assert coordinator.results(run_id) == [20]
            finally:
                await backend.shutdown(run_id)

    async def test_the_remote_coordinator_scales_workers(self, store, tmp_path):
        spec = pipeline()
        backend = ThreadBackend(store, PayloadStore(tmp_path / "p"), spec)
        with HttpStoreClient(
            "http://login-node:8000", transport=api_transport(store)
        ) as remote:
            coordinator = Coordinator(
                remote, PayloadStore(allow_spill=False), backend, tick_seconds=0.01
            )
            run_id = coordinator.start_run(spec, [1, 2, 3, 4])
            try:
                await coordinator.tick(run_id)
                assert await backend.count(run_id, "a") > 0
                await coordinator.run_until_complete(run_id, timeout=60)
                assert await backend.count(run_id, "a") == 0
            finally:
                await backend.shutdown(run_id)

    async def test_a_payload_the_control_plane_cannot_store_fails_loudly(
        self, store, tmp_path
    ):
        """Better a clear error at submit than a file no worker can read."""
        spec = pipeline()
        backend = ThreadBackend(store, PayloadStore(tmp_path / "p"), spec)
        with HttpStoreClient(
            "http://login-node:8000", transport=api_transport(store)
        ) as remote:
            coordinator = Coordinator(
                remote,
                PayloadStore(inline_max_bytes=16, allow_spill=False),
                backend,
            )
            with pytest.raises(PayloadTooLarge, match="pass its path instead"):
                coordinator.start_run(spec, ["x" * 200])
