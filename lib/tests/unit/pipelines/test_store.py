"""Tests for the queue substrate: leases, at-least-once delivery, and fan-in.

The fan-in tests are the point of this file. A DAG on top of queues is only
correct if a job can tell when it has seen everything it will ever see, and the
store claims to answer that without sentinels or windowing -- by settling a task
and enqueuing its outputs in one transaction. These tests pin that claim down.
"""

import pytest

from blackfish.pipelines.spec import Cardinality, JobSpec, Pipeline
from blackfish.pipelines.store import TaskState, TaskStore, derive_task_id


class Clock:
    """A hand-cranked clock, so lease expiry is testable without sleeping."""

    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def linear_pipeline() -> Pipeline:
    return Pipeline(
        name="linear",
        jobs=(
            JobSpec(name="a", fn="m:a"),
            JobSpec(name="b", fn="m:b"),
        ),
        edges=(("a", "b"),),
    )


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def store(clock) -> TaskStore:
    with TaskStore(":memory:", clock=clock) as store:
        yield store


@pytest.fixture
def run(store) -> str:
    return store.create_run(linear_pipeline())


class TestSubmitAndLease:
    def test_submitted_tasks_are_ready(self, store, run):
        assert store.submit(run, "a", ["inline:1", "inline:2"]) == 2
        assert store.job_status(run, "a").ready == 2

    def test_lease_hands_out_at_most_the_requested_batch(self, store, run):
        store.submit(run, "a", [f"inline:{i}" for i in range(5)])
        tasks = store.lease(run, "a", 2, 60, "w1")
        assert len(tasks) == 2

    def test_lease_returns_fewer_rather_than_waiting_for_a_full_batch(self, store, run):
        store.submit(run, "a", ["inline:1"])
        assert len(store.lease(run, "a", 8, 60, "w1")) == 1

    def test_a_leased_task_is_invisible_to_other_workers(self, store, run):
        store.submit(run, "a", ["inline:1"])
        first = store.lease(run, "a", 1, 60, "w1")
        second = store.lease(run, "a", 1, 60, "w2")
        assert len(first) == 1
        assert second == ()

    def test_lease_counts_an_attempt(self, store, run):
        store.submit(run, "a", ["inline:1"])
        assert store.lease(run, "a", 1, 60, "w1")[0].attempts == 1

    def test_lease_on_an_empty_queue_returns_nothing(self, store, run):
        assert store.lease(run, "a", 4, 60, "w1") == ()

    def test_rejects_a_zero_sized_lease(self, store, run):
        with pytest.raises(ValueError, match="max_tasks"):
            store.lease(run, "a", 0, 60, "w1")

    def test_keys_make_submission_idempotent(self, store, run):
        """Resubmitting the same input files must not double the work."""
        assert store.submit(run, "a", ["inline:1"], keys=["/data/x.wav"]) == 1
        assert store.submit(run, "a", ["inline:1"], keys=["/data/x.wav"]) == 0
        assert store.job_status(run, "a").ready == 1

    def test_rejects_mismatched_keys(self, store, run):
        with pytest.raises(ValueError, match="same length"):
            store.submit(run, "a", ["inline:1", "inline:2"], keys=["one"])


class TestLeaseExpiry:
    def test_an_expired_lease_is_reclaimed(self, store, run, clock):
        store.submit(run, "a", ["inline:1"])
        store.lease(run, "a", 1, 60, "w1")
        clock.advance(61)
        assert store.reclaim_expired(run) == 1
        assert store.job_status(run, "a").ready == 1

    def test_a_live_lease_is_left_alone(self, store, run, clock):
        store.submit(run, "a", ["inline:1"])
        store.lease(run, "a", 1, 60, "w1")
        clock.advance(59)
        assert store.reclaim_expired(run) == 0

    def test_a_reclaimed_task_keeps_its_attempt_count(self, store, run, clock):
        """A worker that dies repeatedly must not retry forever."""
        store.submit(run, "a", ["inline:1"])
        store.lease(run, "a", 1, 60, "w1")
        clock.advance(61)
        store.reclaim_expired(run)
        assert store.lease(run, "a", 1, 60, "w2")[0].attempts == 2

    def test_reclaim_can_sweep_every_run(self, store, clock):
        first = store.create_run(linear_pipeline())
        second = store.create_run(linear_pipeline())
        for run_id in (first, second):
            store.submit(run_id, "a", ["inline:1"])
            store.lease(run_id, "a", 1, 60, "w1")
        clock.advance(61)
        assert store.reclaim_expired() == 2


class TestCompletion:
    def test_completing_a_task_enqueues_its_output_downstream(self, store, run):
        store.submit(run, "a", ["inline:1"])
        task = store.lease(run, "a", 1, 60, "w1")[0]
        store.complete_batch(run, "a", {task.task_id: ["inline:out"]}, ["b"])
        assert store.job_status(run, "b").ready == 1

    def test_a_one_to_many_task_enqueues_every_output(self, store, run):
        store.submit(run, "a", ["inline:1"])
        task = store.lease(run, "a", 1, 60, "w1")[0]
        store.complete_batch(
            run, "a", {task.task_id: ["inline:x", "inline:y", "inline:z"]}, ["b"]
        )
        assert store.job_status(run, "b").ready == 3

    def test_a_task_producing_nothing_enqueues_nothing(self, store, run):
        store.submit(run, "a", ["inline:1"])
        task = store.lease(run, "a", 1, 60, "w1")[0]
        store.complete_batch(run, "a", {task.task_id: []}, ["b"])
        assert store.job_status(run, "b").ready == 0
        assert store.job_status(run, "a").done == 1

    def test_every_downstream_job_gets_its_own_copy(self, store):
        pipeline = Pipeline(
            name="fanout",
            jobs=(
                JobSpec(name="a", fn="m:a"),
                JobSpec(name="b", fn="m:b"),
                JobSpec(name="c", fn="m:c"),
            ),
            edges=(("a", "b"), ("a", "c")),
        )
        run = store.create_run(pipeline)
        store.submit(run, "a", ["inline:1"])
        task = store.lease(run, "a", 1, 60, "w1")[0]
        store.complete_batch(run, "a", {task.task_id: ["inline:out"]}, ["b", "c"])
        assert store.job_status(run, "b").ready == 1
        assert store.job_status(run, "c").ready == 1

    def test_sink_outputs_are_recorded_as_results(self, store, run):
        store.submit(run, "a", ["inline:1"])
        task = store.lease(run, "a", 1, 60, "w1")[0]
        store.complete_batch(
            run, "a", {task.task_id: ["inline:out"]}, [], record_results=True
        )
        assert store.results(run) == ("inline:out",)

    def test_replaying_a_completed_batch_changes_nothing(self, store, run):
        """The failure a worker cannot see: a commit whose reply was lost."""
        store.submit(run, "a", ["inline:1"])
        task = store.lease(run, "a", 1, 60, "w1")[0]
        outputs = {task.task_id: ["inline:out"]}
        assert store.complete_batch(run, "a", outputs, ["b"]) == 1
        assert store.complete_batch(run, "a", outputs, ["b"]) == 0
        assert store.job_status(run, "b").ready == 1
        assert store.job_status(run, "a").done == 1

    def test_a_retried_task_reuses_its_output_task_ids(self, store, run, clock):
        """A redelivered task must replace its outputs, not add to them."""
        store.submit(run, "a", ["inline:1"])
        first = store.lease(run, "a", 1, 60, "w1")[0]
        clock.advance(61)
        store.reclaim_expired(run)
        second = store.lease(run, "a", 1, 60, "w2")[0]
        assert second.task_id == first.task_id
        store.complete_batch(run, "a", {second.task_id: ["inline:out"]}, ["b"])
        assert store.job_status(run, "b").seen == 1


class TestFailures:
    def test_a_failed_task_is_retried_while_attempts_remain(self, store, run):
        store.submit(run, "a", ["inline:1"])
        task = store.lease(run, "a", 1, 60, "w1")[0]
        retried, dead = store.fail_batch(run, "a", [task.task_id], "boom", 3)
        assert (retried, dead) == (1, 0)
        assert store.job_status(run, "a").ready == 1

    def test_a_task_is_dead_lettered_once_attempts_run_out(self, store, run):
        store.submit(run, "a", ["inline:1"])
        for _ in range(2):
            task = store.lease(run, "a", 1, 60, "w1")[0]
            store.fail_batch(run, "a", [task.task_id], "boom", 3)
        task = store.lease(run, "a", 1, 60, "w1")[0]
        retried, dead = store.fail_batch(run, "a", [task.task_id], "boom", 3)
        assert (retried, dead) == (0, 1)
        assert store.job_status(run, "a").failed == 1

    def test_dead_letters_report_the_last_error(self, store, run):
        store.submit(run, "a", ["inline:1"])
        task = store.lease(run, "a", 1, 60, "w1")[0]
        store.fail_batch(run, "a", [task.task_id], "ValueError: bad shape", 1)
        assert store.dead_letters(run) == (
            ("a", task.task_id, "ValueError: bad shape"),
        )

    def test_a_dead_letter_does_not_block_the_run_forever(self, store, run):
        """A poison task must settle the job, not hold the DAG open."""
        store.submit(run, "a", ["inline:1"])
        store.seal(run, "a")
        task = store.lease(run, "a", 1, 60, "w1")[0]
        store.fail_batch(run, "a", [task.task_id], "boom", 1)
        assert store.run_status(run).complete

    def test_release_returns_a_task_without_spending_an_attempt(self, store, run):
        store.submit(run, "a", ["inline:1"])
        task = store.lease(run, "a", 1, 60, "w1")[0]
        store.release(run, "a", [task.task_id])
        assert store.lease(run, "a", 1, 60, "w2")[0].attempts == task.attempts


class TestFanIn:
    """The completion rule: complete(job) = upstreams complete and drained."""

    def test_an_unsealed_source_is_never_complete(self, store, run):
        """An empty queue and a slow producer look identical from outside."""
        assert not store.run_status(run).job("a").complete

    def test_sealing_an_empty_source_completes_it(self, store, run):
        store.seal(run, "a")
        assert store.run_status(run).job("a").complete

    def test_a_sealed_source_with_work_left_is_not_complete(self, store, run):
        store.submit(run, "a", ["inline:1"])
        store.seal(run, "a")
        assert not store.run_status(run).job("a").complete

    def test_downstream_is_not_complete_while_upstream_still_holds_work(
        self, store, run
    ):
        """The case that breaks naive DAG-on-queue: an empty downstream queue."""
        store.submit(run, "a", ["inline:1"])
        store.seal(run, "a")
        status = store.run_status(run)
        assert status.job("b").ready == 0
        assert not status.job("b").complete

    def test_downstream_is_not_complete_while_upstream_is_mid_batch(self, store, run):
        store.submit(run, "a", ["inline:1"])
        store.seal(run, "a")
        store.lease(run, "a", 1, 60, "w1")
        assert not store.run_status(run).job("b").complete

    def test_upstream_output_is_visible_the_instant_upstream_completes(
        self, store, run
    ):
        """Ack and emit share a transaction, so there is no window between them."""
        store.submit(run, "a", ["inline:1"])
        store.seal(run, "a")
        task = store.lease(run, "a", 1, 60, "w1")[0]
        store.complete_batch(run, "a", {task.task_id: ["inline:out"]}, ["b"])
        status = store.run_status(run)
        assert status.job("a").complete
        assert status.job("b").ready == 1
        assert not status.job("b").complete

    def test_the_whole_chain_completes_when_the_last_task_settles(self, store, run):
        store.submit(run, "a", ["inline:1"])
        store.seal(run, "a")
        task = store.lease(run, "a", 1, 60, "w1")[0]
        store.complete_batch(run, "a", {task.task_id: ["inline:out"]}, ["b"])
        downstream = store.lease(run, "b", 1, 60, "w1")[0]
        store.complete_batch(
            run, "b", {downstream.task_id: ["inline:done"]}, [], record_results=True
        )
        assert store.run_status(run).complete

    def test_a_join_waits_for_every_branch(self, store):
        """A diamond: the join must not complete while either branch is live."""
        pipeline = Pipeline(
            name="diamond",
            jobs=(
                JobSpec(name="src", fn="m:s"),
                JobSpec(name="left", fn="m:l"),
                JobSpec(name="right", fn="m:r"),
                JobSpec(name="join", fn="m:j"),
            ),
            edges=(
                ("src", "left"),
                ("src", "right"),
                ("left", "join"),
                ("right", "join"),
            ),
        )
        run = store.create_run(pipeline)
        store.submit(run, "src", ["inline:1"])
        store.seal(run, "src")
        task = store.lease(run, "src", 1, 60, "w1")[0]
        store.complete_batch(
            run, "src", {task.task_id: ["inline:x"]}, ["left", "right"]
        )

        left = store.lease(run, "left", 1, 60, "w1")[0]
        store.complete_batch(run, "left", {left.task_id: ["inline:l"]}, ["join"])
        assert not store.run_status(run).job("join").complete, (
            "the join saw one branch finish and must still wait for the other"
        )

        right = store.lease(run, "right", 1, 60, "w1")[0]
        store.complete_batch(run, "right", {right.task_id: ["inline:r"]}, ["join"])
        joined = store.lease(run, "join", 2, 60, "w1")
        assert len(joined) == 2
        store.complete_batch(
            run,
            "join",
            {t.task_id: [] for t in joined},
            [],
        )
        assert store.run_status(run).complete


class TestReduce:
    @pytest.fixture
    def reduce_run(self, store) -> str:
        pipeline = Pipeline(
            name="reduce",
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
        return store.create_run(pipeline)

    def _fill(self, store, run, count):
        store.submit(run, "a", [f"inline:{i}" for i in range(count)])
        store.seal(run, "a")
        tasks = store.lease(run, "a", count, 60, "w1")
        store.complete_batch(run, "a", {t.task_id: [t.payload] for t in tasks}, ["r"])

    def test_folding_replaces_a_batch_with_one_partial(self, store, reduce_run):
        self._fill(store, reduce_run, 4)
        tasks = store.lease(reduce_run, "r", 2, 60, "w1")
        store.fold_batch(reduce_run, "r", [t.task_id for t in tasks], "inline:p")
        status = store.job_status(reduce_run, "r")
        assert (status.ready, status.done) == (3, 2)

    def test_a_repeated_fold_does_not_add_a_second_partial(self, store, reduce_run):
        self._fill(store, reduce_run, 2)
        tasks = store.lease(reduce_run, "r", 2, 60, "w1")
        ids = [t.task_id for t in tasks]
        assert store.fold_batch(reduce_run, "r", ids, "inline:p") == 2
        assert store.fold_batch(reduce_run, "r", ids, "inline:p") == 0
        assert store.job_status(reduce_run, "r").ready == 1

    def test_finalizing_is_refused_while_upstream_is_live(self, store, reduce_run):
        """The reduce cannot emit until it is sure no more input is coming."""
        store.submit(reduce_run, "a", ["inline:1"])
        task = store.lease(reduce_run, "a", 1, 60, "w1")[0]
        store.complete_batch(reduce_run, "a", {task.task_id: ["inline:x"]}, ["r"])
        partial = store.lease(reduce_run, "r", 1, 60, "w1")[0]
        assert not store.finalize_reduce(reduce_run, "r", partial.task_id, [])

    def test_finalizing_is_refused_while_other_partials_remain(self, store, reduce_run):
        self._fill(store, reduce_run, 2)
        first = store.lease(reduce_run, "r", 1, 60, "w1")[0]
        assert not store.finalize_reduce(reduce_run, "r", first.task_id, [])

    def test_the_last_partial_is_emitted_once_upstream_is_done(self, store, reduce_run):
        self._fill(store, reduce_run, 2)
        tasks = store.lease(reduce_run, "r", 2, 60, "w1")
        store.fold_batch(reduce_run, "r", [t.task_id for t in tasks], "inline:total")
        last = store.lease(reduce_run, "r", 2, 60, "w1")[0]
        assert store.finalize_reduce(
            reduce_run, "r", last.task_id, [], record_results=True
        )
        assert store.results(reduce_run) == ("inline:total",)
        assert store.run_status(reduce_run).complete

    def test_a_reduce_over_no_input_completes_with_no_output(self, store, reduce_run):
        store.seal(reduce_run, "a")
        status = store.run_status(reduce_run)
        assert status.complete
        assert store.results(reduce_run) == ()


class TestRunBookkeeping:
    def test_get_pipeline_round_trips_the_spec(self, store, run):
        assert store.get_pipeline(run) == linear_pipeline()

    def test_unknown_run_raises(self, store):
        with pytest.raises(KeyError, match="No such run"):
            store.get_pipeline("nope")

    def test_run_status_reports_dead_letters(self, store, run):
        store.submit(run, "a", ["inline:1"])
        task = store.lease(run, "a", 1, 60, "w1")[0]
        store.fail_batch(run, "a", [task.task_id], "boom", 1)
        assert store.run_status(run).dead_letters == 1

    def test_results_can_be_filtered_by_job(self, store, run):
        store.submit(run, "a", ["inline:1"])
        task = store.lease(run, "a", 1, 60, "w1")[0]
        store.complete_batch(
            run, "a", {task.task_id: ["inline:out"]}, [], record_results=True
        )
        assert store.results(run, "a") == ("inline:out",)
        assert store.results(run, "b") == ()

    def test_runs_are_listed_with_their_state(self, store, run):
        listed = store.list_runs()
        assert [(rid, name) for rid, name, _ in listed] == [(run, "linear")]

    def test_a_task_state_covers_the_whole_lifecycle(self, store, run):
        store.submit(run, "a", ["inline:1"])
        assert store.job_status(run, "a").ready == 1
        task = store.lease(run, "a", 1, 60, "w1")[0]
        assert store.job_status(run, "a").leased == 1
        store.complete_batch(run, "a", {task.task_id: []}, [])
        status = store.job_status(run, "a")
        assert (status.done, status.outstanding) == (1, 0)


def test_derived_ids_are_stable_and_distinct():
    assert derive_task_id("r", "j", "p", "0") == derive_task_id("r", "j", "p", "0")
    assert derive_task_id("r", "j", "p", "0") != derive_task_id("r", "j", "p", "1")
    assert derive_task_id("r", "j", "p", "0") != derive_task_id("r", "k", "p", "0")


def test_task_state_values_are_stable():
    """These strings are persisted; changing them would orphan existing runs."""
    assert {str(state) for state in TaskState} == {"ready", "leased", "done", "failed"}


def test_tasks_are_leased_in_the_order_they_were_submitted():
    """Tasks enqueued in one transaction share a timestamp; order must hold."""
    with TaskStore(":memory:") as store:
        run = store.create_run(linear_pipeline())
        store.submit(run, "a", [f"inline:{i}" for i in range(8)])
        leased = store.lease(run, "a", 8, 60, "w1")
        assert [task.payload for task in leased] == [f"inline:{i}" for i in range(8)]
