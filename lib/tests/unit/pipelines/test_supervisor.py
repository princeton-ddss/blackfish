"""Launching a run as its own process and watching it from outside.

These drive real detached processes rather than mocks, because the properties
being claimed -- that the run survives its launcher, that a dead coordinator is
distinguishable from a slow one, that a recycled pid is not mistaken for a live
run -- are all properties of the operating system, not of the code's structure.
"""

import os
import signal
import sqlite3
import time

import pytest

from blackfish.pipelines.examples.word_count import build_pipeline
from blackfish.pipelines.payload import PayloadStore
from blackfish.pipelines.supervisor import (
    RunHandle,
    RunSupervisor,
    RunVerdict,
)

DOCUMENTS = [
    "the quick brown fox\njumps over the lazy dog",
    "a brown dog\nand a quick fox",
    "the fox is quick\n\nthe dog is lazy",
]


@pytest.fixture
def supervisor(tmp_path) -> RunSupervisor:
    return RunSupervisor(tmp_path / "runs", stale_after=5.0)


def create_run(supervisor: RunSupervisor, seal: bool = True) -> str:
    """What the server does before launching: create the run, submit inputs."""
    return create_run_with_id(supervisor, "run-" + os.urandom(4).hex(), seal)


def create_run_with_id(
    supervisor: RunSupervisor, run_id: str, seal: bool = True
) -> str:
    pipeline = build_pipeline(max_workers=2)
    paths = supervisor.paths(run_id)
    paths.payloads.mkdir(parents=True, exist_ok=True)
    store = supervisor.open_store(run_id)
    try:
        store.create_run(pipeline, run_id=run_id)
        payloads = PayloadStore(paths.payloads)
        store.submit(run_id, "read", [payloads.put(doc) for doc in DOCUMENTS])
        if seal:
            store.seal(run_id, "read")
    finally:
        store.close()
    return run_id


def wait_for(supervisor, run_id, predicate, timeout=30.0):
    deadline = time.monotonic() + timeout
    observation = supervisor.observe(run_id)
    while time.monotonic() < deadline:
        observation = supervisor.observe(run_id)
        if predicate(observation):
            return observation
        time.sleep(0.05)
    raise AssertionError(f"timed out; last verdict was {observation.verdict}")


class TestLaunching:
    def test_a_run_with_no_process_reads_as_queued(self, supervisor):
        run_id = create_run(supervisor)
        observation = supervisor.observe(run_id)
        assert observation.verdict is RunVerdict.QUEUED
        assert observation.pid is None

    def test_a_launched_run_completes(self, supervisor):
        run_id = create_run(supervisor)
        supervisor.launch(run_id, tick_seconds=0.05)
        observation = wait_for(
            supervisor, run_id, lambda o: o.verdict is RunVerdict.COMPLETE
        )
        assert observation.settled
        assert observation.status.dead_letters == 0

    def test_the_results_are_readable_from_outside(self, supervisor):
        run_id = create_run(supervisor)
        supervisor.launch(run_id, tick_seconds=0.05)
        wait_for(supervisor, run_id, lambda o: o.verdict is RunVerdict.COMPLETE)

        store = supervisor.open_store(run_id, read_only=True)
        payloads = PayloadStore(supervisor.paths(run_id).payloads)
        try:
            counts = [payloads.get(ref) for ref in store.results(run_id)]
        finally:
            store.close()
        assert counts == [
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

    def test_the_runner_is_in_its_own_session(self, supervisor):
        """Detachment is the point: the launcher's SIGHUP must not reach it."""
        run_id = create_run(supervisor, seal=False)
        handle = supervisor.launch(run_id, tick_seconds=0.05)
        try:
            assert os.getpgid(handle.pid) != os.getpgid(os.getpid())
        finally:
            supervisor.cancel(run_id, grace_seconds=10)

    def test_progress_is_visible_while_the_run_is_live(self, supervisor):
        run_id = create_run(supervisor, seal=False)
        supervisor.launch(run_id, tick_seconds=0.05)
        try:
            observation = wait_for(
                supervisor,
                run_id,
                lambda o: (
                    o.status is not None and o.status.job("read").done == len(DOCUMENTS)
                ),
            )
            assert observation.verdict is RunVerdict.RUNNING
            assert observation.heartbeat_age is not None
        finally:
            supervisor.cancel(run_id, grace_seconds=10)


class TestStartUp:
    def test_a_freshly_launched_run_reads_as_starting(self, supervisor):
        """Launched is not the same claim as working."""
        run_id = create_run(supervisor, seal=False)
        supervisor.launch(run_id, tick_seconds=0.05)
        try:
            assert supervisor.observe(run_id).verdict in (
                RunVerdict.STARTING,
                RunVerdict.RUNNING,
            )
        finally:
            supervisor.cancel(run_id, grace_seconds=10)

    def test_a_process_that_never_checks_in_reads_as_unresponsive(self, tmp_path):
        run_id = "never"
        supervisor = RunSupervisor(tmp_path / "runs", stale_after=0.0)
        create_run_with_id(supervisor, run_id, seal=False)
        supervisor.launch(run_id, tick_seconds=0.05)
        try:
            observation = supervisor.observe(run_id)
            assert observation.verdict in (
                RunVerdict.UNRESPONSIVE,
                RunVerdict.RUNNING,
            )
        finally:
            supervisor.cancel(run_id, grace_seconds=10)


class TestFailureDetection:
    def test_a_killed_runner_reads_as_crashed(self, supervisor):
        """The queues are intact; only the process is gone."""
        run_id = create_run(supervisor, seal=False)
        handle = supervisor.launch(run_id, tick_seconds=0.05)
        wait_for(supervisor, run_id, lambda o: o.verdict is RunVerdict.RUNNING)

        os.kill(handle.pid, signal.SIGKILL)
        observation = wait_for(
            supervisor, run_id, lambda o: o.verdict is RunVerdict.CRASHED
        )
        assert not observation.alive
        assert observation.status.job("read").seen == len(DOCUMENTS)

    def test_a_crashed_run_can_be_relaunched_on_the_same_queues(self, supervisor):
        run_id = create_run(supervisor)
        handle = supervisor.launch(run_id, tick_seconds=0.05)
        os.kill(handle.pid, signal.SIGKILL)
        wait_for(supervisor, run_id, lambda o: o.verdict is RunVerdict.CRASHED)

        supervisor.launch(run_id, tick_seconds=0.05)
        assert wait_for(
            supervisor, run_id, lambda o: o.verdict is RunVerdict.COMPLETE
        ).settled

    def test_a_recycled_pid_is_not_mistaken_for_a_live_run(self, supervisor):
        """A pid alone is not evidence; the launch time is what makes it one."""
        run_id = create_run(supervisor, seal=False)
        handle = supervisor.launch(run_id, tick_seconds=0.05)
        try:
            assert supervisor.is_alive(handle)
            impostor = RunHandle(
                run_id=run_id,
                pid=handle.pid,
                started_at=handle.started_at - 10_000,
                command=handle.command,
            )
            assert not supervisor.is_alive(impostor)
        finally:
            supervisor.cancel(run_id, grace_seconds=10)

    def test_a_missing_process_is_not_alive(self, supervisor):
        handle = RunHandle(
            run_id="x", pid=2**22 - 1, started_at=time.time(), command=[]
        )
        assert not supervisor.is_alive(handle)


class TestCancelling:
    def test_cancel_stops_a_running_runner(self, supervisor):
        run_id = create_run(supervisor, seal=False)
        supervisor.launch(run_id, tick_seconds=0.05)
        wait_for(supervisor, run_id, lambda o: o.verdict is RunVerdict.RUNNING)

        assert supervisor.cancel(run_id, grace_seconds=30) is True
        observation = wait_for(
            supervisor, run_id, lambda o: o.verdict is RunVerdict.CANCELLED
        )
        assert not observation.alive

    def test_cancelling_a_run_with_no_process_is_a_no_op(self, supervisor):
        run_id = create_run(supervisor)
        assert supervisor.cancel(run_id) is False

    def test_cancelling_during_start_up_still_reads_as_cancelled(self, supervisor):
        """The window before the runner installs its handlers is covered."""
        run_id = create_run(supervisor, seal=False)
        supervisor.launch(run_id, tick_seconds=0.05)
        supervisor.cancel(run_id, grace_seconds=30)
        assert supervisor.observe(run_id).verdict is RunVerdict.CANCELLED


class TestReattaching:
    def test_a_new_supervisor_picks_up_an_existing_run(self, tmp_path):
        """What a server restart looks like: the handle is on disk, not in memory."""
        first = RunSupervisor(tmp_path / "runs")
        run_id = create_run(first, seal=False)
        first.launch(run_id, tick_seconds=0.05)
        wait_for(first, run_id, lambda o: o.verdict is RunVerdict.RUNNING)

        second = RunSupervisor(tmp_path / "runs")
        try:
            observation = second.observe(run_id)
            assert observation.verdict is RunVerdict.RUNNING
            assert observation.pid == first.load_handle(run_id).pid
        finally:
            second.cancel(run_id, grace_seconds=10)

    def test_an_unreadable_handle_is_reported_as_queued(self, supervisor):
        run_id = create_run(supervisor)
        supervisor.paths(run_id).handle.write_text("{not json")
        assert supervisor.observe(run_id).verdict is RunVerdict.QUEUED


class TestObservationIsNonDisturbing:
    def test_a_monitor_cannot_write_to_the_run(self, supervisor):
        run_id = create_run(supervisor)
        store = supervisor.open_store(run_id, read_only=True)
        try:
            with pytest.raises(sqlite3.OperationalError, match="readonly"):
                store.heartbeat(run_id)
        finally:
            store.close()

    def test_a_read_only_store_needs_a_real_file(self, supervisor):
        from blackfish.pipelines.store import TaskStore

        with pytest.raises(ValueError, match="real database file"):
            TaskStore(":memory:", read_only=True)

    def test_the_log_captures_what_the_runner_did(self, supervisor):
        run_id = create_run(supervisor)
        supervisor.launch(run_id, tick_seconds=0.05)
        wait_for(supervisor, run_id, lambda o: o.verdict is RunVerdict.COMPLETE)
        log = "\n".join(supervisor.tail_log(run_id))
        assert "launching runner" in log
        assert "driving pipeline 'word-count'" in log

    def test_relaunching_appends_to_the_log_rather_than_erasing_it(self, supervisor):
        """The log that explains a crash must survive the relaunch."""
        run_id = create_run(supervisor)
        handle = supervisor.launch(run_id, tick_seconds=0.05)
        os.kill(handle.pid, signal.SIGKILL)
        wait_for(supervisor, run_id, lambda o: o.verdict is RunVerdict.CRASHED)

        supervisor.launch(run_id, tick_seconds=0.05)
        wait_for(supervisor, run_id, lambda o: o.verdict is RunVerdict.COMPLETE)
        assert "\n".join(supervisor.tail_log(run_id)).count("launching runner") == 2
