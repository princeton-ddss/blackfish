"""Tests for the `blackfish run` command group.

This module tests the CLI commands for running inference services:
- `blackfish run text-generation` - Start a text generation service
- `blackfish run speech-recognition` - Start a speech recognition service
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
from blackfish.cli.__main__ import main
from blackfish.server.models.profile import LocalProfile, SlurmProfile


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def local_profile():
    """Create a LocalProfile for testing."""
    return LocalProfile(
        name="default",
        home_dir="/tmp/blackfish",
        cache_dir="/tmp/blackfish/cache",
    )


@pytest.fixture
def slurm_profile():
    """Create a SlurmProfile for testing."""
    return SlurmProfile(
        name="cluster",
        host="hpc.example.com",
        user="testuser",
        home_dir="/home/testuser/.blackfish",
        cache_dir="/scratch/testuser/cache",
    )


# =============================================================================
# Tests: run text-generation
# =============================================================================


class TestRunTextGeneration:
    """Tests for the `blackfish run text-generation` command."""

    def test_profile_not_found(self, cli_runner, mock_config):
        """Test error message when profile is not found."""
        cmd = ["run", "-p", "nonexistent", "text-generation", "openai/gpt-2"]

        with patch(
            "blackfish.server.models.profile.deserialize_profile"
        ) as mock_deserialize:
            mock_deserialize.return_value = None

            result = cli_runner.invoke(main, cmd)

        assert "Profile not found" in result.output

    def test_model_not_found(self, cli_runner, mock_config, local_profile):
        """Test error message when model is not available for the profile."""
        cmd = ["run", "-p", "default", "text-generation", "openai/gpt-2"]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.text_generation.get_models"
            ) as mock_get_models,
        ):
            mock_deserialize.return_value = local_profile
            mock_get_models.return_value = []  # No models available

            result = cli_runner.invoke(main, cmd)

        assert "Unable to find openai/gpt-2" in result.output

    def test_dry_run_local_profile(self, cli_runner, mock_config, local_profile):
        """Test dry run with LocalProfile renders job script."""
        cmd = [
            "run",
            "-p",
            "default",
            "text-generation",
            "openai/gpt-2",
            "--dry-run",
        ]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.text_generation.get_models"
            ) as mock_get_models,
            patch(
                "blackfish.cli.services.text_generation.get_revisions"
            ) as mock_get_revisions,
            patch(
                "blackfish.cli.services.text_generation.get_latest_commit"
            ) as mock_get_latest,
            patch(
                "blackfish.cli.services.text_generation.get_model_dir"
            ) as mock_get_model_dir,
            patch(
                "blackfish.cli.services.text_generation.TextGeneration"
            ) as mock_service_class,
        ):
            mock_deserialize.return_value = local_profile
            mock_get_models.return_value = ["openai/gpt-2"]
            mock_get_revisions.return_value = ["abc123"]
            mock_get_latest.return_value = "abc123"
            mock_get_model_dir.return_value = "/path/to/model"

            mock_service = MagicMock()
            mock_service.image = "text_generation"
            mock_service.render_job_script.return_value = "#!/bin/bash\necho test"
            mock_service_class.return_value = mock_service

            result = cli_runner.invoke(main, cmd)

        assert "Rendering job script" in result.output
        assert "model: openai/gpt-2" in result.output
        assert "profile: default" in result.output

    def test_dry_run_slurm_profile(self, cli_runner, mock_config, slurm_profile):
        """Test dry run with SlurmProfile renders job script."""
        cmd = [
            "run",
            "-p",
            "cluster",
            "text-generation",
            "openai/gpt-2",
            "--dry-run",
        ]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.text_generation.get_models"
            ) as mock_get_models,
            patch(
                "blackfish.cli.services.text_generation.get_revisions"
            ) as mock_get_revisions,
            patch(
                "blackfish.cli.services.text_generation.get_latest_commit"
            ) as mock_get_latest,
            patch(
                "blackfish.cli.services.text_generation.get_model_dir"
            ) as mock_get_model_dir,
            patch(
                "blackfish.cli.services.text_generation.TextGeneration"
            ) as mock_service_class,
        ):
            mock_deserialize.return_value = slurm_profile
            mock_get_models.return_value = ["openai/gpt-2"]
            mock_get_revisions.return_value = ["abc123"]
            mock_get_latest.return_value = "abc123"
            mock_get_model_dir.return_value = "/path/to/model"

            mock_service = MagicMock()
            mock_service.scheduler = "slurm"
            mock_service.render_job_script.return_value = "#!/bin/bash\n#SBATCH"
            mock_service_class.return_value = mock_service

            result = cli_runner.invoke(main, cmd)

        assert "Rendering job script" in result.output
        assert "model: openai/gpt-2" in result.output
        assert "profile: cluster" in result.output
        assert "host: hpc.example.com" in result.output

    def test_success_local_profile(self, cli_runner, mock_config, local_profile):
        """Test successful API call with LocalProfile."""
        cmd = ["run", "-p", "default", "text-generation", "openai/gpt-2"]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.text_generation.get_models"
            ) as mock_get_models,
            patch(
                "blackfish.cli.services.text_generation.get_revisions"
            ) as mock_get_revisions,
            patch(
                "blackfish.cli.services.text_generation.get_latest_commit"
            ) as mock_get_latest,
            patch(
                "blackfish.cli.services.text_generation.get_model_dir"
            ) as mock_get_model_dir,
            patch("blackfish.cli.services.text_generation.requests.post") as mock_post,
        ):
            mock_deserialize.return_value = local_profile
            mock_get_models.return_value = ["openai/gpt-2"]
            mock_get_revisions.return_value = ["abc123"]
            mock_get_latest.return_value = "abc123"
            mock_get_model_dir.return_value = "/path/to/model"

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {"id": "service-uuid-123"}
            mock_post.return_value = mock_response

            result = cli_runner.invoke(main, cmd)

        assert "Started service" in result.output
        mock_post.assert_called_once()

    def test_success_slurm_profile(self, cli_runner, mock_config, slurm_profile):
        """Test successful API call with SlurmProfile."""
        cmd = ["run", "-p", "cluster", "text-generation", "openai/gpt-2"]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.text_generation.get_models"
            ) as mock_get_models,
            patch(
                "blackfish.cli.services.text_generation.get_revisions"
            ) as mock_get_revisions,
            patch(
                "blackfish.cli.services.text_generation.get_latest_commit"
            ) as mock_get_latest,
            patch(
                "blackfish.cli.services.text_generation.get_model_dir"
            ) as mock_get_model_dir,
            patch("blackfish.cli.services.text_generation.requests.post") as mock_post,
        ):
            mock_deserialize.return_value = slurm_profile
            mock_get_models.return_value = ["openai/gpt-2"]
            mock_get_revisions.return_value = ["abc123"]
            mock_get_latest.return_value = "abc123"
            mock_get_model_dir.return_value = "/path/to/model"

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {"id": "service-uuid-123"}
            mock_post.return_value = mock_response

            result = cli_runner.invoke(main, cmd)

        assert "Started service" in result.output
        mock_post.assert_called_once()

    def test_api_failure(self, cli_runner, mock_config, local_profile):
        """Test API failure response handling."""
        cmd = ["run", "-p", "default", "text-generation", "openai/gpt-2"]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.text_generation.get_models"
            ) as mock_get_models,
            patch(
                "blackfish.cli.services.text_generation.get_revisions"
            ) as mock_get_revisions,
            patch(
                "blackfish.cli.services.text_generation.get_latest_commit"
            ) as mock_get_latest,
            patch(
                "blackfish.cli.services.text_generation.get_model_dir"
            ) as mock_get_model_dir,
            patch("blackfish.cli.services.text_generation.requests.post") as mock_post,
        ):
            mock_deserialize.return_value = local_profile
            mock_get_models.return_value = ["openai/gpt-2"]
            mock_get_revisions.return_value = ["abc123"]
            mock_get_latest.return_value = "abc123"
            mock_get_model_dir.return_value = "/path/to/model"

            mock_response = Mock()
            mock_response.ok = False
            mock_response.status_code = 500
            mock_response.reason = "Internal Server Error"
            mock_post.return_value = mock_response

            result = cli_runner.invoke(main, cmd)

        assert "Failed to start service" in result.output

    def test_missing_repo_id(self, cli_runner, mock_config, local_profile):
        """Test error when repo_id argument is missing."""
        cmd = ["run", "-p", "default", "text-generation"]

        with patch(
            "blackfish.server.models.profile.deserialize_profile"
        ) as mock_deserialize:
            mock_deserialize.return_value = local_profile

            result = cli_runner.invoke(main, cmd)

        assert result.exit_code == 2
        assert "Missing argument" in result.output

    def test_with_custom_options(self, cli_runner, mock_config, local_profile):
        """Test command with custom name, revision, and port options."""
        cmd = [
            "run",
            "-p",
            "default",
            "text-generation",
            "openai/gpt-2",
            "--name",
            "my-service",
            "--revision",
            "v1.0",
            "--port",
            "9000",
        ]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.text_generation.get_models"
            ) as mock_get_models,
            patch(
                "blackfish.cli.services.text_generation.get_model_dir"
            ) as mock_get_model_dir,
            patch("blackfish.cli.services.text_generation.requests.post") as mock_post,
        ):
            mock_deserialize.return_value = local_profile
            mock_get_models.return_value = ["openai/gpt-2"]
            mock_get_model_dir.return_value = "/path/to/model"

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {"id": "service-uuid-123"}
            mock_post.return_value = mock_response

            result = cli_runner.invoke(main, cmd)

        assert "Started service" in result.output
        # Verify the API was called with correct parameters
        call_args = mock_post.call_args
        assert call_args[1]["json"]["name"] == "my-service"
        assert call_args[1]["json"]["container_config"]["port"] == 9000
        assert call_args[1]["json"]["container_config"]["revision"] == "v1.0"

    def test_with_vllm_extra_args(self, cli_runner, mock_config, local_profile):
        """Test that extra vLLM arguments are passed through."""
        cmd = [
            "run",
            "-p",
            "default",
            "text-generation",
            "openai/gpt-2",
            "--",
            "--api-key",
            "secret",
            "--seed",
            "42",
        ]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.text_generation.get_models"
            ) as mock_get_models,
            patch(
                "blackfish.cli.services.text_generation.get_revisions"
            ) as mock_get_revisions,
            patch(
                "blackfish.cli.services.text_generation.get_latest_commit"
            ) as mock_get_latest,
            patch(
                "blackfish.cli.services.text_generation.get_model_dir"
            ) as mock_get_model_dir,
            patch("blackfish.cli.services.text_generation.requests.post") as mock_post,
        ):
            mock_deserialize.return_value = local_profile
            mock_get_models.return_value = ["openai/gpt-2"]
            mock_get_revisions.return_value = ["abc123"]
            mock_get_latest.return_value = "abc123"
            mock_get_model_dir.return_value = "/path/to/model"

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {"id": "service-uuid-123"}
            mock_post.return_value = mock_response

            result = cli_runner.invoke(main, cmd)

        assert "Started service" in result.output
        # Verify launch_kwargs contains the extra arguments
        call_args = mock_post.call_args
        launch_kwargs = call_args[1]["json"]["container_config"]["launch_kwargs"]
        assert "--api-key" in launch_kwargs
        assert "secret" in launch_kwargs
        assert "--seed" in launch_kwargs
        assert "42" in launch_kwargs

    def test_no_revision_uses_latest(self, cli_runner, mock_config, local_profile):
        """Test that when no revision is provided, the latest commit is used."""
        cmd = ["run", "-p", "default", "text-generation", "openai/gpt-2"]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.text_generation.get_models"
            ) as mock_get_models,
            patch(
                "blackfish.cli.services.text_generation.get_revisions"
            ) as mock_get_revisions,
            patch(
                "blackfish.cli.services.text_generation.get_latest_commit"
            ) as mock_get_latest,
            patch(
                "blackfish.cli.services.text_generation.get_model_dir"
            ) as mock_get_model_dir,
            patch("blackfish.cli.services.text_generation.requests.post") as mock_post,
        ):
            mock_deserialize.return_value = local_profile
            mock_get_models.return_value = ["openai/gpt-2"]
            mock_get_revisions.return_value = ["abc123", "def456"]
            mock_get_latest.return_value = "abc123"
            mock_get_model_dir.return_value = "/path/to/model"

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {"id": "service-uuid-123"}
            mock_post.return_value = mock_response

            result = cli_runner.invoke(main, cmd)

        assert "No revision provided" in result.output
        assert "abc123" in result.output
        mock_get_latest.assert_called_once()

    def test_model_dir_not_found(self, cli_runner, mock_config, local_profile):
        """Test error when model directory cannot be found."""
        cmd = [
            "run",
            "-p",
            "default",
            "text-generation",
            "openai/gpt-2",
            "--revision",
            "nonexistent",
        ]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.text_generation.get_models"
            ) as mock_get_models,
            patch(
                "blackfish.cli.services.text_generation.get_model_dir"
            ) as mock_get_model_dir,
        ):
            mock_deserialize.return_value = local_profile
            mock_get_models.return_value = ["openai/gpt-2"]
            mock_get_model_dir.return_value = None  # Model dir not found

            result = cli_runner.invoke(main, cmd)

        # Command should exit early without calling API
        assert result.exit_code == 0


# =============================================================================
# Tests: run speech-recognition
# =============================================================================


class TestRunSpeechRecognition:
    """Tests for the `blackfish run speech-recognition` command."""

    def test_profile_not_found(self, cli_runner, mock_config):
        """Test error message when profile is not found."""
        cmd = ["run", "-p", "nonexistent", "speech-recognition", "openai/whisper-tiny"]

        with patch(
            "blackfish.server.models.profile.deserialize_profile"
        ) as mock_deserialize:
            mock_deserialize.return_value = None

            result = cli_runner.invoke(main, cmd)

        assert "Profile not found" in result.output

    def test_model_not_found(self, cli_runner, mock_config, local_profile):
        """Test error message when model is not available for the profile."""
        cmd = ["run", "-p", "default", "speech-recognition", "openai/whisper-tiny"]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.speech_recognition.get_models"
            ) as mock_get_models,
        ):
            mock_deserialize.return_value = local_profile
            mock_get_models.return_value = []  # No models available

            result = cli_runner.invoke(main, cmd)

        assert "Unable to find openai/whisper-tiny" in result.output

    def test_dry_run_local_profile(self, cli_runner, mock_config, local_profile):
        """Test dry run with LocalProfile renders job script."""
        cmd = [
            "run",
            "-p",
            "default",
            "speech-recognition",
            "openai/whisper-tiny",
            "--dry-run",
        ]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.speech_recognition.get_models"
            ) as mock_get_models,
            patch(
                "blackfish.cli.services.speech_recognition.get_revisions"
            ) as mock_get_revisions,
            patch(
                "blackfish.cli.services.speech_recognition.get_latest_commit"
            ) as mock_get_latest,
            patch(
                "blackfish.cli.services.speech_recognition.get_model_dir"
            ) as mock_get_model_dir,
            patch(
                "blackfish.cli.services.speech_recognition.SpeechRecognition"
            ) as mock_service_class,
        ):
            mock_deserialize.return_value = local_profile
            mock_get_models.return_value = ["openai/whisper-tiny"]
            mock_get_revisions.return_value = ["abc123"]
            mock_get_latest.return_value = "abc123"
            mock_get_model_dir.return_value = "/path/to/models/whisper-tiny"

            mock_service = MagicMock()
            mock_service.image = "speech_recognition"
            mock_service.render_job_script.return_value = "#!/bin/bash\necho test"
            mock_service_class.return_value = mock_service

            result = cli_runner.invoke(main, cmd)

        assert "Rendering job script" in result.output
        assert "model: openai/whisper-tiny" in result.output
        assert "profile: default" in result.output

    def test_dry_run_slurm_profile(self, cli_runner, mock_config, slurm_profile):
        """Test dry run with SlurmProfile renders job script."""
        cmd = [
            "run",
            "-p",
            "cluster",
            "speech-recognition",
            "openai/whisper-tiny",
            "--dry-run",
        ]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.speech_recognition.get_models"
            ) as mock_get_models,
            patch(
                "blackfish.cli.services.speech_recognition.get_revisions"
            ) as mock_get_revisions,
            patch(
                "blackfish.cli.services.speech_recognition.get_latest_commit"
            ) as mock_get_latest,
            patch(
                "blackfish.cli.services.speech_recognition.get_model_dir"
            ) as mock_get_model_dir,
            patch(
                "blackfish.cli.services.speech_recognition.SpeechRecognition"
            ) as mock_service_class,
        ):
            mock_deserialize.return_value = slurm_profile
            mock_get_models.return_value = ["openai/whisper-tiny"]
            mock_get_revisions.return_value = ["abc123"]
            mock_get_latest.return_value = "abc123"
            mock_get_model_dir.return_value = "/path/to/models/whisper-tiny"

            mock_service = MagicMock()
            mock_service.scheduler = "slurm"
            mock_service.render_job_script.return_value = "#!/bin/bash\n#SBATCH"
            mock_service_class.return_value = mock_service

            result = cli_runner.invoke(main, cmd)

        assert "Rendering job script" in result.output
        assert "model: openai/whisper-tiny" in result.output
        assert "profile: cluster" in result.output
        assert "host: hpc.example.com" in result.output

    def test_success_local_profile(self, cli_runner, mock_config, local_profile):
        """Test successful API call with LocalProfile."""
        cmd = ["run", "-p", "default", "speech-recognition", "openai/whisper-tiny"]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.speech_recognition.get_models"
            ) as mock_get_models,
            patch(
                "blackfish.cli.services.speech_recognition.get_revisions"
            ) as mock_get_revisions,
            patch(
                "blackfish.cli.services.speech_recognition.get_latest_commit"
            ) as mock_get_latest,
            patch(
                "blackfish.cli.services.speech_recognition.get_model_dir"
            ) as mock_get_model_dir,
            patch(
                "blackfish.cli.services.speech_recognition.requests.post"
            ) as mock_post,
        ):
            mock_deserialize.return_value = local_profile
            mock_get_models.return_value = ["openai/whisper-tiny"]
            mock_get_revisions.return_value = ["abc123"]
            mock_get_latest.return_value = "abc123"
            mock_get_model_dir.return_value = "/path/to/models/whisper-tiny"

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {"id": "service-uuid-123"}
            mock_post.return_value = mock_response

            result = cli_runner.invoke(main, cmd)

        assert "Started service" in result.output
        mock_post.assert_called_once()

    def test_success_slurm_profile(self, cli_runner, mock_config, slurm_profile):
        """Test successful API call with SlurmProfile."""
        cmd = ["run", "-p", "cluster", "speech-recognition", "openai/whisper-tiny"]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.speech_recognition.get_models"
            ) as mock_get_models,
            patch(
                "blackfish.cli.services.speech_recognition.get_revisions"
            ) as mock_get_revisions,
            patch(
                "blackfish.cli.services.speech_recognition.get_latest_commit"
            ) as mock_get_latest,
            patch(
                "blackfish.cli.services.speech_recognition.get_model_dir"
            ) as mock_get_model_dir,
            patch(
                "blackfish.cli.services.speech_recognition.requests.post"
            ) as mock_post,
        ):
            mock_deserialize.return_value = slurm_profile
            mock_get_models.return_value = ["openai/whisper-tiny"]
            mock_get_revisions.return_value = ["abc123"]
            mock_get_latest.return_value = "abc123"
            mock_get_model_dir.return_value = "/path/to/models/whisper-tiny"

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {"id": "service-uuid-123"}
            mock_post.return_value = mock_response

            result = cli_runner.invoke(main, cmd)

        assert "Started service" in result.output
        mock_post.assert_called_once()

    def test_api_failure(self, cli_runner, mock_config, local_profile):
        """Test API failure response handling."""
        cmd = ["run", "-p", "default", "speech-recognition", "openai/whisper-tiny"]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.speech_recognition.get_models"
            ) as mock_get_models,
            patch(
                "blackfish.cli.services.speech_recognition.get_revisions"
            ) as mock_get_revisions,
            patch(
                "blackfish.cli.services.speech_recognition.get_latest_commit"
            ) as mock_get_latest,
            patch(
                "blackfish.cli.services.speech_recognition.get_model_dir"
            ) as mock_get_model_dir,
            patch(
                "blackfish.cli.services.speech_recognition.requests.post"
            ) as mock_post,
        ):
            mock_deserialize.return_value = local_profile
            mock_get_models.return_value = ["openai/whisper-tiny"]
            mock_get_revisions.return_value = ["abc123"]
            mock_get_latest.return_value = "abc123"
            mock_get_model_dir.return_value = "/path/to/models/whisper-tiny"

            mock_response = Mock()
            mock_response.ok = False
            mock_response.status_code = 500
            mock_response.reason = "Internal Server Error"
            mock_post.return_value = mock_response

            result = cli_runner.invoke(main, cmd)

        assert "Failed to start service" in result.output

    def test_missing_repo_id(self, cli_runner, mock_config, local_profile):
        """Test error when repo_id argument is missing."""
        cmd = ["run", "-p", "default", "speech-recognition"]

        with patch(
            "blackfish.server.models.profile.deserialize_profile"
        ) as mock_deserialize:
            mock_deserialize.return_value = local_profile

            result = cli_runner.invoke(main, cmd)

        assert result.exit_code == 2
        assert "Missing argument" in result.output

    def test_with_custom_options(self, cli_runner, mock_config, local_profile):
        """Test command with custom name, revision, and port options."""
        cmd = [
            "run",
            "-p",
            "default",
            "speech-recognition",
            "openai/whisper-tiny",
            "--name",
            "my-whisper",
            "--revision",
            "v1.0",
            "--port",
            "9000",
        ]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.speech_recognition.get_models"
            ) as mock_get_models,
            patch(
                "blackfish.cli.services.speech_recognition.get_model_dir"
            ) as mock_get_model_dir,
            patch(
                "blackfish.cli.services.speech_recognition.requests.post"
            ) as mock_post,
        ):
            mock_deserialize.return_value = local_profile
            mock_get_models.return_value = ["openai/whisper-tiny"]
            mock_get_model_dir.return_value = "/path/to/models/whisper-tiny"

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {"id": "service-uuid-123"}
            mock_post.return_value = mock_response

            result = cli_runner.invoke(main, cmd)

        assert "Started service" in result.output
        # Verify the API was called with correct parameters
        call_args = mock_post.call_args
        assert call_args[1]["json"]["name"] == "my-whisper"
        assert call_args[1]["json"]["container_config"]["port"] == 9000
        assert call_args[1]["json"]["container_config"]["revision"] == "v1.0"

    def test_no_revision_uses_latest(self, cli_runner, mock_config, local_profile):
        """Test that when no revision is provided, the latest commit is used."""
        cmd = ["run", "-p", "default", "speech-recognition", "openai/whisper-tiny"]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.speech_recognition.get_models"
            ) as mock_get_models,
            patch(
                "blackfish.cli.services.speech_recognition.get_revisions"
            ) as mock_get_revisions,
            patch(
                "blackfish.cli.services.speech_recognition.get_latest_commit"
            ) as mock_get_latest,
            patch(
                "blackfish.cli.services.speech_recognition.get_model_dir"
            ) as mock_get_model_dir,
            patch(
                "blackfish.cli.services.speech_recognition.requests.post"
            ) as mock_post,
        ):
            mock_deserialize.return_value = local_profile
            mock_get_models.return_value = ["openai/whisper-tiny"]
            mock_get_revisions.return_value = ["abc123", "def456"]
            mock_get_latest.return_value = "abc123"
            mock_get_model_dir.return_value = "/path/to/models/whisper-tiny"

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {"id": "service-uuid-123"}
            mock_post.return_value = mock_response

            result = cli_runner.invoke(main, cmd)

        assert "No revision provided" in result.output
        assert "abc123" in result.output
        mock_get_latest.assert_called_once()

    def test_mount_defaults_to_home_dir(self, cli_runner, mock_config, local_profile):
        """Test that mount defaults to profile's home_dir when not provided."""
        cmd = ["run", "-p", "default", "speech-recognition", "openai/whisper-tiny"]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.speech_recognition.get_models"
            ) as mock_get_models,
            patch(
                "blackfish.cli.services.speech_recognition.get_revisions"
            ) as mock_get_revisions,
            patch(
                "blackfish.cli.services.speech_recognition.get_latest_commit"
            ) as mock_get_latest,
            patch(
                "blackfish.cli.services.speech_recognition.get_model_dir"
            ) as mock_get_model_dir,
            patch(
                "blackfish.cli.services.speech_recognition.requests.post"
            ) as mock_post,
        ):
            mock_deserialize.return_value = local_profile
            mock_get_models.return_value = ["openai/whisper-tiny"]
            mock_get_revisions.return_value = ["abc123"]
            mock_get_latest.return_value = "abc123"
            mock_get_model_dir.return_value = "/path/to/models/whisper-tiny"

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {"id": "service-uuid-123"}
            mock_post.return_value = mock_response

            result = cli_runner.invoke(main, cmd)

        assert "Started service" in result.output
        # Verify mount is set to profile's home_dir
        call_args = mock_post.call_args
        assert call_args[1]["json"]["mount"] == local_profile.home_dir


# =============================================================================
# Tests: run group options
# =============================================================================


class TestRunGroupOptions:
    """Tests for the `run` command group shared options."""

    def test_resource_options_passed_to_slurm_job_config(
        self, cli_runner, mock_config, slurm_profile
    ):
        """Test that resource options are passed to SlurmJobConfig."""
        cmd = [
            "run",
            "-p",
            "cluster",
            "--time",
            "01:00:00",
            "--ntasks-per-node",
            "16",
            "--mem",
            "32",
            "--gres",
            "2",
            "--partition",
            "gpu",
            "--constraint",
            "gpu80",
            "--account",
            "research",
            "text-generation",
            "openai/gpt-2",
        ]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.text_generation.get_models"
            ) as mock_get_models,
            patch(
                "blackfish.cli.services.text_generation.get_revisions"
            ) as mock_get_revisions,
            patch(
                "blackfish.cli.services.text_generation.get_latest_commit"
            ) as mock_get_latest,
            patch(
                "blackfish.cli.services.text_generation.get_model_dir"
            ) as mock_get_model_dir,
            patch("blackfish.cli.services.text_generation.requests.post") as mock_post,
        ):
            mock_deserialize.return_value = slurm_profile
            mock_get_models.return_value = ["openai/gpt-2"]
            mock_get_revisions.return_value = ["abc123"]
            mock_get_latest.return_value = "abc123"
            mock_get_model_dir.return_value = "/path/to/model"

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {"id": "service-uuid-123"}
            mock_post.return_value = mock_response

            result = cli_runner.invoke(main, cmd)

        assert "Started service" in result.output
        # Verify resource options are in job_config
        call_args = mock_post.call_args
        job_config = call_args[1]["json"]["job_config"]
        assert job_config["time"] == "01:00:00"
        assert job_config["ntasks_per_node"] == 16
        assert job_config["mem"] == 32
        assert job_config["gres"] == 2
        assert job_config["partition"] == "gpu"
        assert job_config["constraint"] == "gpu80"
        assert job_config["account"] == "research"

    def test_mount_option(self, cli_runner, mock_config, local_profile):
        """Test that mount option is passed correctly."""
        cmd = [
            "run",
            "-p",
            "default",
            "--mount",
            "/data/custom",
            "text-generation",
            "openai/gpt-2",
        ]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.text_generation.get_models"
            ) as mock_get_models,
            patch(
                "blackfish.cli.services.text_generation.get_revisions"
            ) as mock_get_revisions,
            patch(
                "blackfish.cli.services.text_generation.get_latest_commit"
            ) as mock_get_latest,
            patch(
                "blackfish.cli.services.text_generation.get_model_dir"
            ) as mock_get_model_dir,
            patch("blackfish.cli.services.text_generation.requests.post") as mock_post,
        ):
            mock_deserialize.return_value = local_profile
            mock_get_models.return_value = ["openai/gpt-2"]
            mock_get_revisions.return_value = ["abc123"]
            mock_get_latest.return_value = "abc123"
            mock_get_model_dir.return_value = "/path/to/model"

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {"id": "service-uuid-123"}
            mock_post.return_value = mock_response

            result = cli_runner.invoke(main, cmd)

        assert "Started service" in result.output
        call_args = mock_post.call_args
        assert call_args[1]["json"]["mount"] == "/data/custom"

    def test_grace_period_option(self, cli_runner, mock_config, local_profile):
        """Test that grace-period option is passed correctly."""
        cmd = [
            "run",
            "-p",
            "default",
            "--grace-period",
            "300",
            "text-generation",
            "openai/gpt-2",
        ]

        with (
            patch(
                "blackfish.server.models.profile.deserialize_profile"
            ) as mock_deserialize,
            patch(
                "blackfish.cli.services.text_generation.get_models"
            ) as mock_get_models,
            patch(
                "blackfish.cli.services.text_generation.get_revisions"
            ) as mock_get_revisions,
            patch(
                "blackfish.cli.services.text_generation.get_latest_commit"
            ) as mock_get_latest,
            patch(
                "blackfish.cli.services.text_generation.get_model_dir"
            ) as mock_get_model_dir,
            patch("blackfish.cli.services.text_generation.requests.post") as mock_post,
        ):
            mock_deserialize.return_value = local_profile
            mock_get_models.return_value = ["openai/gpt-2"]
            mock_get_revisions.return_value = ["abc123"]
            mock_get_latest.return_value = "abc123"
            mock_get_model_dir.return_value = "/path/to/model"

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = {"id": "service-uuid-123"}
            mock_post.return_value = mock_response

            result = cli_runner.invoke(main, cmd)

        assert "Started service" in result.output
        call_args = mock_post.call_args
        assert call_args[1]["json"]["grace_period"] == 300
