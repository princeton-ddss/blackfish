"""Remote file management utilities via SFTP.

This module provides SFTP-based file operations for remote server access.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING

from fabric.connection import Connection
from pydantic import BaseModel

from litestar.exceptions import (
    NotFoundException,
    NotAuthorizedException,
    InternalServerException,
    ValidationException,
)

from blackfish.server.logger import logger
from blackfish.server.models.profile import SlurmProfile

if TYPE_CHECKING:
    from paramiko.sftp_client import SFTPClient


class WriteFileResponse(BaseModel):
    """Response for successful file write."""

    filename: str
    size: int
    created_at: datetime
    path: str


def read_file(profile: SlurmProfile, path: str) -> bytes:
    """Read file content from remote server.

    Args:
        profile: Remote SlurmProfile
        path: Absolute path to file

    Returns:
        File content as bytes

    Raises:
        NotFoundException: If file doesn't exist
        NotAuthorizedException: If permission denied
        InternalServerException: If connection fails
    """
    try:
        with Connection(host=profile.host, user=profile.user) as conn:
            with conn.sftp() as sftp:
                with sftp.open(path, "rb") as f:
                    content: bytes = f.read()
                    return content
    except FileNotFoundError:
        raise NotFoundException(f"Remote file not found: {path}")
    except PermissionError:
        raise NotAuthorizedException(f"Permission denied: {path}")
    except Exception as e:
        logger.error(f"Remote file read failed: {e}")
        raise InternalServerException(f"SFTP read failed: {e}")


def write_file(
    profile: SlurmProfile,
    path: str,
    content: bytes,
    update: bool = False,
) -> WriteFileResponse:
    """Write file content to remote server.

    Args:
        profile: Remote SlurmProfile
        path: Absolute path to file
        content: File content as bytes
        update: If True, update existing file; if False, create new

    Returns:
        WriteResponse with file details

    Raises:
        ValidationException: If file exists (update=False) or doesn't exist (update=True)
        NotAuthorizedException: If permission denied
        InternalServerException: If connection fails
    """
    try:
        with Connection(host=profile.host, user=profile.user) as conn:
            with conn.sftp() as sftp:
                exists = True
                try:
                    sftp.stat(path)
                except FileNotFoundError:
                    exists = False

                if not update and exists:
                    raise ValidationException(f"Remote file already exists: {path}")
                if update and not exists:
                    raise NotFoundException(f"Remote file not found: {path}")

                if not update:
                    parent_dir = os.path.dirname(path)
                    _ensure_remote_dir(sftp, parent_dir)

                with sftp.open(path, "wb") as f:
                    f.write(content)

                return WriteFileResponse(
                    filename=os.path.basename(path),
                    size=len(content),
                    created_at=datetime.now(),
                    path=path,
                )
    except (ValidationException, NotFoundException):
        raise
    except PermissionError:
        raise NotAuthorizedException(f"Permission denied: {path}")
    except IOError as e:
        import errno as errno_module
        err_num = getattr(e, "errno", None)
        logger.error(f"Remote file write IOError: {e} (errno={err_num})")

        if err_num == errno_module.ENOSPC:
            raise InternalServerException("SFTP write failed: No space left on device")
        elif err_num == errno_module.EDQUOT:
            raise InternalServerException("SFTP write failed: Disk quota exceeded")
        elif str(e) == "Failure" and err_num is None:
            raise InternalServerException(
                "SFTP write failed: Server returned generic failure "
                "(possible causes: disk quota exceeded, no space left, or permission issue)"
            )
        raise InternalServerException(f"SFTP write failed: {e}")
    except Exception as e:
        logger.error(f"Remote file write failed: {e}")
        raise InternalServerException(f"SFTP write failed: {e}")


def delete_file(profile: SlurmProfile, path: str) -> str:
    """Delete file from remote server.

    Args:
        profile: Remote SlurmProfile
        path: Absolute path to file

    Returns:
        Path of deleted file

    Raises:
        NotFoundException: If file doesn't exist
        NotAuthorizedException: If permission denied
        InternalServerException: If connection fails
    """
    try:
        with Connection(host=profile.host, user=profile.user) as conn:
            with conn.sftp() as sftp:
                sftp.remove(path)
                return path
    except FileNotFoundError:
        raise NotFoundException(f"Remote file not found: {path}")
    except PermissionError:
        raise NotAuthorizedException(f"Permission denied: {path}")
    except Exception as e:
        logger.error(f"Remote file delete failed: {e}")
        raise InternalServerException(f"SFTP delete failed: {e}")


def _ensure_remote_dir(sftp: "SFTPClient", path: str) -> None:
    """Ensure remote directory exists, creating parent directories as needed."""
    try:
        sftp.stat(path)
    except FileNotFoundError:
        parent = os.path.dirname(path)
        if parent and parent != path:
            _ensure_remote_dir(sftp, parent)
        try:
            sftp.mkdir(path)
        except IOError:
            # Directory may have been created by another process
            pass
