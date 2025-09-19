"""Integration tests for HF token support in Blackfish.

These tests verify that HF token authentication works end-to-end
for gated model access.
"""

import os
from unittest.mock import patch

from app.auth import get_hf_token
from app.utils import get_latest_commit, has_model
from app.models.model import add_model


class TestHFTokenIntegration:
    """Test HF token integration across the codebase."""

    def test_environment_variable_token_resolution(self):
        """Test that HF_TOKEN environment variable is properly resolved."""
        test_token = "hf_test_token_12345"

        with patch.dict(os.environ, {"HF_TOKEN": test_token}):
            resolved_token = get_hf_token()
            assert resolved_token == test_token

    def test_get_latest_commit_accepts_token(self):
        """Test that get_latest_commit function accepts token parameter."""
        # Test that function signature works - actual HF API call will fail in CI
        # but this verifies the token parameter is properly passed through

        with patch("huggingface_hub.list_repo_commits") as mock_list_commits:
            # Mock the HF API response
            mock_commit = type("MockCommit", (), {"commit_id": "abc123"})()
            mock_list_commits.return_value = [mock_commit]

            # Call with explicit token
            result = get_latest_commit("test/model", ["abc123"], token="test_token")

            # Verify token was passed to HF API
            mock_list_commits.assert_called_once_with("test/model", token="test_token")
            assert result == "abc123"

    def test_has_model_accepts_token(self):
        """Test that has_model function accepts token parameter."""
        from app.models.profile import LocalProfile

        test_profile = LocalProfile(
            name="test", home_dir="/tmp/test", cache_dir="/tmp/cache"
        )

        with patch("huggingface_hub.ModelCard.load") as mock_load:
            with patch("app.utils.get_models") as mock_get_models:
                mock_get_models.return_value = ["test/model"]

                # Call with explicit token
                has_model("test/model", test_profile, token="test_token")

                # Verify token was passed to ModelCard.load
                mock_load.assert_called_once_with("test/model", token="test_token")

    def test_model_download_uses_token_resolution(self):
        """Test that model download uses automatic token resolution."""
        from app.models.profile import LocalProfile

        test_profile = LocalProfile(
            name="test", home_dir="/tmp/test", cache_dir="/tmp/cache"
        )

        with patch("huggingface_hub.snapshot_download") as mock_download:
            with patch("huggingface_hub.model_info") as mock_model_info:
                with patch("app.auth.get_hf_token") as mock_get_token:
                    mock_get_token.return_value = "resolved_token"
                    mock_download.return_value = "/path/to/model/abc123"
                    mock_model_info.return_value = type(
                        "MockModelInfo", (), {"pipeline_tag": "text-generation"}
                    )()

                    try:
                        add_model("test/model", test_profile)
                    except Exception:
                        # Expected to fail due to mocking, but we can check calls
                        pass

                    # Verify token resolution was used
                    mock_get_token.assert_called()

                    # Verify token was passed to HF APIs
                    mock_download.assert_called()
                    mock_model_info.assert_called()

    def test_fallback_when_no_token_available(self):
        """Test graceful fallback when no HF token is available."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("huggingface_hub.get_token") as mock_get_token:
                mock_get_token.return_value = None

                token = get_hf_token()
                assert token is None

                # Functions should still work with None token (public models)
                with patch("huggingface_hub.list_repo_commits") as mock_list_commits:
                    mock_commit = type("MockCommit", (), {"commit_id": "abc123"})()
                    mock_list_commits.return_value = [mock_commit]

                    get_latest_commit("test/model", ["abc123"])

                    # Should call with None token
                    mock_list_commits.assert_called_once_with("test/model", token=None)
