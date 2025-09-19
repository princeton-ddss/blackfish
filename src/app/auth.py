"""Hugging Face authentication utilities for Blackfish.

This module provides token resolution for accessing Hugging Face Hub APIs,
supporting both environment variables and HF's official token storage.
"""

import os
from typing import Optional


def get_hf_token() -> Optional[str]:
    """Get HF token from environment or HF's official storage.

    Token resolution priority:
    1. HF_TOKEN environment variable (advanced users)
    2. HF's official stored token from ~/.cache/huggingface/token (basic users)
    3. None (anonymous access)

    Returns:
        HF token string if available, None otherwise.
    """
    # 1. Environment variable (advanced users)
    if token := os.getenv("HF_TOKEN"):
        return token

    # 2. HF's official stored token (basic users)
    try:
        from huggingface_hub import get_token

        if token := get_token():
            return token
    except ImportError:
        # huggingface_hub not available
        pass
    except Exception:
        # Handle cases where HF auth not available or corrupted
        pass

    # 3. No token available
    return None


def is_hf_authenticated() -> bool:
    """Check if user is authenticated with Hugging Face.

    Returns:
        True if user has a valid HF token, False otherwise.
    """
    token = get_hf_token()
    if not token:
        return False

    try:
        from huggingface_hub import whoami

        whoami(token=token)
        return True
    except ImportError:
        # huggingface_hub not available, assume token is valid if present
        return True
    except Exception:
        # Token is invalid or API call failed
        return False
