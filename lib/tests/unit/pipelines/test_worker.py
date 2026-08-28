import pytest

from blackfish.pipelines.client import QueueUnavailable
from blackfish.pipelines.payload import PayloadStore
from blackfish.pipelines.spec import Cardinality, JobSpec, Pipeline
from blackfish.pipelines.store import TaskStore, cardinality_check
from blackfish.pipelines.worker import Worker, resolve

from . import jobs

JOBS = "tests.unit.pipelines.jobs"


@pytest.fixture(autouse=True)
def _reset_job_state():
    jobs.reset()
    yield
    jobs.reset()


@pytest.fixture
def payloads(tmp_path) -> PayloadStore:
    return PayloadStore(tmp_path)


class Clock:
    """A hand-cranked clock, so retry backoff is testable without sleeping."""

    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def store(clock) -> TaskStore:
    with TaskStore(":memory:", clock=clock) as store:
        yield store


def make_worker(store, payloads, spec: JobSpec, downstream: JobSpec | None = None):
    specs = (spec,) if downstream is None else (spec, downstream)
    edges = () if downstream is None else ((spec.name, downstream.name),)
    pipeline = Pipeline(name="p", jobs=specs, edges=edges)
    run_id = store.create_run(pipeline)
    worker = Worker(
        run_id=run_id,
        pipeline=pipeline,
        job=spec,
        client=store,
        payloads=payloads,
        owner="test-worker",
        idle_timeout=None,
    )
    return run_id, worker


class TestResolve:
    def test_imports_an_attribute(self):
        assert resolve(f"{JOBS}:double") is jobs.double

    def test_rejects_a_path_without_a_colon(self):
        with pytest.raises(ValueError, match="module:attribute"):
            resolve("blackfish.pipelines")

    def test_reports_a_missing_attribute(self):
        with pytest.raises(AttributeError, match="no attribute 'nope'"):
            resolve(f"{JOBS}:nope")

    def test_reports_a_missing_module(self):
        with pytest.raises(ImportError):
            resolve("no.such.module:thing")


class TestSetup:
    def test_setup_runs_once_no_matter_how_many_batches(self, store, payloads):
        """The whole point: weights are loaded per worker, not per task."""
        spec = JobSpec(
            name="a", fn=f"{JOBS}:scale", setup=f"{JOBS}:load_model", batch_size=2
        )
        run_id, worker = make_worker(store, payloads, spec)
        store.submit(run_id, "a", [payloads.put(i) for i in range(6)])
        while worker.run_once():
            pass
        assert jobs.SETUP_CALLS == 1
        assert worker.batches == 3

    def test_a_job_without_setup_is_called_with_only_the_batch(self, store, payloads):
        spec = JobSpec(name="a", fn=f"{JOBS}:double", batch_size=4)
        run_id, worker = make_worker(store, payloads, spec)
        store.submit(run_id, "a", [payloads.put(i) for i in range(3)])
        assert worker.run_once()
        assert jobs.SETUP_CALLS == 0


class TestBatching:
    def test_a_worker_takes_up_to_batch_size_per_call(self, store, payloads):
        spec = JobSpec(name="a", fn=f"{JOBS}:double", batch_size=4)
        run_id, worker = make_worker(store, payloads, spec)
        store.submit(run_id, "a", [payloads.put(i) for i in range(10)])
        while worker.run_once():
            pass
        assert jobs.BATCH_SIZES == [4, 4, 2]

    def test_an_empty_queue_reports_no_work(self, store, payloads):
        spec = JobSpec(name="a", fn=f"{JOBS}:double")
        _run_id, worker = make_worker(store, payloads, spec)
        assert worker.run_once() is False


class TestCardinalitySemantics:
    def test_one_to_one_emits_one_task_per_input(self, store, payloads):
        spec = JobSpec(name="a", fn=f"{JOBS}:double", batch_size=4)
        sink = JobSpec(name="b", fn=f"{JOBS}:double")
        run_id, worker = make_worker(store, payloads, spec, sink)
        store.submit(run_id, "a", [payloads.put(i) for i in range(3)])
        worker.run_once()
        assert store.job_status(run_id, "b").ready == 3

    def test_one_to_many_emits_a_group_per_input(self, store, payloads):
        spec = JobSpec(
            name="a",
            fn=f"{JOBS}:fan_out",
            cardinality=Cardinality.ONE_TO_MANY,
            batch_size=4,
        )
        sink = JobSpec(name="b", fn=f"{JOBS}:double")
        run_id, worker = make_worker(store, payloads, spec, sink)
        store.submit(run_id, "a", [payloads.put(i) for i in (1, 2, 3)])
        worker.run_once()
        assert store.job_status(run_id, "b").ready == 1 + 2 + 3

    def test_a_one_to_one_job_returning_the_wrong_count_fails_the_batch(
        self, store, payloads
    ):
        spec = JobSpec(
            name="a", fn=f"{JOBS}:wrong_length", batch_size=4, max_attempts=1
        )
        run_id, worker = make_worker(store, payloads, spec)
        store.submit(run_id, "a", [payloads.put(i) for i in range(3)])
        worker.run_once()
        errors = store.dead_letters(run_id)
        assert len(errors) == 3
        assert "one output per input" in errors[0][2]

    def test_a_one_to_many_job_returning_a_flat_list_fails_the_batch(
        self, store, payloads
    ):
        spec = JobSpec(
            name="a",
            fn=f"{JOBS}:flat_instead_of_nested",
            cardinality=Cardinality.ONE_TO_MANY,
            max_attempts=1,
        )
        run_id, worker = make_worker(store, payloads, spec)
        store.submit(run_id, "a", [payloads.put(1)])
        worker.run_once()
        assert "Wrap single values in a list" in store.dead_letters(run_id)[0][2]


class TestFailureHandling:
    def test_a_raising_job_retries_its_batch(self, store, payloads):
        spec = JobSpec(name="a", fn=f"{JOBS}:explode", max_attempts=3)
        run_id, worker = make_worker(store, payloads, spec)
        store.submit(run_id, "a", [payloads.put(1)])
        worker.run_once()
        assert store.job_status(run_id, "a").ready == 1

    def test_a_transient_failure_succeeds_on_retry(self, store, payloads, clock):
        spec = JobSpec(name="a", fn=f"{JOBS}:flaky", max_attempts=3, retry_backoff=5.0)
        sink = JobSpec(name="b", fn=f"{JOBS}:double")
        run_id, worker = make_worker(store, payloads, spec, sink)
        store.submit(run_id, "a", [payloads.put(7)])

        worker.run_once()
        assert worker.run_once() is False, "retried before its backoff elapsed"

        clock.advance(5.0)
        assert worker.run_once() is True
        assert store.job_status(run_id, "b").ready == 1

    def test_a_failed_task_is_held_for_its_backoff(self, store, payloads, clock):
        """Otherwise a rate-limited job spends its whole budget instantly."""
        spec = JobSpec(
            name="a", fn=f"{JOBS}:explode", max_attempts=5, retry_backoff=10.0
        )
        run_id, worker = make_worker(store, payloads, spec)
        store.submit(run_id, "a", [payloads.put(1)])
        worker.run_once()

        status = store.job_status(run_id, "a")
        assert status.ready == 1, "still outstanding"
        assert status.delayed == 1, "but not leasable"
        assert status.backlog == 0, "so the autoscaler sees no work to do"

        clock.advance(10.0)
        assert store.job_status(run_id, "a").backlog == 1

    def test_the_backoff_doubles_with_each_attempt(self, store, payloads, clock):
        spec = JobSpec(
            name="a", fn=f"{JOBS}:explode", max_attempts=5, retry_backoff=1.0
        )
        run_id, worker = make_worker(store, payloads, spec)
        store.submit(run_id, "a", [payloads.put(1)])

        for expected in (1.0, 2.0, 4.0):
            assert worker.run_once() is True
            clock.advance(expected - 0.01)
            assert worker.run_once() is False, f"leasable before {expected}s"
            clock.advance(0.01)

    def test_a_permanently_failing_job_is_dead_lettered(self, store, payloads, clock):
        spec = JobSpec(
            name="a", fn=f"{JOBS}:explode", max_attempts=2, retry_backoff=1.0
        )
        run_id, worker = make_worker(store, payloads, spec)
        store.submit(run_id, "a", [payloads.put(1)])
        for _ in range(4):
            worker.run_once()
            clock.advance(60)
        assert "model went sideways" in store.dead_letters(run_id)[0][2]


class TestReduceWorker:
    def _reduce_worker(self, store, payloads):
        spec = JobSpec(
            name="r",
            fn=f"{JOBS}:total",
            cardinality=Cardinality.MANY_TO_ONE,
            batch_size=2,
        )
        pipeline = Pipeline(name="p", jobs=(spec,))
        run_id = store.create_run(pipeline)
        worker = Worker(
            run_id=run_id,
            pipeline=pipeline,
            job=spec,
            client=store,
            payloads=payloads,
            idle_timeout=None,
        )
        return run_id, worker

    def test_folds_until_one_value_remains(self, store, payloads):
        run_id, worker = self._reduce_worker(store, payloads)
        store.submit(run_id, "r", [payloads.put(i) for i in range(1, 5)])
        store.seal(run_id, "r")
        while worker.run_once():
            pass
        assert [payloads.get(ref) for ref in store.results(run_id)] == [10]

    def test_a_lone_partial_is_put_back_while_more_input_may_arrive(
        self, store, payloads
    ):
        """Folding one value returns it unchanged; the worker must not spin."""
        run_id, worker = self._reduce_worker(store, payloads)
        store.submit(run_id, "r", [payloads.put(1)])
        assert worker.run_once() is False
        status = store.job_status(run_id, "r")
        assert (status.ready, status.done) == (1, 0)

    def test_putting_a_partial_back_does_not_spend_an_attempt(self, store, payloads):
        run_id, worker = self._reduce_worker(store, payloads)
        store.submit(run_id, "r", [payloads.put(1)])
        for _ in range(5):
            worker.run_once()
        assert store.dead_letters(run_id) == ()


class TestCardinalityCheck:
    def test_rejects_a_scalar_from_a_one_to_one_job(self):
        with pytest.raises(ValueError, match="must return a sequence"):
            cardinality_check(Cardinality.ONE_TO_ONE, [1], 42)

    def test_rejects_a_string_masquerading_as_a_sequence(self):
        with pytest.raises(ValueError, match="must return a sequence"):
            cardinality_check(Cardinality.ONE_TO_ONE, [1], "ab")

    def test_normalizes_one_to_one_into_groups(self):
        assert cardinality_check(Cardinality.ONE_TO_ONE, [1, 2], ["a", "b"]) == [
            ["a"],
            ["b"],
        ]

    def test_allows_an_empty_group_in_one_to_many(self):
        assert cardinality_check(Cardinality.ONE_TO_MANY, [1], [[]]) == [[]]

    def test_reduce_outputs_are_not_per_input(self):
        with pytest.raises(ValueError, match="not emitted per input"):
            cardinality_check(Cardinality.MANY_TO_ONE, [1, 2], 3)


class TestRunLoop:
    def test_a_worker_exits_after_being_idle(self, store, payloads):
        """Exiting is what frees the allocation; the autoscaler brings it back."""
        spec = JobSpec(name="a", fn=f"{JOBS}:double", batch_size=2)
        run_id, worker = make_worker(store, payloads, spec)
        worker.idle_timeout = 0.05
        worker.poll_seconds = 0.01
        store.submit(run_id, "a", [payloads.put(i) for i in range(4)])
        worker.run()
        assert worker.tasks_processed == 4
        assert store.job_status(run_id, "a").done == 4

    def test_a_worker_stops_when_asked(self, store, payloads):
        import threading

        spec = JobSpec(name="a", fn=f"{JOBS}:double")
        _run_id, worker = make_worker(store, payloads, spec)
        worker.poll_seconds = 0.01
        stop = threading.Event()
        stop.set()
        worker.run(stop)
        assert worker.batches == 0

    def test_a_failing_fold_retries_the_reduce_batch(self, store, payloads):
        spec = JobSpec(
            name="r",
            fn=f"{JOBS}:explode",
            cardinality=Cardinality.MANY_TO_ONE,
            batch_size=2,
            max_attempts=1,
        )
        pipeline = Pipeline(name="p", jobs=(spec,))
        run_id = store.create_run(pipeline)
        worker = Worker(
            run_id=run_id,
            pipeline=pipeline,
            job=spec,
            client=store,
            payloads=payloads,
            idle_timeout=None,
        )
        store.submit(run_id, "r", [payloads.put(1), payloads.put(2)])
        assert worker.run_once() is True
        assert len(store.dead_letters(run_id)) == 2


class TestWorkerEntryPoint:
    def test_requires_exactly_one_coordinator_address(self):
        from blackfish.pipelines.worker import main

        with pytest.raises(SystemExit):
            main(["--run", "r", "--job", "a", "--payloads", "/tmp/p"])

    def test_rejects_both_addresses_at_once(self):
        from blackfish.pipelines.worker import main

        with pytest.raises(SystemExit):
            main(
                [
                    "--run",
                    "r",
                    "--job",
                    "a",
                    "--payloads",
                    "/tmp/p",
                    "--store",
                    "s.db",
                    "--url",
                    "http://x",
                ]
            )


class TestParams:
    """A job is addressed by import path, so ``params`` is how it is configured."""

    def test_setup_receives_params_as_keywords(self, store, payloads):
        spec = JobSpec(
            name="a",
            fn=f"{JOBS}:multiply",
            setup=f"{JOBS}:build_context",
            params={"scale": 5, "label": "prod"},
        )
        run_id, worker = make_worker(store, payloads, spec)
        store.submit(run_id, "a", [payloads.put(3)])
        worker.run_once()
        assert jobs.SETUP_KWARGS == {"scale": 5, "label": "prod"}

    def test_the_context_reaches_the_function(self, store, payloads):
        spec = JobSpec(
            name="a",
            fn=f"{JOBS}:multiply",
            setup=f"{JOBS}:build_context",
            params={"scale": 5},
        )
        sink = JobSpec(name="b", fn=f"{JOBS}:double")
        run_id, worker = make_worker(store, payloads, spec, sink)
        store.submit(run_id, "a", [payloads.put(3)])
        worker.run_once()
        leased = store.lease(run_id, "b", 1, 60, "w")
        assert payloads.get(leased[0].payload) == 15

    def test_params_are_the_context_when_there_is_no_setup(self, store, payloads):
        spec = JobSpec(name="a", fn=f"{JOBS}:multiply", params={"scale": 4})
        run_id, worker = make_worker(store, payloads, spec)
        store.submit(run_id, "a", [payloads.put(2)])
        worker.run_once()
        assert jobs.SEEN_CONTEXT == [{"scale": 4}]
        assert jobs.SETUP_CALLS == 0

    def test_a_job_with_neither_gets_no_context(self, store, payloads):
        spec = JobSpec(name="a", fn=f"{JOBS}:double")
        run_id, worker = make_worker(store, payloads, spec)
        store.submit(run_id, "a", [payloads.put(2)])
        assert worker.run_once()

    def test_a_misspelled_param_fails_at_worker_start(self, store, payloads):
        """Loudly, before any task is leased -- not an hour into the run."""
        spec = JobSpec(
            name="a",
            fn=f"{JOBS}:multiply",
            setup=f"{JOBS}:build_context",
            params={"scal": 5},
        )
        _run_id, worker = make_worker(store, payloads, spec)
        with pytest.raises(TypeError, match="scal"):
            worker.start()


class FlakyClient:
    """Wraps a queue client and simulates the coordinator going away."""

    def __init__(self, inner, fail_calls: int = 0, permanent: bool = False):
        self.inner = inner
        self.remaining = fail_calls
        self.permanent = permanent
        self.outages = 0

    def __getattr__(self, name):
        attr = getattr(self.inner, name)
        if not callable(attr):
            return attr

        def wrapper(*args, **kwargs):
            if self.permanent or self.remaining > 0:
                self.remaining -= 1
                self.outages += 1
                raise QueueUnavailable("simulated outage")
            return attr(*args, **kwargs)

        return wrapper


class TestOutageTolerance:
    """A worker that cannot reach the coordinator should wait, not die.

    It has already paid to load its model and the queue is durable, so holding
    still is the cheapest correct response. A login node reboots; a laptop lid
    closes. Neither should cost a cluster's worth of warm workers.
    """

    @pytest.fixture(autouse=True)
    def _fast_outage_polling(self, monkeypatch):
        monkeypatch.setattr("blackfish.pipelines.worker.OUTAGE_POLL_MIN_SECONDS", 0.001)
        monkeypatch.setattr("blackfish.pipelines.worker.OUTAGE_POLL_MAX_SECONDS", 0.005)

    def _worker(self, store, payloads, client, **kwargs):
        spec = JobSpec(
            name="a", fn=f"{JOBS}:scale", setup=f"{JOBS}:load_model", batch_size=2
        )
        pipeline = Pipeline(name="p", jobs=(spec,))
        run_id = store.create_run(pipeline)
        worker = Worker(
            run_id=run_id,
            pipeline=pipeline,
            job=spec,
            client=client,
            payloads=payloads,
            idle_timeout=0.05,
            poll_seconds=0.001,
            **kwargs,
        )
        return run_id, worker

    def test_a_worker_survives_an_outage_and_keeps_its_model(self, store, payloads):
        client = FlakyClient(store, fail_calls=4)
        run_id, worker = self._worker(store, payloads, client)
        store.submit(run_id, "a", [payloads.put(i) for i in range(4)])

        worker.run()

        assert client.outages == 4, "the outage really happened"
        assert store.job_status(run_id, "a").done == 4, "work finished afterwards"
        assert jobs.SETUP_CALLS == 1, "the model was not reloaded"

    def test_an_outage_does_not_dead_letter_anything(self, store, payloads):
        """An unreachable coordinator is not a failure of the work."""
        client = FlakyClient(store, fail_calls=3)
        run_id, worker = self._worker(store, payloads, client)
        store.submit(run_id, "a", [payloads.put(1)])
        worker.run()
        assert store.dead_letters(run_id) == ()

    def test_a_worker_gives_up_once_the_outage_outlasts_its_patience(
        self, store, payloads
    ):
        """Holding a GPU against a coordinator that is never coming back is worse."""
        client = FlakyClient(store, permanent=True)
        run_id, worker = self._worker(store, payloads, client, max_outage=0.05)
        store.submit(run_id, "a", [payloads.put(1)])

        worker.run()  # returns rather than raising

        assert client.outages > 1
        assert store.job_status(run_id, "a").ready == 1, "work is left for a retry"

    def test_a_worker_waiting_out_an_outage_can_still_be_stopped(self, store, payloads):
        import threading

        client = FlakyClient(store, permanent=True)
        _run_id, worker = self._worker(store, payloads, client, max_outage=None)
        stop = threading.Event()

        def stop_soon():
            while client.outages < 3:
                pass
            stop.set()

        watcher = threading.Thread(target=stop_soon, daemon=True)
        watcher.start()
        worker.run(stop)
        watcher.join(timeout=5)
        assert stop.is_set()

    def test_startup_waits_for_a_coordinator_that_is_not_up_yet(
        self, store, payloads, monkeypatch
    ):
        """An allocation can start while the coordinator is still restarting."""
        from blackfish.pipelines.worker import _fetch_pipeline

        spec = JobSpec(name="a", fn=f"{JOBS}:double")
        pipeline = Pipeline(name="p", jobs=(spec,))
        run_id = store.create_run(pipeline)
        client = FlakyClient(store, fail_calls=2)
        assert _fetch_pipeline(client, run_id, max_outage=5.0) == pipeline
        assert client.outages == 2

    def test_startup_eventually_gives_up(self, store):
        from blackfish.pipelines.worker import _fetch_pipeline

        client = FlakyClient(store, permanent=True)
        with pytest.raises(QueueUnavailable):
            _fetch_pipeline(client, "run", max_outage=0.01)
