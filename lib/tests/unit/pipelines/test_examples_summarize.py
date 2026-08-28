"""Login-node IO feeding GPU work: placement, rate limits, and batch blast radius."""

from pathlib import Path

import pytest

from blackfish.pipelines import run_local
from blackfish.pipelines.examples.summarize import (
    RateLimited,
    build_pipeline,
    fetch_documents,
    load_summarizer,
    open_session,
    summarize,
)
from blackfish.pipelines.spec import Placement

pytestmark = pytest.mark.anyio


@pytest.fixture
def corpus(tmp_path):
    directory = tmp_path / "corpus"
    directory.mkdir()
    names = []
    for index in range(6):
        name = f"doc{index}.txt"
        (directory / name).write_text(" ".join(f"word{w}" for w in range(30)))
        names.append(name)
    return directory, names


def session_for(tmp_path, corpus_dir, fail_once=False):
    return open_session(
        corpus_dir=str(corpus_dir),
        state_dir=str(tmp_path / "state"),
        audit_log=str(tmp_path / "audit.log"),
        fail_once=fail_once,
    )


class TestPlacement:
    def test_the_two_jobs_have_opposite_shapes(self, tmp_path):
        pipeline = build_pipeline(str(tmp_path), str(tmp_path), str(tmp_path))
        fetch, summarize_job = pipeline.jobs

        assert fetch.placement is Placement.LOGIN
        assert fetch.resources == {}
        assert fetch.max_workers > summarize_job.max_workers

        assert summarize_job.placement is Placement.COMPUTE
        assert summarize_job.resources["gpus"] == 1
        assert summarize_job.batch_size > fetch.batch_size


class TestRateLimiting:
    def test_a_refused_request_raises_rather_than_returning_less(
        self, corpus, tmp_path
    ):
        """Swallowing a rate limit turns a retryable condition into data loss."""
        directory, names = corpus
        session = session_for(tmp_path, directory, fail_once=True)
        with pytest.raises(RateLimited, match="429"):
            fetch_documents(names[:1], session)

    def test_the_second_attempt_succeeds(self, corpus, tmp_path):
        directory, names = corpus
        session = session_for(tmp_path, directory, fail_once=True)
        with pytest.raises(RateLimited):
            fetch_documents(names[:1], session)
        assert fetch_documents(names[:1], session)[0]["name"] == names[0]

    def test_only_the_first_worker_to_ask_is_refused(self, corpus, tmp_path):
        """Exclusive create, so two workers cannot both believe they are first."""
        directory, names = corpus
        first = session_for(tmp_path, directory, fail_once=True)
        second = session_for(tmp_path, directory, fail_once=True)
        with pytest.raises(RateLimited):
            fetch_documents(names[:1], first)
        assert fetch_documents(names[:1], second)


class TestSummaries:
    def test_a_summary_is_produced_per_document(self, corpus, tmp_path):
        directory, names = corpus
        documents = fetch_documents(names[:2], session_for(tmp_path, directory))
        summaries = summarize(documents, load_summarizer(max_words=3))
        assert [s["name"] for s in summaries] == names[:2]
        assert summaries[0]["summary"] == "word0 word1 word2"
        assert summaries[0]["words"] == 30


class TestEndToEnd:
    async def test_every_document_is_fetched_and_summarized(self, corpus, tmp_path):
        directory, names = corpus
        status, results = await run_local(
            build_pipeline(
                corpus_dir=str(directory),
                state_dir=str(tmp_path / "state"),
                audit_log=str(tmp_path / "audit.log"),
            ),
            names,
            root=tmp_path / "run",
            timeout=60,
        )
        assert status.complete
        assert sorted(r["name"] for r in results) == sorted(names)

    async def test_a_rate_limited_service_still_completes(self, corpus, tmp_path):
        """Backoff plus retries, without a single dead letter."""
        directory, names = corpus
        status, results = await run_local(
            build_pipeline(
                corpus_dir=str(directory),
                state_dir=str(tmp_path / "state"),
                audit_log=str(tmp_path / "audit.log"),
                fail_once=True,
                retry_backoff=0.01,
            ),
            names,
            root=tmp_path / "run",
            timeout=60,
        )
        assert status.complete
        assert status.dead_letters == 0
        assert sorted(r["name"] for r in results) == sorted(names)

    async def test_a_refusal_costs_the_whole_batch(self, corpus, tmp_path):
        """The lesson behind fetch's small batch_size, measured."""
        directory, names = corpus
        audit = tmp_path / "audit.log"
        status, _ = await run_local(
            build_pipeline(
                corpus_dir=str(directory),
                state_dir=str(tmp_path / "state"),
                audit_log=str(audit),
                fail_once=True,
                retry_backoff=0.01,
            ),
            names,
            root=tmp_path / "run",
            timeout=60,
        )
        assert status.complete

        fetched = audit.read_text().splitlines()
        assert sorted(set(fetched)) == sorted(names), "every document arrived"
        assert len(fetched) > len(names), (
            "a refused request should have forced its whole batch to be refetched"
        )

    async def test_a_healthy_service_fetches_each_document_once(self, corpus, tmp_path):
        directory, names = corpus
        audit = tmp_path / "audit.log"
        await run_local(
            build_pipeline(
                corpus_dir=str(directory),
                state_dir=str(tmp_path / "state"),
                audit_log=str(audit),
            ),
            names,
            root=tmp_path / "run",
            timeout=60,
        )
        assert sorted(audit.read_text().splitlines()) == sorted(names)

    async def test_the_gpu_job_is_released_when_the_queue_drains(
        self, corpus, tmp_path
    ):
        directory, names = corpus
        status, _ = await run_local(
            build_pipeline(
                corpus_dir=str(directory),
                state_dir=str(tmp_path / "state"),
                audit_log=str(tmp_path / "audit.log"),
            ),
            names,
            root=tmp_path / "run",
            timeout=60,
        )
        assert status.job("summarize").complete
        assert Path(tmp_path / "run").exists()
