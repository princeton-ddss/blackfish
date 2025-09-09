import pytest
from click.testing import CliRunner


@pytest.fixture()
def cli_runner() -> CliRunner:
    return CliRunner()


@pytest.mark.parametrize(
    "profile, mount, repo_id, revision, expected_exit_code, expected_output",
    [
        ("not_a_profile", "test", "openai/whisper-large-v3", None, 0, ""),
        ("test", None, "openai/whisper-large-v3", None, 0, ""),
        ("test", "test", "not_a_repo_id", None, 0, ""),
        ("test", "test", "openai/whisper-large-v3", None, 0, ""),
        ("test-slurm", "test", "openai/whisper-large-v3", None, 0, ""),
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
                profile,  # None => log error, return None, Exit Code?
                "--mount",
                mount,
                "--speech-recognition",
                repo_id,  # None => log error, return None, Exit Code?
                "--revision",
                revision,
                "--dry-run",
            ]
        )
        assert result.exit_code == 0
        assert expected_output in result.output


# Improper filter format => exit code 0?, "Unable to parse filter: {e}"
# Proper filters => exit code 0, "(List of batch jobs based on fixture data and filters and running jobs only!)"
# --all => exit code 0, "(List of all batch jobs based on fixture data)"
# --all w/ filters => exit code 0, "(List of all batch jobs based on fixture data and filters)"
@pytest.mark.parametrize(
    "filters, all, expected_exit_code, expected_output"[
        ("", False, 0, ""),
        ("", True, 0, ""),
    ],
)
def test_cli_batch_ls(filters: str, all: bool) -> None:
    # Mock/fixture requests.get

    with CliRunner() as runner:
        if all:
            result = runner.invoke(["batch", "ls", "--filters", filters, "--all"])
        else:
            result = runner.invoke(["batch", "ls", "--filters", filters])

        assert result.exit_code == 0
        assert "No batch jobs found." in result.output or "Batch jobs:" in result.output


@pytest.mark.parametrize(
    "job_id, expected_exit_code, expected_output",
    [
        (None, 2, ""),
        ("not_a_job_id", 0, "Failed to stop batch job..."),
        ("12345", 0, "Stopped batch job 12345/"),
    ],
)
def test_cli_batch_stop(expected_exit_code: int, expected_output: str) -> None:
    # Mock/fixture requests.put

    with CliRunner() as runner:
        result = runner.invoke(["batch", "stop", "12345"])
        assert result.exit_code == expected_exit_code
        assert expected_output in result.output


@pytest.mark.parametrize(
    "filters, expected_exit_code, expected_output",
    [
        (None, 0, ""),
        ("id=does_not_exist", 0, "Query did not match any batch jobs."),
        ("id=12345", 0, "Removed batch job 12345."),
        ("pipeline=speech_recognition", 0, "Removed batch job 12345."),
        ("pipeline=speech_recognition,status=stopped", 0, "Removed batch job 12345."),
        ("pipeline=speech_recognition, status=stopped", 1, "Unable to parse filter."),
        ("status==stopped", 1, "Unable to parse filter."),
    ],
)
def test_cli_batch_rm(
    filters: str, expected_exit_code: int, expected_output: str
) -> None:
    # Mock/fixture requests.delete

    with CliRunner() as runner:
        result = runner.invoke(["batch", "rm", "--filters", f"{filters}"])
        assert result.exit_code == expected_exit_code
        assert expected_output in result.output
