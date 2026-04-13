"""Unit tests for model metadata fetching and caching."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

from blackfish.server.models.metadata import (
    ModelMetadata,
    fetch_model_metadata,
    get_cached_metadata,
    update_cached_metadata,
    refresh_metadata,
    _get_safetensors_size,
    _get_bin_files_size,
    _calculate_from_config,
    DTYPE_BYTES,
)


class TestModelMetadata:
    """Test ModelMetadata dataclass."""

    def test_to_dict(self):
        """Test serialization to dict."""
        metadata = ModelMetadata(
            model_size_gb=13.5,
            size_source="safetensors",
            parameter_count=7000000000,
            dtype="bfloat16",
            fetched_at="2024-01-15T12:00:00Z",
        )
        result = metadata.to_dict()

        assert result["model_size_gb"] == 13.5
        assert result["size_source"] == "safetensors"
        assert result["parameter_count"] == 7000000000
        assert result["dtype"] == "bfloat16"
        assert result["fetched_at"] == "2024-01-15T12:00:00Z"

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "model_size_gb": 26.0,
            "size_source": "bin_files",
            "parameter_count": 13000000000,
            "dtype": "float16",
            "fetched_at": "2024-01-15T12:00:00Z",
        }
        metadata = ModelMetadata.from_dict(data)

        assert metadata.model_size_gb == 26.0
        assert metadata.size_source == "bin_files"
        assert metadata.parameter_count == 13000000000
        assert metadata.dtype == "float16"

    def test_from_dict_missing_fields(self):
        """Test deserialization with missing optional fields."""
        data = {
            "model_size_gb": 10.0,
            "size_source": "calculated",
        }
        metadata = ModelMetadata.from_dict(data)

        assert metadata.model_size_gb == 10.0
        assert metadata.size_source == "calculated"
        assert metadata.parameter_count is None
        assert metadata.dtype is None
        assert metadata.fetched_at is None

    def test_from_dict_empty(self):
        """Test deserialization from empty dict."""
        metadata = ModelMetadata.from_dict({})

        assert metadata.model_size_gb == 0.0
        assert metadata.size_source == "unknown"


class TestDtypeBytes:
    """Test dtype to bytes mapping."""

    def test_common_dtypes(self):
        """Test common dtype byte sizes."""
        assert DTYPE_BYTES["float32"] == 4
        assert DTYPE_BYTES["float16"] == 2
        assert DTYPE_BYTES["bfloat16"] == 2
        assert DTYPE_BYTES["int8"] == 1
        assert DTYPE_BYTES["int4"] == 0.5


class TestGetSafetensorsSize:
    """Test safetensors metadata fetching."""

    def test_get_safetensors_size_success(self):
        """Test successful safetensors metadata fetch."""
        mock_metadata = MagicMock()
        mock_tensor = MagicMock()
        mock_tensor.nbytes = 1024 * 1024 * 1024  # 1 GB
        mock_tensor.shape = [1000, 1000]
        mock_metadata.tensors = {"weight": mock_tensor}
        mock_metadata.parameter_count = None

        with patch(
            "blackfish.server.models.metadata.get_safetensors_metadata",
            return_value=mock_metadata,
        ):
            result = _get_safetensors_size("test/model")

        assert result is not None
        size_gb, param_count = result
        assert size_gb == 1.0
        assert param_count == 1000000

    def test_get_safetensors_size_with_parameter_count(self):
        """Test safetensors with explicit parameter count."""
        mock_metadata = MagicMock()
        mock_tensor = MagicMock()
        mock_tensor.nbytes = 2 * 1024 * 1024 * 1024  # 2 GB
        mock_metadata.tensors = {"weight": mock_tensor}
        mock_metadata.parameter_count = {"total": 7000000000}

        with patch(
            "blackfish.server.models.metadata.get_safetensors_metadata",
            return_value=mock_metadata,
        ):
            result = _get_safetensors_size("test/model")

        assert result is not None
        size_gb, param_count = result
        assert size_gb == 2.0
        assert param_count == 7000000000

    def test_get_safetensors_size_not_found(self):
        """Test when safetensors metadata not available."""
        with patch(
            "blackfish.server.models.metadata.get_safetensors_metadata",
            return_value=None,
        ):
            result = _get_safetensors_size("test/model")

        assert result is None

    def test_get_safetensors_size_exception(self):
        """Test handling of exceptions."""
        with patch(
            "blackfish.server.models.metadata.get_safetensors_metadata",
            side_effect=Exception("Network error"),
        ):
            result = _get_safetensors_size("test/model")

        assert result is None


class TestGetBinFilesSize:
    """Test bin files size calculation."""

    def test_get_bin_files_size_success(self):
        """Test successful bin files size calculation."""
        mock_sibling1 = MagicMock()
        mock_sibling1.rfilename = "model.bin"
        mock_sibling1.size = 5 * 1024 * 1024 * 1024  # 5 GB

        mock_sibling2 = MagicMock()
        mock_sibling2.rfilename = "model-00001.safetensors"
        mock_sibling2.size = 3 * 1024 * 1024 * 1024  # 3 GB

        mock_sibling3 = MagicMock()
        mock_sibling3.rfilename = "config.json"
        mock_sibling3.size = 1024  # Should be ignored

        mock_repo_info = MagicMock()
        mock_repo_info.siblings = [mock_sibling1, mock_sibling2, mock_sibling3]

        with patch("blackfish.server.models.metadata.HfApi") as mock_api:
            mock_api.return_value.model_info.return_value = mock_repo_info
            result = _get_bin_files_size("test/model")

        assert result is not None
        assert result == 8.0  # 5 + 3 GB

    def test_get_bin_files_size_no_model_files(self):
        """Test when no model files found."""
        mock_sibling = MagicMock()
        mock_sibling.rfilename = "config.json"
        mock_sibling.size = 1024

        mock_repo_info = MagicMock()
        mock_repo_info.siblings = [mock_sibling]

        with patch("blackfish.server.models.metadata.HfApi") as mock_api:
            mock_api.return_value.model_info.return_value = mock_repo_info
            result = _get_bin_files_size("test/model")

        assert result is None

    def test_get_bin_files_size_no_siblings(self):
        """Test when repository has no files."""
        mock_repo_info = MagicMock()
        mock_repo_info.siblings = None

        with patch("blackfish.server.models.metadata.HfApi") as mock_api:
            mock_api.return_value.model_info.return_value = mock_repo_info
            result = _get_bin_files_size("test/model")

        assert result is None

    def test_get_bin_files_size_exception(self):
        """Test handling of exceptions."""
        with patch("blackfish.server.models.metadata.HfApi") as mock_api:
            mock_api.return_value.model_info.side_effect = Exception("Network error")
            result = _get_bin_files_size("test/model")

        assert result is None


class TestCalculateFromConfig:
    """Test size calculation from config.json."""

    def test_calculate_from_config_with_num_parameters(self):
        """Test calculation when num_parameters is in config."""
        config = {
            "num_parameters": 7000000000,
            "torch_dtype": "bfloat16",
        }

        with patch("blackfish.server.models.metadata.HfApi") as mock_api:
            mock_api.return_value.hf_hub_download.return_value = "/tmp/config.json"
            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read = lambda: json.dumps(
                    config
                )
                with patch("json.load", return_value=config):
                    result = _calculate_from_config("test/model")

        assert result is not None
        size_gb, param_count, dtype = result
        assert param_count == 7000000000
        assert dtype == "bfloat16"
        # 7B params * 2 bytes = 14 GB
        assert abs(size_gb - 13.04) < 0.1

    def test_calculate_from_config_from_architecture(self):
        """Test calculation from architecture parameters."""
        config = {
            "hidden_size": 4096,
            "num_hidden_layers": 32,
            "vocab_size": 32000,
            "intermediate_size": 11008,
            "torch_dtype": "float16",
        }

        with patch("blackfish.server.models.metadata.HfApi") as mock_api:
            mock_api.return_value.hf_hub_download.return_value = "/tmp/config.json"
            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read = lambda: json.dumps(
                    config
                )
                with patch("json.load", return_value=config):
                    result = _calculate_from_config("test/model")

        assert result is not None
        size_gb, param_count, dtype = result
        assert param_count > 0
        assert dtype == "float16"

    def test_calculate_from_config_exception(self):
        """Test handling of exceptions."""
        with patch("blackfish.server.models.metadata.HfApi") as mock_api:
            mock_api.return_value.hf_hub_download.side_effect = Exception("Not found")
            result = _calculate_from_config("test/model")

        assert result is None


class TestFetchModelMetadata:
    """Test the main fetch_model_metadata function."""

    def test_fetch_uses_safetensors_first(self):
        """Test that safetensors is tried first."""
        with patch(
            "blackfish.server.models.metadata._get_safetensors_size",
            return_value=(13.5, 7000000000),
        ):
            result = fetch_model_metadata("test/model")

        assert result.model_size_gb == 13.5
        assert result.size_source == "safetensors"
        assert result.parameter_count == 7000000000

    def test_fetch_falls_back_to_bin_files(self):
        """Test fallback to bin files when safetensors unavailable."""
        with patch(
            "blackfish.server.models.metadata._get_safetensors_size",
            return_value=None,
        ):
            with patch(
                "blackfish.server.models.metadata._get_bin_files_size",
                return_value=26.0,
            ):
                result = fetch_model_metadata("test/model")

        assert result.model_size_gb == 26.0
        assert result.size_source == "bin_files"

    def test_fetch_falls_back_to_calculated(self):
        """Test fallback to calculated when bin files unavailable."""
        with patch(
            "blackfish.server.models.metadata._get_safetensors_size",
            return_value=None,
        ):
            with patch(
                "blackfish.server.models.metadata._get_bin_files_size",
                return_value=None,
            ):
                with patch(
                    "blackfish.server.models.metadata._calculate_from_config",
                    return_value=(10.0, 5000000000, "float16"),
                ):
                    result = fetch_model_metadata("test/model")

        assert result.model_size_gb == 10.0
        assert result.size_source == "calculated"
        assert result.parameter_count == 5000000000
        assert result.dtype == "float16"

    def test_fetch_returns_unknown_when_all_fail(self):
        """Test unknown source when all methods fail."""
        with patch(
            "blackfish.server.models.metadata._get_safetensors_size",
            return_value=None,
        ):
            with patch(
                "blackfish.server.models.metadata._get_bin_files_size",
                return_value=None,
            ):
                with patch(
                    "blackfish.server.models.metadata._calculate_from_config",
                    return_value=None,
                ):
                    result = fetch_model_metadata("test/model")

        assert result.model_size_gb == 0.0
        assert result.size_source == "unknown"

    def test_fetch_includes_timestamp(self):
        """Test that fetched_at timestamp is included."""
        with patch(
            "blackfish.server.models.metadata._get_safetensors_size",
            return_value=(10.0, None),
        ):
            result = fetch_model_metadata("test/model")

        assert result.fetched_at is not None


class TestCachedMetadata:
    """Test metadata caching functions."""

    def test_get_cached_metadata_file_not_found(self):
        """Test when info.json doesn't exist."""
        with TemporaryDirectory() as tmpdir:
            result = get_cached_metadata("test/model", tmpdir)
            assert result is None

    def test_get_cached_metadata_model_not_in_cache(self):
        """Test when model is not in cache."""
        with TemporaryDirectory() as tmpdir:
            info_path = Path(tmpdir) / "info.json"
            info_path.write_text(json.dumps({"other/model": "text-generation"}))

            result = get_cached_metadata("test/model", tmpdir)
            assert result is None

    def test_get_cached_metadata_old_format(self):
        """Test handling of old string format."""
        with TemporaryDirectory() as tmpdir:
            info_path = Path(tmpdir) / "info.json"
            info_path.write_text(json.dumps({"test/model": "text-generation"}))

            result = get_cached_metadata("test/model", tmpdir)
            assert result is None

    def test_get_cached_metadata_new_format(self):
        """Test reading new format with metadata."""
        with TemporaryDirectory() as tmpdir:
            info_path = Path(tmpdir) / "info.json"
            data = {
                "test/model": {
                    "image": "text-generation",
                    "metadata": {
                        "model_size_gb": 13.5,
                        "size_source": "safetensors",
                        "parameter_count": 7000000000,
                    },
                }
            }
            info_path.write_text(json.dumps(data))

            result = get_cached_metadata("test/model", tmpdir)

            assert result is not None
            assert result.model_size_gb == 13.5
            assert result.size_source == "safetensors"
            assert result.parameter_count == 7000000000

    def test_get_cached_metadata_invalid_json(self):
        """Test handling of invalid JSON."""
        with TemporaryDirectory() as tmpdir:
            info_path = Path(tmpdir) / "info.json"
            info_path.write_text("invalid json")

            result = get_cached_metadata("test/model", tmpdir)
            assert result is None

    def test_update_cached_metadata_new_file(self):
        """Test creating new info.json."""
        with TemporaryDirectory() as tmpdir:
            metadata = ModelMetadata(
                model_size_gb=13.5,
                size_source="safetensors",
            )

            update_cached_metadata("test/model", tmpdir, metadata, "text-generation")

            info_path = Path(tmpdir) / "info.json"
            assert info_path.exists()

            data = json.loads(info_path.read_text())
            assert "test/model" in data
            assert data["test/model"]["image"] == "text-generation"
            assert data["test/model"]["metadata"]["model_size_gb"] == 13.5

    def test_update_cached_metadata_preserves_image_from_old_format(self):
        """Test that old format image is preserved when updating."""
        with TemporaryDirectory() as tmpdir:
            # Create old format entry
            info_path = Path(tmpdir) / "info.json"
            info_path.write_text(json.dumps({"test/model": "text-generation"}))

            metadata = ModelMetadata(
                model_size_gb=13.5,
                size_source="safetensors",
            )

            # Update without specifying image
            update_cached_metadata("test/model", tmpdir, metadata)

            data = json.loads(info_path.read_text())
            assert data["test/model"]["image"] == "text-generation"
            assert data["test/model"]["metadata"]["model_size_gb"] == 13.5

    def test_update_cached_metadata_preserves_other_models(self):
        """Test that updating one model doesn't affect others."""
        with TemporaryDirectory() as tmpdir:
            info_path = Path(tmpdir) / "info.json"
            initial_data = {
                "other/model": {
                    "image": "speech-recognition",
                    "metadata": {"model_size_gb": 5.0, "size_source": "bin_files"},
                }
            }
            info_path.write_text(json.dumps(initial_data))

            metadata = ModelMetadata(
                model_size_gb=13.5,
                size_source="safetensors",
            )
            update_cached_metadata("test/model", tmpdir, metadata, "text-generation")

            data = json.loads(info_path.read_text())
            assert "other/model" in data
            assert data["other/model"]["metadata"]["model_size_gb"] == 5.0


class TestRefreshMetadata:
    """Test refresh_metadata function."""

    def test_refresh_metadata_fetches_and_caches(self):
        """Test that refresh fetches new metadata and updates cache."""
        with TemporaryDirectory() as tmpdir:
            with patch(
                "blackfish.server.models.metadata.fetch_model_metadata"
            ) as mock_fetch:
                mock_fetch.return_value = ModelMetadata(
                    model_size_gb=13.5,
                    size_source="safetensors",
                    fetched_at="2024-01-15T12:00:00Z",
                )

                result = refresh_metadata("test/model", tmpdir)

            assert result.model_size_gb == 13.5
            mock_fetch.assert_called_once_with("test/model", None)

            # Verify it was cached
            cached = get_cached_metadata("test/model", tmpdir)
            assert cached is not None
            assert cached.model_size_gb == 13.5

    def test_refresh_metadata_with_token(self):
        """Test refresh with HF token."""
        with TemporaryDirectory() as tmpdir:
            with patch(
                "blackfish.server.models.metadata.fetch_model_metadata"
            ) as mock_fetch:
                mock_fetch.return_value = ModelMetadata(
                    model_size_gb=26.0,
                    size_source="safetensors",
                )

                refresh_metadata("test/model", tmpdir, token="hf_token123")

            mock_fetch.assert_called_once_with("test/model", "hf_token123")
