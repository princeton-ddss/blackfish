import pytest
import requests
from unittest.mock import patch, Mock
from app.cli.__main__ import main


@pytest.mark.parametrize(
    "profile, image, refresh, mock_response, expected_exit_code, expected_in_output",
    [
        # Basic successful request with models
        (
            None,
            None,
            False,
            {
                "json": [
                    {
                        "repo": "openai/whisper-large-v3",
                        "revision": "main",
                        "profile": "default",
                        "image": "speech-recognition",
                    },
                    {
                        "repo": "microsoft/DialoGPT-medium",
                        "revision": "main",
                        "profile": "default",
                        "image": "text-generation",
                    },
                ],
                "status_code": 200,
            },
            0,
            "openai/whisper-large-v3",
        ),
        # Empty response - no models found
        (
            "default",
            None,
            False,
            {"json": [], "status_code": 200},
            0,
            "No models found",
        ),
        # Server error
        (
            None,
            "text-generation",
            False,
            {"json": {}, "status_code": 500},
            0,
            "Blackfish API encountered an error: 500",
        ),
        # With profile filter
        (
            "test-profile",
            None,
            False,
            {
                "json": [
                    {
                        "repo": "microsoft/DialoGPT-medium",
                        "revision": "main",
                        "profile": "test-profile",
                        "image": "text-generation",
                    }
                ],
                "status_code": 200,
            },
            0,
            "microsoft/DialoGPT-medium",
        ),
        # With image filter and refresh
        (
            None,
            "speech-recognition",
            True,
            {
                "json": [
                    {
                        "repo": "openai/whisper-base",
                        "revision": "main",
                        "profile": "default",
                        "image": "speech-recognition",
                    }
                ],
                "status_code": 200,
            },
            0,
            "openai/whisper-base",
        ),
        # Profile warning when no models found for specific profile
        (
            "admin",  # not in profile.cfg
            None,
            False,
            {"json": [], "status_code": 200},
            0,
            "No models found.",
        ),
    ],
)
def test_list_models(
    cli_runner,
    mock_config,
    profile: str,
    image: str,
    refresh: bool,
    mock_response: dict,
    expected_exit_code: int,
    expected_in_output: str,
) -> None:
    """Test `blackfish model ls` command."""

    # Prepare command
    cmd = ["model", "ls"]
    if profile:
        cmd.extend(["-p", profile])
    if image:
        cmd.extend(["-t", image])
    if refresh:
        cmd.append("-r")

    with patch("app.cli.__main__.requests.get") as mock_get:
        mock_response_obj = Mock()
        mock_response_obj.ok = mock_response["status_code"] == 200
        mock_response_obj.status_code = mock_response["status_code"]
        mock_response_obj.json.return_value = mock_response["json"]
        mock_get.return_value = mock_response_obj

        result = cli_runner.invoke(main, cmd)

    # Verify request was made with correct parameters
    mock_get.assert_called_once()
    call_url = mock_get.call_args[0][0]
    assert f"http://{mock_config.HOST}:{mock_config.PORT}/api/models" in call_url
    assert f"refresh={refresh}" in call_url
    if profile:
        assert f"profile={profile}" in call_url
    if image:
        assert f"image={image}" in call_url

    assert result.exit_code == expected_exit_code
    assert expected_in_output in result.output


@pytest.mark.parametrize(
    "repo_id, profile, revision, use_cache, profile_exists, is_local_profile, "
    "add_model_success, mock_post_response, expected_exit_code, expected_in_output",
    [
        # Successful model addition
        (
            "openai/whisper-large-v3",
            "default",
            None,
            False,
            True,
            True,
            True,
            {"status_code": 200},
            0,
            "Added model openai/whisper-large-v3",
        ),
        # Profile not found
        (
            "openai/whisper-large-v3",
            "nonexistent",
            None,
            False,
            False,
            True,
            True,
            {"status_code": 200},
            0,
            "Profile not found",
        ),
        # Non-local Slurm profile
        (
            "openai/whisper-large-v3",
            "slurm-remote",
            None,
            False,
            True,
            False,
            True,
            {"status_code": 200},
            0,
            "Blackfish can only manage models for local profiles",
        ),
        # Model download fails
        (
            "invalid/model",
            "default",
            None,
            False,
            True,
            True,
            False,
            {"status_code": 200},
            0,
            "Failed to download model invalid/model",
        ),
        # Database insertion fails
        (
            "openai/whisper-large-v3",
            "default",
            "v2.0",
            True,
            True,
            True,
            True,
            {"status_code": 500, "reason": "Internal Server Error"},
            0,
            "Failed to insert model openai/whisper-large-v3",
        ),
        # With revision and cache
        (
            "microsoft/DialoGPT-medium",
            "test-profile",
            "v1.0",
            True,
            True,
            True,
            True,
            {"status_code": 200},
            0,
            "Added model microsoft/DialoGPT-medium",
        ),
    ],
)
def test_add_model(
    cli_runner,
    mock_config,
    repo_id: str,
    profile: str,
    revision: str,
    use_cache: bool,
    profile_exists: bool,
    is_local_profile: bool,
    add_model_success: bool,
    mock_post_response: dict,
    expected_exit_code: int,
    expected_in_output: str,
) -> None:
    """Test `blackfish model add` command."""

    # Prepare command
    cmd = ["model", "add", repo_id]
    if profile != "default":
        cmd.extend(["-p", profile])
    if revision:
        cmd.extend(["-r", revision])
    if use_cache:
        cmd.append("-c")

    with (
        patch("app.models.profile.deserialize_profile") as mock_deserialize_profile,
        patch("app.models.model.add_model") as mock_add_model,
        patch("app.cli.__main__.requests.post") as mock_post,
    ):
        # Mock profile deserialization
        if not profile_exists:
            mock_deserialize_profile.return_value = None
        else:
            mock_profile = Mock()
            mock_profile.name = profile
            if is_local_profile:
                mock_profile.is_local.return_value = True
                mock_deserialize_profile.return_value = mock_profile
            else:
                # Mock SlurmProfile that's not local
                from app.models.profile import SlurmProfile

                mock_profile = Mock(spec=SlurmProfile)
                mock_profile.is_local.return_value = False
                mock_deserialize_profile.return_value = mock_profile

        # Mock add_model function
        if add_model_success:
            mock_model = Mock()
            mock_model.repo = repo_id
            mock_model.profile = profile
            mock_model.revision = revision or "main"
            mock_model.image = "text-generation"
            mock_add_model.return_value = (mock_model, "/path/to/model")
        else:
            mock_add_model.side_effect = Exception("Download failed")

        # Mock requests.post
        mock_response_obj = Mock()
        mock_response_obj.ok = mock_post_response["status_code"] == 200
        mock_response_obj.status_code = mock_post_response["status_code"]
        mock_response_obj.reason = mock_post_response.get("reason", "OK")
        mock_post.return_value = mock_response_obj

        result = cli_runner.invoke(main, cmd)

        # Verify calls made appropriately
        mock_deserialize_profile.assert_called_once_with(mock_config.HOME_DIR, profile)

        if profile_exists and is_local_profile:
            mock_add_model.assert_called_once()
            if add_model_success:
                mock_post.assert_called_once()

        assert result.exit_code == expected_exit_code
        assert expected_in_output in result.output


@pytest.mark.parametrize(
    "repo_id, profile, revision, use_cache, profile_exists, is_local_profile, "
    "remove_model_success, expected_exit_code, expected_in_output",
    [
        # Successful model removal
        (
            "openai/whisper-large-v3",
            "default",
            None,
            False,
            True,
            True,
            True,
            0,
            "Removed model openai/whisper-large-v3",
        ),
        # Profile not found
        (
            "openai/whisper-large-v3",
            "nonexistent",
            None,
            False,
            False,
            True,
            True,
            0,
            "Profile not found",
        ),
        # Non-local Slurm profile
        (
            "openai/whisper-large-v3",
            "slurm-remote",
            None,
            False,
            True,
            False,
            True,
            0,
            "Blackfish can only manage models for local profiles",
        ),
        # Model removal fails
        (
            "nonexistent/model",
            "default",
            None,
            False,
            True,
            True,
            False,
            0,
            "Failed to remove model",
        ),
        # With revision and cache
        (
            "microsoft/DialoGPT-medium",
            "test-profile",
            "v1.0",
            True,
            True,
            True,
            True,
            0,
            "Removed model microsoft/DialoGPT-medium",
        ),
    ],
)
def test_remove_model(
    cli_runner,
    mock_config,
    repo_id: str,
    profile: str,
    revision: str,
    use_cache: bool,
    profile_exists: bool,
    is_local_profile: bool,
    remove_model_success: bool,
    expected_exit_code: int,
    expected_in_output: str,
) -> None:
    """Test `blackfish model rm` command."""

    # Prepare command
    cmd = ["model", "rm", repo_id]
    if profile != "default":
        cmd.extend(["-p", profile])
    if revision:
        cmd.extend(["-r", revision])
    if use_cache:
        cmd.append("-c")

    with (
        patch("app.models.profile.deserialize_profile") as mock_deserialize_profile,
        patch("app.models.model.remove_model") as mock_remove_model,
    ):
        # Mock profile deserialization
        if not profile_exists:
            mock_deserialize_profile.return_value = None
        else:
            mock_profile = Mock()
            mock_profile.name = profile
            if is_local_profile:
                mock_profile.is_local.return_value = True
                mock_deserialize_profile.return_value = mock_profile
            else:
                # Mock SlurmProfile that's not local
                from app.models.profile import SlurmProfile

                mock_profile = Mock(spec=SlurmProfile)
                mock_profile.is_local.return_value = False
                mock_deserialize_profile.return_value = mock_profile

        # Mock remove_model function
        if not remove_model_success:
            mock_remove_model.side_effect = Exception("Model not found")

        result = cli_runner.invoke(main, cmd)

        # Verify calls made appropriately
        mock_deserialize_profile.assert_called_once_with(mock_config.HOME_DIR, profile)

        if profile_exists and is_local_profile:
            if remove_model_success:
                mock_remove_model.assert_called_once_with(
                    repo_id,
                    profile=mock_profile,
                    revision=revision,
                    use_cache=use_cache,
                )
            else:
                mock_remove_model.assert_called_once()

        assert result.exit_code == expected_exit_code
        assert expected_in_output in result.output


# Additional edge case tests for Click argument validation
@pytest.mark.parametrize(
    "cmd, expected_exit_code, expected_in_output",
    [
        # Missing repo_id for add command
        (["model", "add"], 2, "Missing argument"),
        # Missing repo-id for rm command
        (["model", "rm"], 2, "Missing argument"),
    ],
)
def test_missing_required_arguments(
    cli_runner, cmd, expected_exit_code, expected_in_output
):
    """Test that required arguments are validated by Click."""
    result = cli_runner.invoke(main, cmd)

    assert result.exit_code == expected_exit_code
    assert expected_in_output in result.output or "Usage:" in result.output


def test_list_models_connection_error(cli_runner):
    """Test that connection errors are handled gracefully."""

    with (
        patch("app.config.config") as mock_config,
        patch("app.cli.__main__.requests.get") as mock_get,
    ):
        # Mock config
        mock_config.HOST = "localhost"
        mock_config.PORT = "8080"  # wrong port

        # Mock requests.post raises ConnectionError
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        result = cli_runner.invoke(main, ["model", "ls"])

        assert "Failed to connect" in result.output
        assert result.exit_code == 0


def test_add_model_connection_error(cli_runner):
    with (
        patch("app.models.profile.deserialize_profile") as mock_deserialize_profile,
        patch("app.models.model.add_model") as mock_add_model,
        patch("app.cli.__main__.requests.post") as mock_post,
        patch("app.config.config") as mock_config,
    ):
        # Mock config
        mock_config.HOST = "localhost"
        mock_config.PORT = "8080"  # wrong port

        # Mock profile deserialization
        mock_profile = Mock()
        mock_profile.name = "test"
        mock_profile.is_local.return_value = True
        mock_deserialize_profile.return_value = mock_profile

        # Mock add model
        mock_model = Mock()
        mock_model.repo = "openai/whisper-tiny"
        mock_model.profile = "default"
        mock_model.revision = "main"
        mock_model.image = "speech-recognition"
        mock_add_model.return_value = (mock_model, "/path/to/model")

        # Mock requests.post raises ConnectionError
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

        result = cli_runner.invoke(main, ["model", "add", "openai/whisper-tiny"])

        assert "Failed to connect" in result.output
        assert result.exit_code == 0
