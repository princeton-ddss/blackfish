"""Tests for HuggingFace authentication utilities."""

import os
from unittest.mock import patch

from app.auth import get_hf_token, is_hf_authenticated


class TestHFTokenResolution:
    """Test HF token resolution from different sources."""

    def test_get_hf_token_from_environment(self):
        """Test token resolution from HF_TOKEN environment variable."""
        with patch.dict(os.environ, {"HF_TOKEN": "test_env_token"}):
            token = get_hf_token()
            assert token == "test_env_token"

    def test_get_hf_token_from_hf_storage(self):
        """Test token resolution from HF's official storage."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("huggingface_hub.get_token") as mock_get_token:
                mock_get_token.return_value = "test_stored_token"
                token = get_hf_token()
                assert token == "test_stored_token"

    def test_get_hf_token_priority_env_over_storage(self):
        """Test that environment variable takes priority over stored token."""
        with patch.dict(os.environ, {"HF_TOKEN": "test_env_token"}):
            with patch("huggingface_hub.get_token") as mock_get_token:
                mock_get_token.return_value = "test_stored_token"
                token = get_hf_token()
                assert token == "test_env_token"

    def test_get_hf_token_no_token_available(self):
        """Test token resolution when no token is available."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("huggingface_hub.get_token") as mock_get_token:
                mock_get_token.return_value = None
                token = get_hf_token()
                assert token is None

    def test_get_hf_token_hf_exception(self):
        """Test graceful handling when HF auth throws an exception."""
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "huggingface_hub.get_token", side_effect=Exception("Auth error")
            ):
                token = get_hf_token()
                assert token is None


class TestHFAuthentication:
    """Test HF authentication status checking."""

    def test_is_hf_authenticated_with_valid_token(self):
        """Test authentication check with valid token."""
        with patch("app.auth.get_hf_token") as mock_get_token:
            with patch("huggingface_hub.whoami") as mock_whoami:
                mock_get_token.return_value = "valid_token"
                mock_whoami.return_value = {"name": "test_user"}

                assert is_hf_authenticated() is True
                mock_whoami.assert_called_once_with(token="valid_token")

    def test_is_hf_authenticated_no_token(self):
        """Test authentication check when no token is available."""
        with patch("app.auth.get_hf_token") as mock_get_token:
            mock_get_token.return_value = None
            assert is_hf_authenticated() is False

    def test_is_hf_authenticated_invalid_token(self):
        """Test authentication check with invalid token."""
        with patch("app.auth.get_hf_token") as mock_get_token:
            with patch("huggingface_hub.whoami") as mock_whoami:
                mock_get_token.return_value = "invalid_token"
                mock_whoami.side_effect = Exception("Invalid token")

                assert is_hf_authenticated() is False
