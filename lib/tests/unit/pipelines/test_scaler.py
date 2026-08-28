import pytest

from blackfish.pipelines.scaler import Autoscaler
from blackfish.pipelines.spec import JobSpec
from blackfish.pipelines.store import JobStatus


def status(**kwargs) -> JobStatus:
    defaults = dict(
        job="a",
        ready=0,
        leased=0,
        done=0,
        failed=0,
        seen=0,
        sealed=True,
        upstream_complete=True,
        complete=False,
    )
    return JobStatus(**{**defaults, **kwargs})


def job(**kwargs) -> JobSpec:
    return JobSpec(name="a", fn="m:f", **kwargs)


class TestScaleUp:
    def test_backlog_is_divided_by_batch_size(self):
        """A hundred tasks at 32 per call is four workers, not a hundred."""
        decision = Autoscaler().decide(
            job(batch_size=32, max_workers=100), status(ready=100), current=0
        )
        assert decision.desired == 4

    def test_scaling_up_happens_on_the_first_tick(self):
        decision = Autoscaler().decide(job(max_workers=4), status(ready=4), current=0)
        assert decision.desired == 4
        assert "backlog" in decision.reason

    def test_max_workers_is_a_hard_ceiling(self):
        decision = Autoscaler().decide(
            job(batch_size=1, max_workers=2), status(ready=50), current=0
        )
        assert decision.desired == 2

    def test_min_workers_is_held_even_with_an_empty_queue(self):
        decision = Autoscaler().decide(
            job(min_workers=2, max_workers=4), status(ready=0), current=0
        )
        assert decision.desired == 2

    def test_in_flight_work_counts_toward_demand(self):
        """Otherwise a job is scaled down while its workers are mid-batch."""
        decision = Autoscaler().decide(
            job(batch_size=1, max_workers=4), status(ready=0, leased=2), current=2
        )
        assert decision.desired == 2


class TestScaleDown:
    def test_an_idle_job_is_not_released_immediately(self):
        """Slurm queue time makes a premature release expensive to undo."""
        scaler = Autoscaler(scale_down_after=3)
        decision = scaler.decide(job(max_workers=4), status(ready=0), current=2)
        assert decision.desired == 2
        assert "1/3" in decision.reason

    def test_a_job_idle_for_long_enough_is_released(self):
        scaler = Autoscaler(scale_down_after=3)
        spec, idle = job(max_workers=4), status(ready=0)
        for _ in range(2):
            assert scaler.decide(spec, idle, current=2).desired == 2
        assert scaler.decide(spec, idle, current=2).desired == 0

    def test_returning_work_resets_the_countdown(self):
        scaler = Autoscaler(scale_down_after=3)
        spec = job(batch_size=1, max_workers=4)
        scaler.decide(spec, status(ready=0), current=2)
        scaler.decide(spec, status(ready=2), current=2)
        for _ in range(2):
            assert scaler.decide(spec, status(ready=0), current=2).desired == 2

    def test_scale_down_stops_at_min_workers(self):
        scaler = Autoscaler(scale_down_after=1)
        decision = scaler.decide(
            job(min_workers=1, max_workers=4), status(ready=0), current=3
        )
        assert decision.desired == 1

    def test_hysteresis_is_tracked_per_job(self):
        scaler = Autoscaler(scale_down_after=2)
        first, second = job(), JobSpec(name="b", fn="m:f")
        scaler.decide(first, status(ready=0), current=1)
        assert scaler.decide(second, status(job="b", ready=0), current=1).desired == 1


class TestCompletion:
    def test_a_complete_job_releases_every_worker(self):
        decision = Autoscaler().decide(
            job(min_workers=2, max_workers=2), status(complete=True), current=2
        )
        assert decision.desired == 0
        assert decision.reason == "job complete"

    def test_completion_beats_min_workers_and_hysteresis(self):
        scaler = Autoscaler(scale_down_after=10)
        assert (
            scaler.decide(
                job(min_workers=4, max_workers=4),
                status(complete=True),
                current=4,
            ).desired
            == 0
        )


def test_a_decision_that_changes_nothing_is_flagged_as_such():
    decision = Autoscaler().decide(job(max_workers=2), status(ready=2), current=2)
    assert decision.desired == 2
    assert not decision.changed
    assert decision.reason == "at target"


def test_forget_clears_hysteresis_state():
    scaler = Autoscaler(scale_down_after=2)
    spec = job(max_workers=4)
    scaler.decide(spec, status(ready=0), current=2)
    scaler.forget("a")
    assert "1/2" in scaler.decide(spec, status(ready=0), current=2).reason


@pytest.mark.parametrize("backlog,batch,expected", [(1, 8, 1), (8, 8, 1), (9, 8, 2)])
def test_a_partial_batch_still_needs_a_worker(backlog, batch, expected):
    decision = Autoscaler().decide(
        job(batch_size=batch, max_workers=10), status(ready=backlog), current=0
    )
    assert decision.desired == expected
