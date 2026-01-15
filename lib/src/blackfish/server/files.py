"""File management utilities for REST API endpoints.

This module provides shared validation and error handling logic for image, text, and audio file operations.
"""

from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel

from litestar.exceptions import (
    NotFoundException,
    NotAuthorizedException,
    InternalServerException,
    ValidationException,
)
from litestar.response import File

from blackfish.server.logger import logger


def validate_file_exists(file_path: Path) -> None:
    """Validate that a file exists and is actually a file (not a directory).

    Args:
        file_path: Path to the file to validate

    Raises:
        NotFoundException: If the file doesn't exist
        ValidationException: If the path is not a file
    """
    if not file_path.exists():
        raise NotFoundException(f"The requested path ({file_path}) does not exist")

    if not file_path.is_file():
        raise ValidationException(f"The requested path ({file_path}) is not a file")


def validate_file_extension(
    file_path: Path,
    extensions: list[str],
) -> None:
    """Validate that a file has a supported extension.

    Args:
        file_path: Path to the file to validate
        extensions: List of allowed file extensions

    Raises:
        ValidationException: If the file extension is not supported
    """
    if not any(str(file_path).lower().endswith(ext) for ext in extensions):
        raise ValidationException(
            f"Invalid file extension. Allowed extensions: {', '.join(extensions)}"
        )


def validate_file_size(content: bytes, max_size: int) -> None:
    """Validate that file content doesn't exceed maximum size.

    Args:
        content: File content bytes
        max_size: Maximum allowed file size in bytes

    Raises:
        ValidationException: If file size exceeds the maximum
    """
    content_length = len(content)
    if content_length > max_size:
        max_mb = max_size / (1024 * 1024)
        file_mb = content_length / (1024 * 1024)
        raise ValidationException(
            f"File size ({file_mb:.1f}MB) exceeds maximum file size ({max_mb:.1f}MB)"
        )


class FileUploadResponse(BaseModel):
    filename: str
    size: int
    created_at: datetime


def try_write_file(
    path: Path, content: bytes, update: bool = False
) -> FileUploadResponse:
    """Write file content to disk with error handling.

    Args:
        path: Path to write
        content: File content bytes
        update: If True, update existing file (errors if parent doesn't exist).
                If False, create new file (errors if file already exists, creates parent dirs).

    Returns:
        FileUploadResponse containing filename, size, and created_at timestamp

    Raises:
        NotAuthorizedException: If permission denied
        InternalServerException: If file exists (update=False), parent missing (update=True), or other OS error
    """
    try:
        if not update:
            if path.exists():
                raise OSError(f"File already exists: {path}")
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            if not path.parent.exists():
                raise OSError(f"Parent directory does not exist: {path.parent}")

        path.write_bytes(content)
        action = "Updated" if update else "Created"
        logger.debug(f"{action} file at {path}")
        return FileUploadResponse(
            filename=os.path.basename(path),
            size=len(content),
            created_at=datetime.now(),
        )
    except PermissionError as e:
        action = "update" if update else "create"
        logger.error(
            f"User does not have permission to {action} file at path {path}: {e}"
        )
        raise NotAuthorizedException(f"Permission denied: {e}")
    except (OSError, Exception) as e:
        action = "update" if update else "create"
        logger.error(f"Failed to {action} file at path {path}: {e}")
        raise InternalServerException(f"Failed to {action} file: {e}")


def try_delete_file(file_path: Path) -> Path:
    """Delete a file with comprehensive error handling.

    Args:
        file_path: Path to the file to delete

    Returns:
        Dictionary with success message

    Raises:
        NotAuthorizedException: If permission denied
        InternalServerException: If other error occurs
    """
    try:
        file_path.unlink()
        logger.debug(f"Deleted file at {file_path}")
        return file_path
    except PermissionError as e:
        logger.error(f"Permission denied deleting file at {file_path}: {e}")
        raise NotAuthorizedException(f"Permission denied: {e}")
    except Exception as e:
        logger.error(f"Failed to delete file at {file_path}: {e}")
        raise InternalServerException(f"Failed to delete file: {e}")


def try_read_file(file_path: Path) -> File:
    """Read a file and return it with comprehensive error handling.

    Args:
        file_path: Path to the file to read

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
        logger.error(f"Failed to read file at {file_path}: {e}")
        raise InternalServerException(f"Failed to read file: {e}")
