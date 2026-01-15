import pytest
from click.testing import CliRunner


@pytest.fixture()
def cli_runner() -> CliRunner:
    return CliRunner()


# @pytest.mark.parametrize(
#     "profile, mount, repo_id, revision, expected_exit_code, expected_output",
#     [
#         ("not_a_profile", "test", "openai/whisper-large-v3", None, 0, ""),
#         ("test", None, "openai/whisper-large-v3", None, 0, ""),
#         ("test", "test", "not_a_repo_id", None, 0, ""),
#         ("test", "test", "openai/whisper-large-v3", None, 0, ""),
#         ("test-slurm", "test", "openai/whisper-large-v3", None, 0, ""),
#     ],
# )
# def test_cli_batch_speech_recognition(
#     profile: str,
#     mount: str,
#     repo_id: str,
#     revision: str,
#     expected_exit_code: int,
#     expected_output: str,
# ) -> None:
#     # Mock/fixture deserialize_profile, get_models, get_latest_commit, get_model_dir
#     # Mock/fixture requests.post, etc.

#     with CliRunner() as runner:
#         result = runner.invoke(
#             [
#                 "batch",
#                 "--profile",
#                 profile,  # None => log error, return None, Exit Code?
#                 "--mount",
#                 mount,
#                 "--speech-recognition",
#                 repo_id,  # None => log error, return None, Exit Code?
#                 "--revision",
#                 revision,
#                 "--dry-run",
#             ]
#         )
#         assert result.exit_code == expected_exit_code
#         assert expected_output in result.output


# # Improper filter format => exit code 0?, "Unable to parse filter: {e}"
# # Proper filters => exit code 0, "(List of batch jobs based on fixture data and filters and running jobs only!)"
# # --all => exit code 0, "(List of all batch jobs based on fixture data)"
# # --all w/ filters => exit code 0, "(List of all batch jobs based on fixture data and filters)"
# @pytest.mark.parametrize(
#     "filters, all, expected_exit_code, expected_output", [
#         ("", False, 0, ""),
#         ("", True, 0, ""),
#     ],
# )
# def test_cli_batch_ls(filters: str, all: bool, expected_exit_code: int, expected_output: str) -> None:
#     # Mock/fixture requests.get

#     with CliRunner() as runner:
#         if all:
#             result = runner.invoke(["batch", "ls", "--filters", filters, "--all"])
#         else:
#             result = runner.invoke(["batch", "ls", "--filters", filters])

#         assert result.exit_code == 0
#         assert "No batch jobs found." in result.output or "Batch jobs:" in result.output


# @pytest.mark.parametrize(
#     "job_id, expected_exit_code, expected_output",
#     [
#         (None, 2, ""),
#         ("not_a_job_id", 0, "Failed to stop batch job..."),
#         ("12345", 0, "Stopped batch job 12345/"),
#     ],
# )
# def test_cli_batch_stop(job_id: str, expected_exit_code: int, expected_output: str) -> None:
#     # Mock/fixture requests.put

#     with CliRunner() as runner:
#         result = runner.invoke(["batch", "stop", "12345"])
#         assert result.exit_code == expected_exit_code
#         assert expected_output in result.output


@pytest.mark.parametrize()
def test_cli_batch_speech_recognition():
    pass


@pytest.mark.parametrize(
    "job_id, mock_response, expected_exit_code, expected_in_output",
    [
        # No job provided
        (None, None, 2, None),
        # Invalid job provided
        (
            "not_a_job",
            {"detail": "Job not_a_job not found", "status_code": 404},
            0,
            "Failed to stop batch job not_a_job",
        ),
        # Success with valid job ID
        (
            "12345",
            {
                "json": {
                    "name": "test",  # Mapped[str]
                    "pipeline": "speech_recognition",  # Mapped[str]
                    "repo_id": "open-ai/whisper-large-v3",  # Mapped[str]
                    "profile": "default",  # Mapped[str]
                    "user": "test",  # Mapped[Optional[str]]
                    "host": "localhost",  # Mapped[Optional[str]]
                    "home_dir": "/home/calvin/.blackfish",  # Mapped[Optional[str]]
                    "cache_dir": "/home/calvin/.blackfish",  # Mapped[Optional[str]]
                    "job_id": "12345",  # Mapped[Optional[str]]
                    "status": "healthy",  # Mapped[Optional[BatchJobStatus]]
                    "ntotal": 1,  # Mapped[Optional[int]]
                    "nsuccess": 1,  # Mapped[Optional[int]]
                    "nfail": 0,  # Mapped[Optional[int]]
                    "scheduler": "slurm",  # Mapped[Optional[str]]
                    "provider": None,  # Mapped[Optional[ContainerProvider]]
                    "mount": "/home/calvin",  # Mapped[Optional[str]]
                },
                "status_code": 200,
            },
            0,
            "Stopped batch job 12345.",
        ),
        # Error with valid job ID
        (
            "12345",
            {"detail": "An error occurred while stopping the job.", "status_code": 500},
            0,
            "Failed to stop batch job 12345",
        ),
    ],
)
def test_cli_batch_stop(
    cli_runner,
    job_id: str,
    mock_response: dict,
    expected_exit_code: int,
    expected_in_output: str,
) -> None:
    """Test the batch rm command with various filter scenarios."""
    from unittest.mock import patch, Mock
    from blackfish.cli.__main__ import main

    # Prepare the command
    cmd = ["batch", "stop"]
    if job_id is None:
        result = cli_runner.invoke(main, cmd)
        assert result.exit_code == expected_exit_code
        return

    # Mock the requests.put call
    with (
        patch("blackfish.cli.__main__.requests.put") as mock_put,
        patch("blackfish.cli.__main__.config") as mock_config,
        patch(
            "blackfish.server.models.profile.deserialize_profile"
        ) as mock_deserialize_profile,
    ):
        mock_response_obj = Mock()
        mock_response_obj.ok = mock_response["status_code"] == 200
        mock_response_obj.status_code = mock_response["status_code"]
        if mock_response["status_code"] == 200:
            mock_response_obj.json.return_value = mock_response["json"]
        else:
            mock_response_obj.json.return_value = mock_response["detail"]
        mock_put.return_value = mock_response_obj

        # Mock config values
        mock_config.HOST = "localhost"
        mock_config.PORT = 8000
        mock_config.HOME_DIR = "/tmp/blackfish-test"

        # Mock profile deserialization to return a valid profile
        mock_profile = Mock()
        mock_profile.name = "default"
        mock_deserialize_profile.return_value = mock_profile

        # Invoke the command
        cmd.append(job_id)
        result = cli_runner.invoke(main, cmd)

        # Check the result
        mock_put.assert_called_once()
        mock_url = (
            f"http://{mock_config.HOST}:{mock_config.PORT}/api/jobs/{job_id}/stop"
        )
        assert mock_put.call_args[0][0] == mock_url
        assert result.exit_code == expected_exit_code
        assert expected_in_output in result.output


@pytest.mark.parametrize(
    "filters, mock_response, expected_exit_code, expected_in_output",
    [
        # No filters provided - should succeed with empty response
        (
            None,
            {"json": [], "status_code": 200},
            0,
            "Query did not match any batch jobs",
        ),
        # Valid filters with successful deletion
        (
            "id=12345",
            {"json": [{"status": "ok", "id": "12345"}], "status_code": 200},
            0,
            "Removed 1 batch job",
        ),
        # Multiple successful deletions
        (
            "pipeline=speech_recognition",
            {
                "json": [
                    {"status": "ok", "id": "12345"},
                    {"status": "ok", "id": "67890"},
                ],
                "status_code": 200,
            },
            0,
            "Removed 2 batch jobs",
        ),
        # Mixed success and errors
        (
            "status=stopped",
            {
                "json": [
                    {"status": "ok", "id": "12345"},
                    {"status": "error", "id": "67890", "message": "Job is running"},
                ],
                "status_code": 200,
            },
            0,
            "Removed 1 batch job",
        ),
        # Invalid filter format with spaces
        ("stopped", None, 1, "Unable to parse filter"),
        # Invalid filter format with double equals
        ("status==stopped", None, 1, "Unable to parse filter"),
        # Server error
        (
            "id=12345",
            {"json": {}, "status_code": 500},
            0,
            "An error occurred while attempting to remove batch jobs",
        ),
        # Valid complex filters
        (
            "pipeline=speech_recognition,status=stopped",
            {"json": [{"status": "ok", "id": "12345"}], "status_code": 200},
            0,
            "Removed 1 batch job",
        ),
    ],
)
def test_cli_batch_rm(
    cli_runner,
    filters: str,
    mock_response: dict,
    expected_exit_code: int,
    expected_in_output: str,
) -> None:
    """Test the batch rm command with various filter scenarios."""
    from unittest.mock import patch, Mock
    from blackfish.cli.__main__ import main

    # Prepare the command
    cmd = ["batch", "rm"]
    if filters is not None:
        cmd.extend(["--filters", filters])

    # Test invalid filter parsing (should exit before making request)
    if expected_exit_code == 1:
        result = cli_runner.invoke(main, cmd)
        assert result.exit_code == expected_exit_code
        assert expected_in_output in result.output
        return

    # Mock the requests.delete call for valid cases
    with (
        patch("blackfish.cli.__main__.requests.delete") as mock_delete,
        patch("blackfish.cli.__main__.config") as mock_config,
        patch(
            "blackfish.server.models.profile.deserialize_profile"
        ) as mock_deserialize_profile,
    ):
        mock_response_obj = Mock()
        mock_response_obj.ok = mock_response["status_code"] == 200
        mock_response_obj.status_code = mock_response["status_code"]
        mock_response_obj.json.return_value = mock_response["json"]
        mock_delete.return_value = mock_response_obj

        # Mock config values
        mock_config.HOST = "localhost"
        mock_config.PORT = 8000
        mock_config.HOME_DIR = "/tmp/blackfish-test"

        # Mock profile deserialization to return a valid profile
        mock_profile = Mock()
        mock_profile.name = "default"
        mock_deserialize_profile.return_value = mock_profile

        result = cli_runner.invoke(main, cmd)

        # Verify the request was made with correct parameters
        if filters:
            try:
                expected_params = {
                    k: v for k, v in map(lambda x: x.split("="), filters.split(","))
                }
                mock_delete.assert_called_once()
                call_args = mock_delete.call_args
                assert call_args[1]["params"] == expected_params
            except ValueError:
                # This shouldn't happen for valid filters in this test
                pass
        else:
            mock_delete.assert_called_once_with(
                "http://localhost:8000/api/jobs", params=None
            )

        assert result.exit_code == expected_exit_code
        assert expected_in_output in result.output


def test_cli_batch_rm_with_errors_displayed(cli_runner):
    """Test that error details are properly displayed when some deletions fail."""
    from unittest.mock import patch, Mock
    from blackfish.cli.__main__ import main

    # Mock response with errors
    mock_response_data = [
        {"status": "ok", "id": "12345"},
        {"status": "error", "id": "67890", "message": "Job is currently running"},
        {"status": "error", "id": "abcdef", "message": "Permission denied"},
    ]

    with (
        patch("blackfish.cli.__main__.requests.delete") as mock_delete,
        patch("blackfish.cli.__main__.config") as mock_config,
        patch(
            "blackfish.server.models.profile.deserialize_profile"
        ) as mock_deserialize_profile,
    ):
        mock_response_obj = Mock()
        mock_response_obj.ok = True
        mock_response_obj.status_code = 200
        mock_response_obj.json.return_value = mock_response_data
        mock_delete.return_value = mock_response_obj

        # Mock config values
        mock_config.HOST = "localhost"
        mock_config.PORT = 8000

        # Mock profile deserialization to return a valid profile
        mock_profile = Mock()
        mock_profile.name = "default"
        mock_deserialize_profile.return_value = mock_profile

        result = cli_runner.invoke(main, ["batch", "rm", "--filters", "status=stopped"])

        assert result.exit_code == 0
        # Check that success message is shown
        assert "Removed 1 batch job" in result.output
        # Check that error summary is shown
        assert "Failed to delete 2 batch jobs" in result.output
        # Check that individual error details are shown
        assert "67890 - Job is currently running" in result.output
        assert "abcdef - Permission denied" in result.output


@pytest.mark.parametrize()
def test_cli_batch_ls():
    pass
