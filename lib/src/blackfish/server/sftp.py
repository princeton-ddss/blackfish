"""Remote file management utilities via SFTP.

Thin domain wrappers around :mod:`blackfish.server.remote`'s pooled SFTP
sessions: each function acquires the shared session for the profile,
performs one SFTP operation, and translates filesystem errors into the
Litestar HTTP exceptions the route handlers expect.

``stream_file`` is the exception — its generator outlives the function
call, so it keeps its own non-pooled :class:`fabric.connection.Connection`
rather than holding the shared session for the duration of the read.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING, Generator

from fabric.connection import Connection
from pydantic import BaseModel

from litestar.exceptions import (
    NotFoundException,
    NotAuthorizedException,
    InternalServerException,
    ValidationException,
)

from blackfish.server import remote
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


def get_file_size(profile: SlurmProfile, path: str) -> int:
    """Get file size from remote server.

    Args:
        profile: Remote SlurmProfile
        path: Absolute path to file

    Returns:
        File size in bytes

    Raises:
        NotFoundException: If file doesn't exist
        NotAuthorizedException: If permission denied
        InternalServerException: If connection fails
    """
    try:
        with remote.acquire(profile.host, profile.user) as sess:
            stat = sess.stat(path)
            size: int | None = stat.st_size
            if size is None:
                raise InternalServerException(f"Could not determine file size: {path}")
            return size
    except FileNotFoundError:
        raise NotFoundException(f"Remote file not found: {path}")
    except PermissionError:
        raise NotAuthorizedException(f"Permission denied: {path}")
    except Exception as e:
        logger.error(f"Remote file stat failed: {e}")
        raise InternalServerException(f"SFTP stat failed: {e}")


def stream_file(
    profile: SlurmProfile, path: str, chunk_size: int = 65536
) -> tuple[int, Generator[bytes, None, None]]:
    """Stream file content from remote server.

    Args:
        profile: Remote SlurmProfile
        path: Absolute path to file
        chunk_size: Size of chunks to yield (default 64KB)

    Returns:
        Tuple of (file_size, generator that yields chunks)

    Raises:
        NotFoundException: If file doesn't exist
        NotAuthorizedException: If permission denied
        InternalServerException: If connection fails
    """
    try:
        conn = Connection(host=profile.host, user=profile.user)
        conn.open()
        sftp = conn.sftp()
        stat = sftp.stat(path)
        file_size: int | None = stat.st_size
        if file_size is None:
            raise InternalServerException(f"Could not determine file size: {path}")
        file_handle = sftp.open(path, "rb")

        def generator() -> Generator[bytes, None, None]:
            try:
                while True:
                    chunk = file_handle.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
            finally:
                file_handle.close()
                sftp.close()
                conn.close()

        return file_size, generator()
    except FileNotFoundError:
        raise NotFoundException(f"Remote file not found: {path}")
    except PermissionError:
        raise NotAuthorizedException(f"Permission denied: {path}")
    except Exception as e:
        logger.error(f"Remote file stream failed: {e}")
        raise InternalServerException(f"SFTP stream failed: {e}")


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
        with remote.acquire(profile.host, profile.user) as sess:
            return sess.read_bytes(path)
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
        with remote.acquire(profile.host, profile.user) as sess:
            exists = sess.exists(path)

            if not update and exists:
                raise ValidationException(f"Remote file already exists: {path}")
            if update and not exists:
                raise NotFoundException(f"Remote file not found: {path}")

            if not update:
                parent_dir = os.path.dirname(path)
                _ensure_remote_dir(sess.sftp, parent_dir)

            sess.write_bytes(path, content)

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
        with remote.acquire(profile.host, profile.user) as sess:
            # Preserve file-only semantics: refuse to silently rmdir.
            sess.sftp.remove(path)
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
