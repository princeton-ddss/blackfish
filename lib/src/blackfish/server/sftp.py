"""Remote file management utilities via SFTP.

This module provides SFTP-based file operations for remote server access.
"""

from __future__ import annotations

import os
import stat
from datetime import datetime
from dataclasses import dataclass
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
from blackfish.server.models.profile import SlurmProfile, deserialize_profile
from blackfish.server.config import config as blackfish_config

if TYPE_CHECKING:
    from paramiko.sftp_client import SFTPClient


@dataclass
class RemoteFileStats:
    """File statistics for remote files."""

    name: str
    path: str
    is_dir: bool
    size: int
    modified_at: datetime
    permissions: str


class RemoteFileUploadResponse(BaseModel):
    """Response for successful remote file upload."""

    filename: str
    size: int
    created_at: datetime
    remote_path: str


def resolve_remote_path(profile: SlurmProfile, relative_path: str) -> str:
    """Resolve a path relative to the profile's home_dir.

    Args:
        profile: The SFTP profile containing home_dir
        relative_path: Path relative to home_dir

    Returns:
        Absolute path on remote system

    Raises:
        ValidationException: If path attempts directory traversal
    """
    # Handle empty or root path
    stripped = relative_path.lstrip("/")
    if not stripped:
        return profile.home_dir

    # Normalize the path
    normalized = os.path.normpath(stripped)

    # Check for directory traversal
    if normalized.startswith("..") or "/../" in relative_path:
        raise ValidationException("Path traversal not allowed")

    full_path = os.path.join(profile.home_dir, normalized)

    # Ensure result is still under home_dir
    if not os.path.normpath(full_path).startswith(os.path.normpath(profile.home_dir)):
        raise ValidationException("Path must be within profile home directory")

    return full_path


def format_permissions(mode: int) -> str:
    """Convert numeric mode to rwx string format."""
    perms = ["r", "w", "x"]
    result = ""
    for i in range(2, -1, -1):
        bits = (mode >> (i * 3)) & 0o7
        for j, p in enumerate(perms):
            result += p if bits & (4 >> j) else "-"
    return result


def get_remote_profile(profile_name: str) -> SlurmProfile:
    """Look up a remote profile by name.

    Args:
        profile_name: Name of the profile to look up

    Returns:
        SlurmProfile instance

    Raises:
        NotFoundException: If profile not found
        ValidationException: If profile is local (not remote)
    """
    try:
        profile = deserialize_profile(blackfish_config.HOME_DIR, profile_name)
    except FileNotFoundError:
        raise NotFoundException("Profile configuration not found")

    if profile is None:
        raise NotFoundException(f"Profile '{profile_name}' not found")

    if not isinstance(profile, SlurmProfile) or profile.is_local():
        raise ValidationException(f"Profile '{profile_name}' is not a remote profile")

    return profile


def sftp_listdir(
    sftp: "SFTPClient",
    profile: SlurmProfile,
    relative_path: str,
    hidden: bool = False,
) -> list[RemoteFileStats]:
    """List directory contents via SFTP.

    Args:
        sftp: Active SFTP client
        profile: Remote profile
        relative_path: Path relative to profile's home_dir
        hidden: Include hidden files (starting with .)

    Returns:
        List of RemoteFileStats

    Raises:
        FileNotFoundError: If path doesn't exist
        PermissionError: If no read access
        OSError: If connection fails
    """
    full_path = resolve_remote_path(profile, relative_path)

    try:
        entries = sftp.listdir_attr(full_path)
    except (FileNotFoundError, PermissionError):
        raise
    except Exception as e:
        logger.error(f"SFTP listdir error: {e}")
        raise OSError(str(e)) from e

    # Normalize relative_path for building entry paths
    base_relative = relative_path.strip("/") if relative_path else ""

    results = []
    for attr in entries:
        if not hidden and attr.filename.startswith("."):
            continue
        # Return paths relative to home_dir, not absolute paths
        if base_relative:
            entry_relative_path = f"{base_relative}/{attr.filename}"
        else:
            entry_relative_path = attr.filename
        results.append(
            RemoteFileStats(
                name=attr.filename,
                path=entry_relative_path,
                is_dir=stat.S_ISDIR(attr.st_mode) if attr.st_mode else False,
                size=attr.st_size or 0,
                modified_at=(
                    datetime.fromtimestamp(attr.st_mtime)
                    if attr.st_mtime
                    else datetime.now()
                ),
                permissions=(
                    format_permissions(attr.st_mode & 0o777)
                    if attr.st_mode
                    else "rwxrwxrwx"
                ),
            )
        )

    return results


def sftp_stat(
    sftp: "SFTPClient",
    profile: SlurmProfile,
    relative_path: str,
) -> RemoteFileStats:
    """Get file statistics via SFTP.

    Args:
        sftp: Active SFTP client
        profile: Remote profile
        relative_path: Path relative to profile's home_dir

    Returns:
        RemoteFileStats for the path

    Raises:
        FileNotFoundError: If path doesn't exist
        PermissionError: If no read access
        OSError: If connection fails
    """
    full_path = resolve_remote_path(profile, relative_path)

    try:
        attr = sftp.stat(full_path)
    except (FileNotFoundError, PermissionError):
        raise
    except Exception as e:
        logger.error(f"SFTP stat error: {e}")
        raise OSError(str(e)) from e

    # Return relative path, not absolute
    normalized_relative = relative_path.strip("/") if relative_path else ""
    return RemoteFileStats(
        name=os.path.basename(full_path),
        path=normalized_relative,
        is_dir=stat.S_ISDIR(attr.st_mode) if attr.st_mode else False,
        size=attr.st_size or 0,
        modified_at=(
            datetime.fromtimestamp(attr.st_mtime) if attr.st_mtime else datetime.now()
        ),
        permissions=(
            format_permissions(attr.st_mode & 0o777) if attr.st_mode else "rwxrwxrwx"
        ),
    )


def sftp_exists(
    sftp: "SFTPClient",
    profile: SlurmProfile,
    relative_path: str,
) -> bool:
    """Check if path exists via SFTP.

    Args:
        sftp: Active SFTP client
        profile: Remote profile
        relative_path: Path relative to profile's home_dir

    Returns:
        True if path exists, False otherwise
    """
    full_path = resolve_remote_path(profile, relative_path)

    try:
        sftp.stat(full_path)
        return True
    except FileNotFoundError:
        return False
    except Exception as e:
        logger.error(f"SFTP exists check error: {e}")
        raise OSError(str(e)) from e


def sftp_mkdir(
    sftp: "SFTPClient",
    profile: SlurmProfile,
    relative_path: str,
) -> None:
    """Create directory via SFTP.

    Args:
        sftp: Active SFTP client
        profile: Remote profile
        relative_path: Path relative to profile's home_dir

    Raises:
        FileNotFoundError: If parent path doesn't exist
        PermissionError: If no write access
        ValueError: If directory already exists
        OSError: If connection fails
    """
    full_path = resolve_remote_path(profile, relative_path)

    try:
        sftp.mkdir(full_path)
    except (FileNotFoundError, PermissionError):
        raise
    except IOError as e:
        if "exists" in str(e).lower():
            raise ValueError(f"Directory already exists: {full_path}") from e
        logger.error(f"SFTP mkdir error: {e}")
        raise OSError(str(e)) from e
    except Exception as e:
        logger.error(f"SFTP mkdir error: {e}")
        raise OSError(str(e)) from e


def sftp_delete(
    sftp: "SFTPClient",
    profile: SlurmProfile,
    relative_path: str,
) -> None:
    """Delete file or directory via SFTP.

    Args:
        sftp: Active SFTP client
        profile: Remote profile
        relative_path: Path relative to profile's home_dir

    Raises:
        FileNotFoundError: If path doesn't exist
        PermissionError: If no write access
        ValueError: If directory not empty
        OSError: If connection fails
    """
    full_path = resolve_remote_path(profile, relative_path)

    try:
        attr = sftp.stat(full_path)
        if stat.S_ISDIR(attr.st_mode) if attr.st_mode else False:
            sftp.rmdir(full_path)
        else:
            sftp.remove(full_path)
    except (FileNotFoundError, PermissionError):
        raise
    except IOError as e:
        if "not empty" in str(e).lower():
            raise ValueError(f"Directory not empty: {full_path}") from e
        logger.error(f"SFTP delete error: {e}")
        raise OSError(str(e)) from e
    except Exception as e:
        logger.error(f"SFTP delete error: {e}")
        raise OSError(str(e)) from e


def sftp_rename(
    sftp: "SFTPClient",
    profile: SlurmProfile,
    old_relative_path: str,
    new_relative_path: str,
) -> None:
    """Rename file or directory via SFTP.

    Args:
        sftp: Active SFTP client
        profile: Remote profile
        old_relative_path: Current path relative to profile's home_dir
        new_relative_path: New path relative to profile's home_dir

    Raises:
        FileNotFoundError: If source path doesn't exist
        PermissionError: If no write access
        OSError: If connection fails
    """
    old_full_path = resolve_remote_path(profile, old_relative_path)
    new_full_path = resolve_remote_path(profile, new_relative_path)

    try:
        sftp.rename(old_full_path, new_full_path)
    except (FileNotFoundError, PermissionError):
        raise
    except Exception as e:
        logger.error(f"SFTP rename error: {e}")
        raise OSError(str(e)) from e


def remote_read_file(profile: SlurmProfile, relative_path: str) -> bytes:
    """Read file content from remote server.

    Args:
        profile: Remote profile
        relative_path: Path relative to profile's home_dir

    Returns:
        File content as bytes

    Raises:
        NotFoundException: If file doesn't exist
        NotAuthorizedException: If permission denied
        InternalServerException: If connection fails
    """
    full_path = resolve_remote_path(profile, relative_path)

    try:
        with Connection(host=profile.host, user=profile.user) as conn:
            with conn.sftp() as sftp:
                with sftp.open(full_path, "rb") as f:
                    content: bytes = f.read()
                    return content
    except FileNotFoundError:
        raise NotFoundException(f"Remote file not found: {full_path}")
    except PermissionError:
        raise NotAuthorizedException(f"Permission denied: {full_path}")
    except Exception as e:
        logger.error(f"Remote file read failed: {e}")
        raise InternalServerException(f"SFTP read failed: {e}")


def remote_write_file(
    profile: SlurmProfile,
    relative_path: str,
    content: bytes,
    update: bool = False,
) -> RemoteFileUploadResponse:
    """Write file content to remote server.

    Args:
        profile: Remote profile
        relative_path: Path relative to profile's home_dir
        content: File content as bytes
        update: If True, update existing file; if False, create new

    Returns:
        RemoteFileUploadResponse with file details

    Raises:
        ValidationException: If file exists (update=False) or doesn't exist (update=True)
        NotAuthorizedException: If permission denied
        InternalServerException: If connection fails
    """
    full_path = resolve_remote_path(profile, relative_path)

    try:
        with Connection(host=profile.host, user=profile.user) as conn:
            with conn.sftp() as sftp:
                # Check existence
                exists = True
                try:
                    sftp.stat(full_path)
                except FileNotFoundError:
                    exists = False

                if not update and exists:
                    raise ValidationException(
                        f"Remote file already exists: {full_path}"
                    )
                if update and not exists:
                    raise NotFoundException(f"Remote file not found: {full_path}")

                # Create parent directories if needed (for new files)
                if not update:
                    parent_dir = os.path.dirname(full_path)
                    _ensure_remote_dir(sftp, parent_dir)

                # Write file
                with sftp.open(full_path, "wb") as f:
                    f.write(content)

                return RemoteFileUploadResponse(
                    filename=os.path.basename(full_path),
                    size=len(content),
                    created_at=datetime.now(),
                    remote_path=full_path,
                )
    except (ValidationException, NotFoundException):
        raise
    except PermissionError:
        raise NotAuthorizedException(f"Permission denied: {full_path}")
    except Exception as e:
        logger.error(f"Remote file write failed: {e}")
        raise InternalServerException(f"SFTP write failed: {e}")


def remote_delete_file(profile: SlurmProfile, relative_path: str) -> str:
    """Delete file from remote server.

    Args:
        profile: Remote profile
        relative_path: Path relative to profile's home_dir

    Returns:
        Full path of deleted file

    Raises:
        NotFoundException: If file doesn't exist
        NotAuthorizedException: If permission denied
        InternalServerException: If connection fails
    """
    full_path = resolve_remote_path(profile, relative_path)

    try:
        with Connection(host=profile.host, user=profile.user) as conn:
            with conn.sftp() as sftp:
                sftp.remove(full_path)
                return full_path
    except FileNotFoundError:
        raise NotFoundException(f"Remote file not found: {full_path}")
    except PermissionError:
        raise NotAuthorizedException(f"Permission denied: {full_path}")
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
