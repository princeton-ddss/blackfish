"""Unit tests for blackfish.server.models.model module."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

from blackfish.server.models.model import (
    validate_repo_id,
    split,
    remove_model,
    get_pipeline,
    add_model,
    InvalidRepoIdError,
    ModelNotFoundError,
    RevisionNotFoundError,
    PIPELINE_IMAGES,
)
from blackfish.server.models.metadata import ModelMetadata


# =============================================================================
# Test validate_repo_id
# =============================================================================


class TestValidateRepoId:
    """Tests for validate_repo_id function."""

    def test_valid_simple_repo_id(self):
        """Test valid simple repo ID."""
        validate_repo_id("openai/whisper-large-v3")  # Should not raise

    def test_valid_repo_id_with_dots(self):
        """Test valid repo ID with dots."""
        validate_repo_id("meta-llama/Llama-3.2-3B")  # Should not raise

    def test_valid_repo_id_with_underscores(self):
        """Test valid repo ID with underscores."""
        validate_repo_id("big_science/bloom_560m")  # Should not raise

    def test_valid_repo_id_with_numbers(self):
        """Test valid repo ID with numbers."""
        validate_repo_id("org123/model456")  # Should not raise

    def test_invalid_empty_string(self):
        """Test that empty string raises InvalidRepoIdError."""
        with pytest.raises(InvalidRepoIdError):
            validate_repo_id("")

    def test_invalid_no_slash(self):
        """Test that repo ID without slash raises InvalidRepoIdError."""
        with pytest.raises(InvalidRepoIdError):
            validate_repo_id("openai-whisper")

    def test_invalid_multiple_slashes(self):
        """Test that repo ID with multiple slashes raises InvalidRepoIdError."""
        with pytest.raises(InvalidRepoIdError):
            validate_repo_id("org/sub/model")

    def test_invalid_special_characters(self):
        """Test that repo ID with special characters raises InvalidRepoIdError."""
        with pytest.raises(InvalidRepoIdError):
            validate_repo_id("org/model@latest")

    def test_invalid_spaces(self):
        """Test that repo ID with spaces raises InvalidRepoIdError."""
        with pytest.raises(InvalidRepoIdError):
            validate_repo_id("org/my model")

    def test_invalid_none(self):
        """Test that None raises InvalidRepoIdError."""
        with pytest.raises(InvalidRepoIdError):
            validate_repo_id(None)  # type: ignore


# =============================================================================
# Test split
# =============================================================================


class TestSplit:
    """Tests for split function."""

    def test_split_simple(self):
        """Test splitting a simple repo ID."""
        namespace, model = split("openai/whisper-large-v3")
        assert namespace == "openai"
        assert model == "whisper-large-v3"

    def test_split_with_dashes(self):
        """Test splitting repo ID with dashes."""
        namespace, model = split("meta-llama/Llama-3.2-3B")
        assert namespace == "meta-llama"
        assert model == "Llama-3.2-3B"

    def test_split_invalid_raises(self):
        """Test that invalid repo ID raises InvalidRepoIdError."""
        with pytest.raises(InvalidRepoIdError):
            split("invalid-repo-id")


# =============================================================================
# Test remove_model
# =============================================================================


@dataclass
class MockProfile:
    """Mock profile for testing."""

    name: str = "test"
    home_dir: str = "/tmp/blackfish"
    cache_dir: str = "/tmp/blackfish/cache"


class TestRemoveModel:
    """Tests for remove_model function."""

    def test_remove_model_entire_directory(self, tmp_path: Path):
        """Test removing entire model directory (no revision specified)."""
        # Setup: create model directory structure
        models_dir = tmp_path / "models"
        model_dir = models_dir / "models--openai--whisper-large-v3"
        snapshots_dir = model_dir / "snapshots" / "abc123"
        snapshots_dir.mkdir(parents=True)
        (snapshots_dir / "model.safetensors").touch()

        profile = MockProfile(home_dir=str(tmp_path))

        remove_model("openai/whisper-large-v3", profile)

        assert not model_dir.exists()

    def test_remove_model_not_found(self, tmp_path: Path):
        """Test removing non-existent model raises ModelNotFoundError."""
        models_dir = tmp_path / "models"
        models_dir.mkdir(parents=True)

        profile = MockProfile(home_dir=str(tmp_path))

        with pytest.raises(ModelNotFoundError):
            remove_model("openai/whisper-large-v3", profile)

    def test_remove_model_specific_revision_only_one(self, tmp_path: Path):
        """Test removing specific revision when it's the only one deletes entire dir."""
        models_dir = tmp_path / "models"
        model_dir = models_dir / "models--openai--whisper-large-v3"
        snapshots_dir = model_dir / "snapshots"
        revision_dir = snapshots_dir / "v1.0"
        revision_dir.mkdir(parents=True)
        (revision_dir / "model.safetensors").touch()

        profile = MockProfile(home_dir=str(tmp_path))

        remove_model("openai/whisper-large-v3", profile, revision="v1.0")

        # Entire model dir should be deleted since it was the only revision
        assert not model_dir.exists()

    def test_remove_model_specific_revision_multiple(self, tmp_path: Path):
        """Test removing specific revision when multiple exist."""
        models_dir = tmp_path / "models"
        model_dir = models_dir / "models--openai--whisper-large-v3"
        snapshots_dir = model_dir / "snapshots"

        # Create two revisions
        (snapshots_dir / "v1.0").mkdir(parents=True)
        (snapshots_dir / "v2.0").mkdir(parents=True)
        (snapshots_dir / "v1.0" / "model.safetensors").touch()
        (snapshots_dir / "v2.0" / "model.safetensors").touch()

        profile = MockProfile(home_dir=str(tmp_path))

        # Mock scan_cache_dir to avoid HF cache operations
        with patch("blackfish.server.models.model.scan_cache_dir") as mock_scan:
            mock_scan.return_value.repos = []  # HF scan doesn't find it
            remove_model("openai/whisper-large-v3", profile, revision="v1.0")

        # v1.0 should be deleted, v2.0 should remain
        assert not (snapshots_dir / "v1.0").exists()
        assert (snapshots_dir / "v2.0").exists()

    def test_remove_model_revision_not_found(self, tmp_path: Path):
        """Test removing non-existent revision raises RevisionNotFoundError."""
        models_dir = tmp_path / "models"
        model_dir = models_dir / "models--openai--whisper-large-v3"
        snapshots_dir = model_dir / "snapshots" / "v1.0"
        snapshots_dir.mkdir(parents=True)

        profile = MockProfile(home_dir=str(tmp_path))

        with pytest.raises(RevisionNotFoundError):
            remove_model("openai/whisper-large-v3", profile, revision="v2.0")

    def test_remove_model_no_snapshots_dir(self, tmp_path: Path):
        """Test removing model when snapshots directory doesn't exist."""
        models_dir = tmp_path / "models"
        model_dir = models_dir / "models--openai--whisper-large-v3"
        model_dir.mkdir(parents=True)
        # No snapshots subdirectory

        profile = MockProfile(home_dir=str(tmp_path))

        remove_model("openai/whisper-large-v3", profile, revision="v1.0")

        # Entire model dir should be deleted
        assert not model_dir.exists()

    def test_remove_model_use_cache(self, tmp_path: Path):
        """Test removing model from cache directory."""
        cache_dir = tmp_path / "cache"
        models_dir = cache_dir / "models"
        model_dir = models_dir / "models--openai--whisper-large-v3"
        model_dir.mkdir(parents=True)

        profile = MockProfile(cache_dir=str(cache_dir))

        remove_model("openai/whisper-large-v3", profile, use_cache=True)

        assert not model_dir.exists()

    def test_remove_model_with_hf_cache_cleanup(self, tmp_path: Path):
        """Test removal using HuggingFace cache cleanup when available."""
        models_dir = tmp_path / "models"
        model_dir = models_dir / "models--openai--whisper-large-v3"
        snapshots_dir = model_dir / "snapshots"
        (snapshots_dir / "v1.0").mkdir(parents=True)
        (snapshots_dir / "v2.0").mkdir(parents=True)

        profile = MockProfile(home_dir=str(tmp_path))

        # Mock HF cache operations
        mock_repo = MagicMock()
        mock_repo.repo_id = "openai/whisper-large-v3"
        mock_cache = MagicMock()
        mock_cache.repos = [mock_repo]
        mock_op = MagicMock()
        mock_cache.delete_revisions.return_value = mock_op

        with patch("blackfish.server.models.model.scan_cache_dir") as mock_scan:
            mock_scan.return_value = mock_cache
            remove_model("openai/whisper-large-v3", profile, revision="v1.0")

        mock_cache.delete_revisions.assert_called_once_with("v1.0")
        mock_op.execute.assert_called_once()

    def test_remove_model_revision_model_dir_not_exists(self, tmp_path: Path):
        """Test removing revision when model directory doesn't exist."""
        models_dir = tmp_path / "models"
        models_dir.mkdir(parents=True)
        # Model directory doesn't exist

        profile = MockProfile(home_dir=str(tmp_path))

        with pytest.raises(ModelNotFoundError):
            remove_model("openai/whisper-large-v3", profile, revision="v1.0")

    def test_remove_model_hf_cache_exception_fallback(self, tmp_path: Path):
        """Test fallback to direct deletion when HF cache operations fail."""
        models_dir = tmp_path / "models"
        model_dir = models_dir / "models--openai--whisper-large-v3"
        snapshots_dir = model_dir / "snapshots"
        (snapshots_dir / "v1.0").mkdir(parents=True)
        (snapshots_dir / "v1.0" / "model.bin").touch()
        (snapshots_dir / "v2.0").mkdir(parents=True)
        (snapshots_dir / "v2.0" / "model.bin").touch()

        profile = MockProfile(home_dir=str(tmp_path))

        # Mock HF cache to raise an exception
        with patch("blackfish.server.models.model.scan_cache_dir") as mock_scan:
            mock_scan.side_effect = Exception("HF cache error")
            remove_model("openai/whisper-large-v3", profile, revision="v1.0")

        # v1.0 should be deleted via fallback, v2.0 should remain
        assert not (snapshots_dir / "v1.0").exists()
        assert (snapshots_dir / "v2.0").exists()


# =============================================================================
# Test get_pipeline
# =============================================================================


class TestGetPipeline:
    """Tests for get_pipeline function."""

    def test_get_pipeline_from_pipeline_tag(self):
        """Test extracting pipeline from pipeline_tag attribute."""
        mock_info = MagicMock()
        mock_info.pipeline_tag = "text-generation"
        mock_info.card_data = None

        result = get_pipeline(mock_info)
        assert result == "text-generation"

    def test_get_pipeline_from_card_data(self):
        """Test extracting pipeline from card_data when pipeline_tag is None."""
        mock_info = MagicMock()
        mock_info.pipeline_tag = None
        mock_info.card_data = {"pipeline_tag": "automatic-speech-recognition"}

        result = get_pipeline(mock_info)
        assert result == "automatic-speech-recognition"

    def test_get_pipeline_none_when_not_available(self):
        """Test returns None when no pipeline info available."""
        mock_info = MagicMock()
        mock_info.pipeline_tag = None
        mock_info.card_data = None

        result = get_pipeline(mock_info)
        assert result is None

    def test_get_pipeline_card_data_no_pipeline(self):
        """Test returns None when card_data exists but has no pipeline_tag."""
        mock_info = MagicMock()
        mock_info.pipeline_tag = None
        mock_info.card_data = {"other_field": "value"}

        result = get_pipeline(mock_info)
        assert result is None


# =============================================================================
# Test add_model
# =============================================================================


class TestAddModel:
    """Tests for add_model function."""

    @patch("blackfish.server.models.model.fetch_model_metadata")
    @patch("blackfish.server.models.model.model_info")
    @patch("blackfish.server.models.model.snapshot_download")
    def test_add_model_success(
        self, mock_download, mock_info, mock_metadata, tmp_path: Path
    ):
        """Test successful model download."""
        mock_download.return_value = str(tmp_path / "snapshots" / "abc123def")
        mock_info.return_value = MagicMock(
            pipeline_tag="text-generation", card_data=None
        )
        mock_metadata.return_value = ModelMetadata(
            model_size_gb=3.5,
            size_source="safetensors",
            parameter_count=1000000,
            dtype="float16",
        )

        profile = MockProfile(home_dir=str(tmp_path))

        model, path = add_model("meta-llama/Llama-3.2-3B", profile)

        assert model.repo == "meta-llama/Llama-3.2-3B"
        assert model.profile == "test"
        assert model.revision == "abc123def"
        assert model.image == "text-generation"
        assert model.metadata_ is not None
        assert model.metadata_["model_size_gb"] == 3.5
        assert path == str(tmp_path / "snapshots" / "abc123def")

    @patch("blackfish.server.models.model.fetch_model_metadata")
    @patch("blackfish.server.models.model.model_info")
    @patch("blackfish.server.models.model.snapshot_download")
    def test_add_model_with_revision(
        self, mock_download, mock_info, mock_metadata, tmp_path: Path
    ):
        """Test downloading specific revision."""
        mock_download.return_value = str(tmp_path / "snapshots" / "v1.0")
        mock_info.return_value = MagicMock(
            pipeline_tag="automatic-speech-recognition", card_data=None
        )
        mock_metadata.return_value = ModelMetadata(
            model_size_gb=1.5, size_source="bin_files"
        )

        profile = MockProfile(home_dir=str(tmp_path))

        model, path = add_model("openai/whisper-large-v3", profile, revision="v1.0")

        assert model.revision == "v1.0"
        assert model.image == "speech-recognition"
        mock_download.assert_called_once()
        call_kwargs = mock_download.call_args[1]
        assert call_kwargs["revision"] == "v1.0"

    @patch("blackfish.server.models.model.fetch_model_metadata")
    @patch("blackfish.server.models.model.model_info")
    @patch("blackfish.server.models.model.snapshot_download")
    def test_add_model_use_cache(
        self, mock_download, mock_info, mock_metadata, tmp_path: Path
    ):
        """Test downloading to cache directory."""
        cache_dir = tmp_path / "cache"
        mock_download.return_value = str(cache_dir / "snapshots" / "main")
        mock_info.return_value = MagicMock(
            pipeline_tag="text-generation", card_data=None
        )
        mock_metadata.return_value = ModelMetadata(
            model_size_gb=2.0, size_source="calculated"
        )

        profile = MockProfile(cache_dir=str(cache_dir))

        model, path = add_model("org/model", profile, use_cache=True)

        mock_download.assert_called_once()
        call_kwargs = mock_download.call_args[1]
        assert "cache" in str(call_kwargs["cache_dir"])

    @patch("blackfish.server.models.model.fetch_model_metadata")
    @patch("blackfish.server.models.model.model_info")
    @patch("blackfish.server.models.model.snapshot_download")
    def test_add_model_unknown_pipeline(
        self, mock_download, mock_info, mock_metadata, tmp_path: Path, capsys
    ):
        """Test handling unknown pipeline type."""
        mock_download.return_value = str(tmp_path / "snapshots" / "main")
        mock_info.return_value = MagicMock(
            pipeline_tag="some-new-pipeline", card_data=None
        )
        mock_metadata.return_value = ModelMetadata(
            model_size_gb=1.0, size_source="unknown"
        )

        profile = MockProfile(home_dir=str(tmp_path))

        model, path = add_model("org/model", profile)

        # Should use the pipeline name as image when not in PIPELINE_IMAGES
        assert model.image == "some-new-pipeline"
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "not a known task type" in captured.out

    @patch("blackfish.server.models.model.fetch_model_metadata")
    @patch("blackfish.server.models.model.model_info")
    @patch("blackfish.server.models.model.snapshot_download")
    def test_add_model_no_pipeline(
        self, mock_download, mock_info, mock_metadata, tmp_path: Path
    ):
        """Test handling model with no pipeline info."""
        mock_download.return_value = str(tmp_path / "snapshots" / "main")
        mock_info.return_value = MagicMock(pipeline_tag=None, card_data=None)
        mock_metadata.return_value = ModelMetadata(
            model_size_gb=0.0, size_source="unknown"
        )

        profile = MockProfile(home_dir=str(tmp_path))

        model, path = add_model("org/model", profile)

        assert model.image == "none"

    @patch("blackfish.server.models.model.fetch_model_metadata")
    @patch("blackfish.server.models.model.model_info")
    @patch("blackfish.server.models.model.snapshot_download")
    def test_add_model_with_token(
        self, mock_download, mock_info, mock_metadata, tmp_path: Path
    ):
        """Test downloading with authentication token."""
        mock_download.return_value = str(tmp_path / "snapshots" / "main")
        mock_info.return_value = MagicMock(
            pipeline_tag="text-generation", card_data=None
        )
        mock_metadata.return_value = ModelMetadata(
            model_size_gb=5.0, size_source="safetensors"
        )

        @dataclass
        class ProfileWithToken:
            name: str = "test"
            home_dir: str = ""
            token: str = "hf_secret_token"

        profile = ProfileWithToken(home_dir=str(tmp_path))

        model, path = add_model("org/gated-model", profile)

        mock_download.assert_called_once()
        call_kwargs = mock_download.call_args[1]
        assert call_kwargs["token"] == "hf_secret_token"


# =============================================================================
# Test PIPELINE_IMAGES mapping
# =============================================================================


class TestPipelineImages:
    """Tests for PIPELINE_IMAGES constant."""

    def test_common_pipelines_mapped(self):
        """Test that common pipeline types are mapped."""
        assert "automatic-speech-recognition" in PIPELINE_IMAGES
        assert "text-generation" in PIPELINE_IMAGES
        assert "image-text-to-text" in PIPELINE_IMAGES

    def test_none_pipeline_mapped(self):
        """Test that None pipeline is mapped to 'none'."""
        assert PIPELINE_IMAGES[None] == "none"
