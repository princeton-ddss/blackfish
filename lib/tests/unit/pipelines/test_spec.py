import pytest

from blackfish.pipelines.spec import Cardinality, JobSpec, Pipeline, Placement


def job(name: str, **kwargs) -> JobSpec:
    kwargs.setdefault("fn", f"tests.jobs:{name}")
    return JobSpec(name=name, **kwargs)


class TestJobSpec:
    def test_rejects_fn_that_is_not_an_import_path(self):
        with pytest.raises(ValueError, match="module:attribute"):
            JobSpec(name="a", fn="not_an_import_path")

    def test_rejects_setup_that_is_not_an_import_path(self):
        with pytest.raises(ValueError, match="module:attribute"):
            JobSpec(name="a", fn="m:f", setup="nope")

    def test_rejects_empty_name(self):
        with pytest.raises(ValueError, match="non-empty"):
            JobSpec(name="", fn="m:f")

    @pytest.mark.parametrize(
        "kwargs,message",
        [
            ({"batch_size": 0}, "batch_size must be >= 1"),
            ({"min_workers": -1}, "min_workers must be >= 0"),
            ({"max_workers": 0}, "max_workers must be >= 1"),
            ({"min_workers": 3, "max_workers": 2}, "exceeds"),
            ({"max_attempts": 0}, "max_attempts must be >= 1"),
            ({"lease_seconds": 0}, "lease_seconds must be >= 1"),
        ],
    )
    def test_rejects_out_of_range_settings(self, kwargs, message):
        with pytest.raises(ValueError, match=message):
            JobSpec(name="a", fn="m:f", **kwargs)

    def test_reduce_requires_a_batch_of_at_least_two(self):
        """A fold over one value returns it unchanged, so the queue never shrinks."""
        with pytest.raises(ValueError, match="batch_size >= 2"):
            JobSpec(
                name="a",
                fn="m:f",
                cardinality=Cardinality.MANY_TO_ONE,
                batch_size=1,
            )

    def test_reduce_accepts_a_batch_of_two(self):
        spec = JobSpec(
            name="a", fn="m:f", cardinality=Cardinality.MANY_TO_ONE, batch_size=2
        )
        assert spec.cardinality is Cardinality.MANY_TO_ONE


class TestPipelineValidation:
    def test_rejects_empty_pipeline(self):
        with pytest.raises(ValueError, match="no jobs"):
            Pipeline(name="p", jobs=())

    def test_rejects_duplicate_job_names(self):
        with pytest.raises(ValueError, match="duplicate job names: a"):
            Pipeline(name="p", jobs=(job("a"), job("a")))

    def test_rejects_edge_to_unknown_job(self):
        with pytest.raises(ValueError, match="unknown job 'b'"):
            Pipeline(name="p", jobs=(job("a"),), edges=(("a", "b"),))

    def test_rejects_self_edge(self):
        with pytest.raises(ValueError, match="cannot depend on itself"):
            Pipeline(name="p", jobs=(job("a"),), edges=(("a", "a"),))

    def test_rejects_duplicate_edges(self):
        with pytest.raises(ValueError, match="duplicate edges"):
            Pipeline(
                name="p",
                jobs=(job("a"), job("b")),
                edges=(("a", "b"), ("a", "b")),
            )

    def test_rejects_a_cycle(self):
        with pytest.raises(ValueError, match="cyclic"):
            Pipeline(
                name="p",
                jobs=(job("a"), job("b"), job("c")),
                edges=(("a", "b"), ("b", "c"), ("c", "a")),
            )

    def test_names_the_jobs_on_the_cycle(self):
        with pytest.raises(ValueError, match="a, b, c"):
            Pipeline(
                name="p",
                jobs=(job("a"), job("b"), job("c")),
                edges=(("a", "b"), ("b", "c"), ("c", "a")),
            )


class TestPipelineTopology:
    @pytest.fixture
    def diamond(self) -> Pipeline:
        return Pipeline(
            name="diamond",
            jobs=(job("src"), job("left"), job("right"), job("join")),
            edges=(
                ("src", "left"),
                ("src", "right"),
                ("left", "join"),
                ("right", "join"),
            ),
        )

    def test_sources_and_sinks(self, diamond):
        assert [j.name for j in diamond.sources] == ["src"]
        assert [j.name for j in diamond.sinks] == ["join"]

    def test_upstream_and_downstream(self, diamond):
        assert diamond.downstream("src") == ("left", "right")
        assert diamond.upstream("join") == ("left", "right")
        assert diamond.upstream("src") == ()

    def test_toposort_puts_producers_before_consumers(self, diamond):
        order = [j.name for j in diamond.toposorted()]
        assert order.index("src") < order.index("left")
        assert order.index("left") < order.index("join")
        assert order.index("right") < order.index("join")

    def test_job_lookup_raises_for_unknown_name(self, diamond):
        with pytest.raises(KeyError, match="no job named 'nope'"):
            diamond.job("nope")

    def test_round_trips_through_plain_data(self, diamond):
        restored = Pipeline.from_dict(diamond.to_dict())
        assert restored == diamond

    def test_round_trip_preserves_every_job_setting(self):
        original = Pipeline(
            name="p",
            jobs=(
                JobSpec(
                    name="a",
                    fn="m:f",
                    setup="m:s",
                    cardinality=Cardinality.ONE_TO_MANY,
                    batch_size=7,
                    min_workers=1,
                    max_workers=9,
                    placement=Placement.LOGIN,
                    resources={"gpus": 2},
                    max_attempts=5,
                    lease_seconds=42,
                ),
            ),
        )
        assert Pipeline.from_dict(original.to_dict()) == original
