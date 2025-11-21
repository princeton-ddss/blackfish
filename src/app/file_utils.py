"""File management utilities for REST API endpoints.

This module provides shared validation and error handling logic for image, text, and audio file operations.
"""

from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime
from typing import Callable

from litestar.exceptions import (
    NotFoundException,
    NotAuthorizedException,
    InternalServerException,
    ValidationException,
)
from litestar.response import File

from app.logger import logger


def create_extension_validator(extensions: list[str], file_type: str) -> Callable[[str], str]:
    """Create an extension validator function for a specific file type.

    Args:
        extensions: List of allowed file extensions (e.g., ['.txt', '.md'])
        file_type: Human-readable file type name (e.g., 'text')

    Returns:
        A validator function that raises ValidationException if extension is invalid
    """
    def validator(path: str) -> str:
        if not any(path.lower().endswith(ext) for ext in extensions):
            raise ValidationException(
                f"Invalid {file_type} file extension. Allowed extensions: {', '.join(extensions)}"
            )
        return path
    return validator


def validate_file_exists_and_type(file_path: Path, extensions: list[str], file_type: str) -> None:
    """Validate that a file exists, is actually a file, and has the correct extension.

    Args:
        file_path: Path to the file to validate
        extensions: List of allowed file extensions
        file_type: Human-readable file type name for error messages

    Raises:
        NotFoundException: If the file doesn't exist
        ValidationException: If the path is not a file or has wrong extension
    """
    if not file_path.exists():
        raise NotFoundException(f"The requested path ({file_path}) does not exist")

    if not file_path.is_file():
        raise ValidationException(f"The requested path ({file_path}) is not a file")

    if not any(str(file_path).lower().endswith(ext) for ext in extensions):
        raise ValidationException(
            f"Invalid {file_type} file extension. Allowed extensions: {', '.join(extensions)}"
        )


def validate_file_size(content: bytes, max_size: int, file_type: str) -> None:
    """Validate that file content doesn't exceed maximum size.

    Args:
        content: File content bytes
        max_size: Maximum allowed file size in bytes
        file_type: Human-readable file type name for error messages

    Raises:
        ValidationException: If file size exceeds the maximum
    """
    content_length = len(content)
    if content_length > max_size:
        max_mb = max_size / (1024 * 1024)
        file_mb = content_length / (1024 * 1024)
        raise ValidationException(
            f"{file_type.capitalize()} file size ({file_mb:.1f}MB) exceeds maximum file size ({max_mb:.1f}MB)"
        )


def write_file_with_error_handling(path: Path, content: bytes, file_type: str) -> dict[str, str | int | datetime]:
    """Write file content to disk with comprehensive error handling.

    Creates parent directories if they don't exist.

    Args:
        path: Destination path for the file
        content: File content bytes to write
        file_type: Human-readable file type name for error messages

    Returns:
        Dictionary with filename, size, and created_at timestamp

    Raises:
        NotAuthorizedException: If permission denied
        InternalServerException: If other OS error occurs
    """
    try:
        parent_dir = path.parent
        parent_dir.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        logger.debug(f"Created {file_type} file at {path}")
        return {
            "filename": os.path.basename(path),
            "size": len(content),
            "created_at": datetime.now(),
        }
    except PermissionError as e:
        logger.error(f"User does not have permission to create file at path {path}: {e}")
        raise NotAuthorizedException(f"Permission denied: {e}")
    except OSError as e:
        logger.error(f"Failed to create {file_type} file at path {path}: {e}")
        raise InternalServerException(f"Failed to create file: {e}")
    except Exception as e:
        logger.error(f"Failed to create {file_type} file at path {path}: {e}")
        raise InternalServerException(f"Failed to create file: {e}")


def update_file_with_error_handling(path: Path, content: bytes, file_type: str) -> dict[str, str | int | datetime]:
    """Update existing file content with comprehensive error handling.

    Args:
        path: Path to the file to update
        content: New file content bytes
        file_type: Human-readable file type name for error messages

    Returns:
        Dictionary with filename, size, and created_at timestamp

    Raises:
        NotAuthorizedException: If permission denied
        InternalServerException: If other error occurs
    """
    try:
        path.write_bytes(content)
        logger.debug(f"Updated {file_type} file at {path}")
        return {
            "filename": os.path.basename(path),
            "size": len(content),
            "created_at": datetime.now(),
        }
    except PermissionError as e:
        logger.error(f"User does not have permission to update file at path {path}: {e}")
        raise NotAuthorizedException(f"Permission denied: {e}")
    except Exception as e:
        logger.error(f"Failed to update {file_type} file at path {path}: {e}")
        raise InternalServerException(f"Failed to update file: {e}")


def delete_file_with_error_handling(file_path: Path, file_type: str) -> dict[str, str]:
    """Delete a file with comprehensive error handling.

    Args:
        file_path: Path to the file to delete
        file_type: Human-readable file type name for error messages

    Returns:
        Dictionary with success message

    Raises:
        NotAuthorizedException: If permission denied
        InternalServerException: If other error occurs
    """
    try:
        file_path.unlink()
        logger.debug(f"Deleted {file_type} file at {file_path}")
        return {"message": f"Successfully deleted {file_type} file at {file_path}"}
    except PermissionError as e:
        logger.error(f"Permission denied deleting file at {file_path}: {e}")
        raise NotAuthorizedException(f"Permission denied: {e}")
    except Exception as e:
        logger.error(f"Failed to delete {file_type} file at {file_path}: {e}")
        raise InternalServerException(f"Failed to delete file: {e}")


def read_file_with_error_handling(file_path: Path, file_type: str) -> File:
    """Read a file and return it with comprehensive error handling.

    Args:
        file_path: Path to the file to read
        file_type: Human-readable file type name for error messages

    Returns:
        File response object

    Raises:
        NotAuthorizedException: If permission denied
        InternalServerException: If other error occurs
    """
    try:
        return File(path=file_path)
    except PermissionError as e:
        logger.error(f"Permission denied reading file at {file_path}: {e}")
        raise NotAuthorizedException(f"Permission denied: {e}")
    except Exception as e:
        logger.error(f"Failed to read {file_type} file at {file_path}: {e}")
        raise InternalServerException(f"Failed to read file: {e}")
