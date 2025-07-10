from typing import Any

import pytest
from click.testing import CliRunner

from app.models import BatchJob


@pytest.fixture()
def cli_runner() -> CliRunner:
    return CliRunner()


@pytest.mark.parametrize(
    "profile, mount, repo_id, revision, expected_exit_code, expected_output",
    [
        (["not_a_profile", "test", "openai/whisper-large-v3", None, 0, ""], 0),
        (["test", None, "openai/whisper-large-v3", None, 0, ""], 0),
        (["test", "test", "not_a_repo_id", None, 0, ""], 0),
        (["test", "test", "openai/whisper-large-v3", None, 0, ""], 0),
        (["test-slurm", "test", "openai/whisper-large-v3", None, 0, ""], 0),
    ],
)
def test_cli_batch_speech_recognition(
    profile: str,
    mount: str,
    repo_id: str,
    revision: str,
    expected_exit_code: int,
    expected_output: str,
) -> None:
    # Mock/fixture deserialize_profile, get_models, get_latest_commit, get_model_dir
    # Mock/fixture requests.post, etc.

    with CliRunner() as runner:
        result = runner.invoke(
            [
                "batch",
                "--profile",
                profile,  # missing => log error, return None, Exit Code?
                "--mount",
                mount,
                "--speech-recognition",
                repo_id,  # missing => log error, return None, Exit Code?
                "--revision",
                revision,
                "--dry-run",
            ]
        )
        assert result.exit_code == 0
        assert result.output.contains(expected_output)


# Improper filter format => exit code 0?, "Unable to parse filter: {e}"
# Proper filters => exit code 0, "(List of batch jobs based on fixture data and filters and running jobs only!)"
# --all => exit code 0, "(List of all batch jobs based on fixture data)"
# --all w/ filters => exit code 0, "(List of all batch jobs based on fixture data and filters)"
def test_cli_batch_ls(batch_jobs: list[BatchJob | dict[str, Any]]) -> None:
    # Mock/fixture requests.get

    with CliRunner() as runner:
        result = runner.invoke(["batch", "ls"])
        assert result.exit_code == 0
        assert "No batch jobs found." in result.output or "Batch jobs:" in result.output


# Missing job ID => exit code 2
# Non-existent job ID => exit code 0, "Failed to stop batch job ..."
# Existing job ID => exit code 0, "Stopped batch job 12345."
def test_cli_batch_stop(expected_exit_code: int, expected_output: str) -> None:
    # Mock/fixture requests.put

    with CliRunner() as runner:
        result = runner.invoke(["batch", "stop", "12345"])
        assert result.exit_code == expected_exit_code
        assert expected_output in result.output


# Missing filters => ???
# Invalid filters => exit code 1, "Unable to parse filter: {e}"
# Non-existent job ID => exit code 0, "Query did not match any batch jobs."
# Existing job ID => exit code 0, "Stopped batch job 12345."
# Unable to rm a job => there will be an error message...
def test_cli_batch_rm(id: str, expected_exit_code: int, expected_output: str) -> None:
    # Mock/fixture requests.delete

    with CliRunner() as runner:
        result = runner.invoke(["batch", "rm", "--filters", f"id={id}"])
        assert result.exit_code == expected_exit_code
        assert expected_output in result.output
