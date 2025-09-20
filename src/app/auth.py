"""Hugging Face authentication utilities for Blackfish.

This module provides token resolution for accessing Hugging Face Hub APIs,
supporting both environment variables and HF's official token storage.
"""

import os
from typing import Optional
from huggingface_hub import get_token, whoami


def get_hf_token() -> Optional[str]:
    """Get HF token from environment or HF's official storage.

    Token resolution priority:
    1. HF_TOKEN environment variable
    2. HF's official stored token from ~/.cache/huggingface/token
    3. None

    Returns:
        HF token string (if available), else None.
    """
    # 1. Useenvironment variable
    if token := os.getenv("HF_TOKEN"):
        return token

    # 2. Use HF's stored token
    try:
        if token := get_token():
            return token
    except Exception:
        pass

    # 3. No token available
    return None


def is_hf_authenticated() -> bool:
    """Check if user is authenticated with Hugging Face.

    Returns:
        True if user has a valid HF token, else False.
    """
    token = get_hf_token()

    if not token:
        return False

    try:
        whoami(token=token)
        return True
    except Exception:
        # Token is invalid or API call failed
        return False
