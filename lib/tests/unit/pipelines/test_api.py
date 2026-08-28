"""The worker-facing queue API, over both HTTP and the client that speaks it.

Workers on a compute node reach the coordinator only through this API, so the
wire format is a contract: the client's requests must be exactly what the
handlers read, and the handlers' replies exactly what the client parses. These
tests drive both halves against a real store.
"""

import json

import httpx
import pytest
from litestar import Litestar
from litestar.testing import TestClient

from blackfish.pipelines.api import QueueAPI, create_pipeline_router
from blackfish.pipelines.client import HttpQueueClient
from blackfish.pipelines.spec import Cardinality, JobSpec, Pipeline
from blackfish.pipelines.store import TaskStore


def pipeline() -> Pipeline:
    return Pipeline(
        name="linear",
        jobs=(
            JobSpec(name="a", fn="m:a"),
            JobSpec(
                name="r",
                fn="m:r",
                cardinality=Cardinality.MANY_TO_ONE,
                batch_size=2,
            ),
        ),
        edges=(("a", "r"),),
    )


@pytest.fixture
def store() -> TaskStore:
    with TaskStore(":memory:") as store:
        yield store


@pytest.fixture
def run(store) -> str:
    return store.create_run(pipeline())


@pytest.fixture
def client(store) -> HttpQueueClient:
    """An HTTP client wired to the real API through an in-memory transport."""
    api = QueueAPI(store)
    routes = {
        "lease": api.lease,
        "complete": api.complete,
        "fold": api.fold,
        "release": api.release,
        "fail": api.fail,
        "finalize": api.finalize,
    }

    def handle(request: httpx.Request) -> httpx.Response:
        parts = request.url.path.strip("/").split("/")
        if parts[-1] == "spec":
            return httpx.Response(200, json=api.spec(parts[2]))
        if parts[-1] == "status":
            return httpx.Response(200, json=api.status(parts[2]))
        _, _, run_id, _, job, action = parts
        body = json.loads(request.content or b"{}")
        return httpx.Response(200, json=routes[action](run_id, job, body))

    with HttpQueueClient(
        "http://coordinator", transport=httpx.MockTransport(handle)
    ) as client:
        yield client


class TestClientOverHttp:
    def test_fetches_the_pipeline_spec(self, client, run):
        assert client.get_pipeline(run) == pipeline()

    def test_leases_and_completes_a_batch(self, client, store, run):
        store.submit(run, "a", ["inline:1", "inline:2"])
        tasks = client.lease(run, "a", 2, 60, "worker-1")
        assert [task.payload for task in tasks] == ["inline:1", "inline:2"]
        settled = client.complete_batch(
            run, "a", {task.task_id: ["inline:out"] for task in tasks}, ["r"]
        )
        assert settled == 2
        assert store.job_status(run, "r").ready == 2

    def test_lease_carries_the_attempt_count(self, client, store, run):
        store.submit(run, "a", ["inline:1"])
        assert client.lease(run, "a", 1, 60, "w")[0].attempts == 1

    def test_an_empty_queue_returns_no_tasks(self, client, run):
        assert client.lease(run, "a", 4, 60, "w") == ()

    def test_records_sink_results(self, client, store, run):
        store.submit(run, "a", ["inline:1"])
        task = client.lease(run, "a", 1, 60, "w")[0]
        client.complete_batch(
            run, "a", {task.task_id: ["inline:out"]}, [], record_results=True
        )
        assert store.results(run) == ("inline:out",)

    def test_folds_a_reduce_batch(self, client, store, run):
        store.submit(run, "r", ["inline:1", "inline:2"])
        tasks = client.lease(run, "r", 2, 60, "w")
        assert client.fold_batch(run, "r", [t.task_id for t in tasks], "inline:3") == 2
        assert store.job_status(run, "r").ready == 1

    def test_finalizes_a_reduce(self, client, store, run):
        store.seal(run, "a")
        store.submit(run, "r", ["inline:total"])
        task = client.lease(run, "r", 1, 60, "w")[0]
        assert client.finalize_reduce(run, "r", task.task_id, [], record_results=True)
        assert store.results(run) == ("inline:total",)

    def test_refuses_to_finalize_while_upstream_is_live(self, client, store, run):
        store.submit(run, "r", ["inline:partial"])
        task = client.lease(run, "r", 1, 60, "w")[0]
        assert not client.finalize_reduce(run, "r", task.task_id, [])

    def test_releases_a_task_without_spending_an_attempt(self, client, store, run):
        store.submit(run, "a", ["inline:1"])
        task = client.lease(run, "a", 1, 60, "w")[0]
        client.release(run, "a", [task.task_id])
        assert client.lease(run, "a", 1, 60, "w")[0].attempts == task.attempts

    def test_reports_retries_and_dead_letters(self, client, store, run):
        store.submit(run, "a", ["inline:1"])
        task = client.lease(run, "a", 1, 60, "w")[0]
        assert client.fail_batch(run, "a", [task.task_id], "boom", 3) == (1, 0)
        task = client.lease(run, "a", 1, 60, "w")[0]
        assert client.fail_batch(run, "a", [task.task_id], "boom", 1) == (0, 1)


class TestRetries:
    def test_a_transient_failure_is_retried(self, store, run, monkeypatch):
        """A worker that has loaded a model must not die over one bad reply."""
        monkeypatch.setattr("blackfish.pipelines.client.DEFAULT_BACKOFF_SECONDS", 0)
        attempts = {"n": 0}
        api = QueueAPI(store)

        def handle(request: httpx.Request) -> httpx.Response:
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise httpx.ConnectError("connection refused")
            return httpx.Response(200, json=api.spec(run))

        with HttpQueueClient(
            "http://coordinator", transport=httpx.MockTransport(handle)
        ) as client:
            assert client.get_pipeline(run) == pipeline()
        assert attempts["n"] == 3

    def test_a_server_error_is_retried_then_raised(self, store, run, monkeypatch):
        monkeypatch.setattr("blackfish.pipelines.client.DEFAULT_BACKOFF_SECONDS", 0)
        calls = {"n": 0}

        def handle(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return httpx.Response(503, json={"detail": "unavailable"})

        with HttpQueueClient(
            "http://coordinator",
            transport=httpx.MockTransport(handle),
            max_retries=3,
        ) as client:
            with pytest.raises(httpx.HTTPStatusError):
                client.get_pipeline(run)
        assert calls["n"] == 3


class TestLitestarRoutes:
    @pytest.fixture
    def app(self, store) -> Litestar:
        return Litestar(route_handlers=[create_pipeline_router(store)])

    def test_serves_the_pipeline_spec(self, app, run):
        with TestClient(app=app) as client:
            response = client.get(f"/pipelines/runs/{run}/spec")
        assert response.status_code == 200
        assert Pipeline.from_dict(response.json()) == pipeline()

    def test_reports_run_status(self, app, store, run):
        store.submit(run, "a", ["inline:1"])
        with TestClient(app=app) as client:
            body = client.get(f"/pipelines/runs/{run}/status").json()
        assert body["complete"] is False
        assert [job["job"] for job in body["jobs"]] == ["a", "r"]
        assert body["jobs"][0]["ready"] == 1

    def test_leases_over_the_wire(self, app, store, run):
        store.submit(run, "a", ["inline:1"])
        with TestClient(app=app) as client:
            body = client.post(
                f"/pipelines/runs/{run}/jobs/a/lease",
                json={"max_tasks": 4, "lease_seconds": 60, "owner": "w"},
            ).json()
        assert len(body["tasks"]) == 1
        assert body["tasks"][0]["payload"] == "inline:1"

    def test_an_unknown_run_is_a_404(self, app):
        with TestClient(app=app) as client:
            assert client.get("/pipelines/runs/nope/spec").status_code == 404
