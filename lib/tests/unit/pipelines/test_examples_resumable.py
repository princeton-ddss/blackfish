"""The standing-run example: restart survival and idempotent re-submission.

These are the two continuity properties a long-lived pipeline needs, and they
are worth testing directly because both fail silently: a botched restart
quietly redoes finished work, and a botched re-scan quietly reprocesses the
whole directory every time the timer fires.
"""

import pytest

from blackfish.pipelines.backends.local import ThreadBackend
from blackfish.pipelines.coordinator import Coordinator
from blackfish.pipelines.examples.resumable import (
    build_pipeline,
    scan_directory,
    submit_directory,
)
from blackfish.pipelines.payload import PayloadStore
from blackfish.pipelines.store import TaskStore

pytestmark = pytest.mark.anyio


class Harness:
    """A coordinator that can be torn down and rebuilt over the same store."""

    def __init__(self, root):
        self.root = root
        self.inbox = root / "inbox"
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.audit = root / "audit.log"
        self.pipeline = build_pipeline(
            output_dir=str(root / "out"), audit_log=str(self.audit)
        )
        self.store = None
        self.backend = None
        self.coordinator = None
        self.run_id = None

    def open(self):
        """Start (or restart) the coordinator over the durable store."""
        self.store = TaskStore(self.root / "pipeline.db")
        payloads = PayloadStore(self.root / "payloads")
        self.backend = ThreadBackend(self.store, payloads, self.pipeline)
        self.coordinator = Coordinator(
            self.store, payloads, self.backend, tick_seconds=0.01
        )
        return self.coordinator

    async def close(self):
        if self.run_id is not None:
            await self.backend.shutdown(self.run_id)
        self.store.close()

    def add_files(self, *names):
        for name in names:
            (self.inbox / name).write_text(f"contents of {name}\n")

    def submit(self) -> int:
        return submit_directory(
            self.coordinator, self.run_id, "transform", str(self.inbox)
        )

    async def drain(self, ticks: int = 400):
        """Tick until the queue is empty. An unsealed run never reports complete."""
        for _ in range(ticks):
            status = await self.coordinator.tick(self.run_id)
            if status.job("transform").outstanding == 0:
                return status
        raise AssertionError("queue did not drain")

    @property
    def processed(self) -> list[str]:
        if not self.audit.exists():
            return []
        return self.audit.read_text().splitlines()


@pytest.fixture
async def harness(tmp_path):
    h = Harness(tmp_path)
    h.open()
    yield h
    await h.close()


class TestDirectoryScan:
    def test_scan_is_sorted_and_filtered(self, tmp_path):
        for name in ("b.txt", "a.txt", "c.md"):
            (tmp_path / name).write_text("x")
        found = scan_directory(str(tmp_path))
        assert [f.rsplit("/", 1)[-1] for f in found] == ["a.txt", "b.txt"]

    def test_an_empty_directory_scans_to_nothing(self, tmp_path):
        assert scan_directory(str(tmp_path)) == []


class TestIdempotentSubmission:
    async def test_files_are_submitted_once(self, harness):
        harness.add_files("a.txt", "b.txt", "c.txt")
        harness.run_id = harness.coordinator.start_run(harness.pipeline, [], seal=False)
        assert harness.submit() == 3

    async def test_resubmitting_the_same_directory_enqueues_nothing(self, harness):
        harness.add_files("a.txt", "b.txt")
        harness.run_id = harness.coordinator.start_run(harness.pipeline, [], seal=False)
        assert harness.submit() == 2
        assert harness.submit() == 0
        assert harness.submit() == 0

    async def test_only_new_files_are_picked_up(self, harness):
        harness.add_files("a.txt")
        harness.run_id = harness.coordinator.start_run(harness.pipeline, [], seal=False)
        harness.submit()
        await harness.drain()
        harness.add_files("b.txt", "c.txt")
        assert harness.submit() == 2

    async def test_dedupe_holds_after_the_files_are_processed(self, harness):
        """The queue remembers what it has seen; the pipeline keeps no manifest."""
        harness.add_files("a.txt", "b.txt")
        harness.run_id = harness.coordinator.start_run(harness.pipeline, [], seal=False)
        harness.submit()
        await harness.drain()
        assert harness.submit() == 0
        assert len(harness.processed) == 2


class TestRestart:
    async def test_a_restart_does_not_redo_finished_work(self, harness):
        harness.add_files("a.txt", "b.txt", "c.txt")
        harness.run_id = harness.coordinator.start_run(harness.pipeline, [], seal=False)
        harness.submit()
        await harness.drain()
        assert len(harness.processed) == 3

        # The coordinator dies and comes back over the same store.
        await harness.backend.shutdown(harness.run_id)
        harness.store.close()
        harness.open()

        await harness.drain()
        assert len(harness.processed) == 3, "finished work was redone on restart"

    async def test_a_restart_recovers_the_run_without_being_told_about_it(
        self, harness
    ):
        """Everything the coordinator needs is in the store, including the DAG."""
        harness.add_files("a.txt")
        harness.run_id = harness.coordinator.start_run(harness.pipeline, [], seal=False)
        harness.submit()
        await harness.drain()

        await harness.backend.shutdown(harness.run_id)
        harness.store.close()
        harness.open()

        recovered = harness.store.get_pipeline(harness.run_id)
        assert recovered == harness.pipeline

    async def test_new_work_arrives_after_a_restart(self, harness):
        harness.add_files("a.txt")
        harness.run_id = harness.coordinator.start_run(harness.pipeline, [], seal=False)
        harness.submit()
        await harness.drain()

        await harness.backend.shutdown(harness.run_id)
        harness.store.close()
        harness.open()

        harness.add_files("b.txt", "c.txt")
        assert harness.submit() == 2
        await harness.drain()
        assert sorted(p.rsplit("/", 1)[-1] for p in harness.processed) == [
            "a.txt",
            "b.txt",
            "c.txt",
        ]

    async def test_work_in_flight_when_the_coordinator_died_is_recovered(
        self, tmp_path
    ):
        """A lease outlives the coordinator; expiry is what brings it back."""
        now = {"t": 1000.0}
        harness = Harness(tmp_path)
        harness.store = TaskStore(tmp_path / "pipeline.db", clock=lambda: now["t"])
        payloads = PayloadStore(tmp_path / "payloads")
        harness.backend = ThreadBackend(harness.store, payloads, harness.pipeline)
        harness.coordinator = Coordinator(
            harness.store, payloads, harness.backend, tick_seconds=0.01
        )
        harness.add_files("a.txt", "b.txt")
        harness.run_id = harness.coordinator.start_run(harness.pipeline, [], seal=False)
        harness.submit()

        # A worker takes the batch, then the whole node goes away.
        harness.store.lease(harness.run_id, "transform", 4, 300, "doomed")
        assert harness.processed == []

        now["t"] += 600  # the lease expires while nothing is running
        await harness.drain()
        assert len(harness.processed) == 2
        await harness.close()


class TestSealing:
    async def test_an_unsealed_run_never_reports_complete(self, harness):
        harness.add_files("a.txt")
        harness.run_id = harness.coordinator.start_run(harness.pipeline, [], seal=False)
        harness.submit()
        status = await harness.drain()
        assert not status.complete, "a standing run stays open by design"

    async def test_sealing_closes_the_run(self, harness):
        harness.add_files("a.txt", "b.txt")
        harness.run_id = harness.coordinator.start_run(harness.pipeline, [], seal=False)
        harness.submit()
        await harness.drain()
        harness.coordinator.seal(harness.run_id, "transform")
        status = await harness.coordinator.run_until_complete(
            harness.run_id, timeout=30
        )
        assert status.complete
        assert len(harness.coordinator.results(harness.run_id)) == 2

    async def test_outputs_land_where_the_records_say(self, harness):
        from pathlib import Path

        harness.add_files("a.txt")
        harness.run_id = harness.coordinator.start_run(harness.pipeline, [], seal=False)
        harness.submit()
        await harness.drain()
        harness.coordinator.seal(harness.run_id, "transform")
        await harness.coordinator.run_until_complete(harness.run_id, timeout=30)

        record = harness.coordinator.results(harness.run_id)[0]
        assert Path(record["output"]).read_text() == "CONTENTS OF A.TXT\n"
