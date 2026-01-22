"""WebSocket-based remote file browser.

This module provides a WebSocket endpoint for browsing remote file systems
via SFTP, with persistent connections for efficient file operations.
"""

from __future__ import annotations

import asyncio
import json
import os
import stat
from typing import Annotated, Any, Literal, TYPE_CHECKING
from enum import StrEnum
from datetime import datetime

from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from fabric.connection import Connection
from litestar import WebSocket
from litestar.handlers import WebsocketListener

from blackfish.server.logger import logger
from blackfish.server.models.profile import (
    SlurmProfile,
    deserialize_profile,
)
from blackfish.server.config import config as blackfish_config

if TYPE_CHECKING:
    from paramiko.sftp_client import SFTPClient


class FileEntry(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: int
    modified_at: datetime
    permissions: str


class ErrorCode(StrEnum):
    INVALID_PROFILE = "invalid_profile"
    CONNECTION_ERROR = "connection_error"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    INVALID_PATH = "invalid_path"
    INVALID_REQUEST = "invalid_request"
    UNKNOWN_ACTION = "unknown_action"


class ListMessage(BaseModel):
    action: Literal["list"]
    id: str | None = None
    path: str = "/"
    show_hidden: bool = False


class StatMessage(BaseModel):
    action: Literal["stat"]
    id: str | None = None
    path: str


class ExistsMessage(BaseModel):
    action: Literal["exists"]
    id: str | None = None
    path: str


class MkdirMessage(BaseModel):
    action: Literal["mkdir"]
    id: str | None = None
    path: str


class DeleteMessage(BaseModel):
    action: Literal["delete"]
    id: str | None = None
    path: str


class RenameMessage(BaseModel):
    action: Literal["rename"]
    id: str | None = None
    old_path: str
    new_path: str


BrowserMessage = Annotated[
    ListMessage
    | StatMessage
    | ExistsMessage
    | MkdirMessage
    | DeleteMessage
    | RenameMessage,
    Field(discriminator="action"),
]

BrowserMessageAdapter: TypeAdapter[BrowserMessage] = TypeAdapter(BrowserMessage)


def _format_permissions(mode: int) -> str:
    """Convert numeric mode to rwx string format."""
    perms = ["r", "w", "x"]
    result = ""
    for i in range(2, -1, -1):
        bits = (mode >> (i * 3)) & 0o7
        for j, p in enumerate(perms):
            result += p if bits & (4 >> j) else "-"
    return result


def _map_exception_to_error_code(error: Exception) -> ErrorCode:
    """Map exception to ErrorCode enum."""
    if isinstance(error, FileNotFoundError):
        return ErrorCode.NOT_FOUND
    elif isinstance(error, PermissionError):
        return ErrorCode.PERMISSION_DENIED
    elif isinstance(error, ValueError):
        return ErrorCode.INVALID_PATH
    elif isinstance(error, OSError):
        return ErrorCode.CONNECTION_ERROR
    else:
        return ErrorCode.CONNECTION_ERROR


class RemoteFileBrowser:
    def __init__(self, profile: SlurmProfile) -> None:
        self.profile = profile
        self._connection: Connection | None = None
        self._sftp: "SFTPClient | None" = None

    def connect(self) -> None:
        """Establish SSH connection and open SFTP session."""
        if self.profile.is_local():
            raise ValueError("Profile must be a remote SlurmProfile")

        self._connection = Connection(
            host=self.profile.host,
            user=self.profile.user,
        )
        self._connection.__enter__()
        self._sftp = self._connection.sftp().__enter__()
        logger.info(
            f"SFTP connection established to {self.profile.user}@{self.profile.host}"
        )

    def disconnect(self) -> None:
        """Close SFTP session and SSH connection."""
        if self._sftp:
            try:
                self._sftp.__exit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing SFTP session: {e}")
        if self._connection:
            try:
                self._connection.__exit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing SSH connection: {e}")
        self._sftp = None
        self._connection = None
        logger.info("SFTP connection closed")

    def __enter__(self) -> "RemoteFileBrowser":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.disconnect()

    @property
    def sftp(self) -> "SFTPClient":
        """Get the active SFTP client."""
        if self._sftp is None:
            raise RuntimeError("SFTP connection not established")
        return self._sftp

    def list_dir(self, path: str, show_hidden: bool = False) -> list[FileEntry]:
        """List directory contents.

        Args:
            path: Absolute path to directory
            show_hidden: Include hidden files (starting with .)

        Returns:
            List of FileEntry models
        """
        try:
            entries = self.sftp.listdir_attr(path)
        except (FileNotFoundError, PermissionError):
            raise
        except Exception as e:
            logger.error(f"SFTP listdir error: {e}")
            raise OSError(str(e)) from e

        results = []
        for attr in entries:
            if not show_hidden and attr.filename.startswith("."):
                continue
            results.append(
                FileEntry(
                    name=attr.filename,
                    path=os.path.join(path, attr.filename),
                    is_dir=stat.S_ISDIR(attr.st_mode) if attr.st_mode else False,
                    size=attr.st_size or 0,
                    modified_at=(
                        datetime.fromtimestamp(attr.st_mtime)
                        if attr.st_mtime
                        else datetime.now()
                    ),
                    permissions=(
                        _format_permissions(attr.st_mode & 0o777)
                        if attr.st_mode
                        else "rwxrwxrwx"
                    ),
                )
            )
        return results

    def stat(self, path: str) -> FileEntry:
        """Get file statistics.

        Args:
            path: Absolute path to file or directory

        Returns:
            FileEntry model
        """
        try:
            attr = self.sftp.stat(path)
        except (FileNotFoundError, PermissionError):
            raise
        except Exception as e:
            logger.error(f"SFTP stat error: {e}")
            raise OSError(str(e)) from e

        return FileEntry(
            name=os.path.basename(path),
            path=path,
            is_dir=stat.S_ISDIR(attr.st_mode) if attr.st_mode else False,
            size=attr.st_size or 0,
            modified_at=(
                datetime.fromtimestamp(attr.st_mtime)
                if attr.st_mtime
                else datetime.now()
            ),
            permissions=(
                _format_permissions(attr.st_mode & 0o777)
                if attr.st_mode
                else "rwxrwxrwx"
            ),
        )

    def exists(self, path: str) -> bool:
        """Check if path exists.

        Args:
            path: Absolute path to check

        Returns:
            True if path exists
        """
        try:
            self.sftp.stat(path)
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"SFTP exists check error: {e}")
            raise OSError(str(e)) from e

    def mkdir(self, path: str) -> None:
        """Create directory.

        Args:
            path: Absolute path to create
        """
        try:
            self.sftp.mkdir(path)
        except (FileNotFoundError, PermissionError):
            raise
        except IOError as e:
            if "exists" in str(e).lower():
                raise ValueError(f"Directory already exists: {path}") from e
            logger.error(f"SFTP mkdir error: {e}")
            raise OSError(str(e)) from e
        except Exception as e:
            logger.error(f"SFTP mkdir error: {e}")
            raise OSError(str(e)) from e

    def delete(self, path: str) -> None:
        """Delete file or directory.

        Args:
            path: Absolute path to delete
        """
        try:
            attr = self.sftp.stat(path)
            if stat.S_ISDIR(attr.st_mode) if attr.st_mode else False:
                self.sftp.rmdir(path)
            else:
                self.sftp.remove(path)
        except (FileNotFoundError, PermissionError):
            raise
        except IOError as e:
            if "not empty" in str(e).lower():
                raise ValueError(f"Directory not empty: {path}") from e
            logger.error(f"SFTP delete error: {e}")
            raise OSError(str(e)) from e
        except Exception as e:
            logger.error(f"SFTP delete error: {e}")
            raise OSError(str(e)) from e

    def rename(self, old_path: str, new_path: str) -> None:
        """Rename file or directory.

        Args:
            old_path: Current absolute path
            new_path: New absolute path
        """
        try:
            self.sftp.rename(old_path, new_path)
        except (FileNotFoundError, PermissionError):
            raise
        except Exception as e:
            logger.error(f"SFTP rename error: {e}")
            raise OSError(str(e)) from e


class RemoteFileBrowserSession(WebsocketListener):
    """WebSocket handler for remote file browsing with persistent SFTP connection."""

    path = "/ws/files/{profile_name:str}"

    browser: RemoteFileBrowser | None = None
    profile_name: str | None = None

    async def on_accept(
        self, socket: WebSocket[Any, Any, Any], profile_name: str
    ) -> None:
        """Handle WebSocket connection acceptance.

        Validates the profile and establishes SFTP connection.
        """
        self.profile_name = profile_name

        try:
            profile = deserialize_profile(blackfish_config.HOME_DIR, profile_name)
        except FileNotFoundError:
            await socket.send_json(
                {
                    "status": "error",
                    "error": {
                        "code": ErrorCode.INVALID_PROFILE,
                        "message": "Profile configuration file not found",
                    },
                }
            )
            await socket.close()
            return

        if profile is None:
            await socket.send_json(
                {
                    "status": "error",
                    "error": {
                        "code": ErrorCode.INVALID_PROFILE,
                        "message": f"Profile '{profile_name}' not found",
                    },
                }
            )
            await socket.close()
            return

        if not isinstance(profile, SlurmProfile) or profile.is_local():
            await socket.send_json(
                {
                    "status": "error",
                    "error": {
                        "code": ErrorCode.INVALID_PROFILE,
                        "message": f"Profile '{profile_name}' is not a remote profile",
                    },
                }
            )
            await socket.close()
            return

        try:
            self.browser = RemoteFileBrowser(profile)
            await asyncio.to_thread(self.browser.connect)
            await socket.send_json(
                {
                    "status": "connected",
                    "profile": profile_name,
                    "home_dir": profile.home_dir,
                }
            )
        except Exception as e:
            logger.error(f"Failed to establish SFTP connection: {e}")
            await socket.send_json(
                {
                    "status": "error",
                    "error": {
                        "code": ErrorCode.CONNECTION_ERROR,
                        "message": f"Failed to connect to {profile.host}: {e}",
                    },
                }
            )
            await socket.close()

    async def on_disconnect(self, socket: WebSocket[Any, Any, Any]) -> None:
        """Handle WebSocket disconnection - clean up SFTP connection."""
        if self.browser:
            try:
                await asyncio.to_thread(self.browser.disconnect)
            except Exception as e:
                logger.warning(f"Error during disconnect cleanup: {e}")
            self.browser = None
        logger.info(f"WebSocket disconnected for profile {self.profile_name}")

    async def on_receive(self, data: str) -> str:
        """Handle incoming WebSocket messages.

        Args:
            data: JSON string containing the request

        Returns:
            JSON string containing the response
        """
        try:
            raw_message = json.loads(data)
        except json.JSONDecodeError as e:
            return json.dumps(
                {
                    "status": "error",
                    "error": {
                        "code": ErrorCode.INVALID_REQUEST,
                        "message": f"Invalid JSON: {e}",
                    },
                }
            )

        try:
            message = BrowserMessageAdapter.validate_python(raw_message)
        except ValidationError as e:
            action = (
                raw_message.get("action") if isinstance(raw_message, dict) else None
            )
            if action is not None and action not in (
                "list",
                "stat",
                "exists",
                "mkdir",
                "delete",
                "rename",
            ):
                return json.dumps(
                    {
                        "id": raw_message.get("id")
                        if isinstance(raw_message, dict)
                        else None,
                        "status": "error",
                        "action": action,
                        "error": {
                            "code": ErrorCode.UNKNOWN_ACTION,
                            "message": f"Unknown action: {action}",
                        },
                    }
                )
            return json.dumps(
                {
                    "id": raw_message.get("id")
                    if isinstance(raw_message, dict)
                    else None,
                    "status": "error",
                    "action": action,
                    "error": {
                        "code": ErrorCode.INVALID_REQUEST,
                        "message": str(e.errors()[0]["msg"]) if e.errors() else str(e),
                    },
                }
            )

        response = await asyncio.to_thread(self.handle_message, message)
        return json.dumps(response, default=str)

    def handle_message(self, message: BrowserMessage) -> dict[str, Any]:
        """Route message to appropriate handler based on action.

        Args:
            message: Validated request message

        Returns:
            Response dict
        """
        if self.browser is None:
            return {
                "status": "error",
                "error": {
                    "code": ErrorCode.CONNECTION_ERROR,
                    "message": "SFTP connection not established",
                },
            }

        try:
            match message:
                case ListMessage():
                    entries = self.browser.list_dir(
                        message.path, show_hidden=message.show_hidden
                    )
                    return {
                        "id": message.id,
                        "status": "ok",
                        "action": message.action,
                        "entries": [e.model_dump(mode="json") for e in entries],
                    }

                case StatMessage():
                    entry = self.browser.stat(message.path)
                    return {
                        "id": message.id,
                        "status": "ok",
                        "action": message.action,
                        "entry": entry.model_dump(mode="json"),
                    }

                case ExistsMessage():
                    exists = self.browser.exists(message.path)
                    return {
                        "id": message.id,
                        "status": "ok",
                        "action": message.action,
                        "data": {"exists": exists},
                    }

                case MkdirMessage():
                    self.browser.mkdir(message.path)
                    return {
                        "id": message.id,
                        "status": "ok",
                        "action": message.action,
                    }

                case DeleteMessage():
                    self.browser.delete(message.path)
                    return {
                        "id": message.id,
                        "status": "ok",
                        "action": message.action,
                    }

                case RenameMessage():
                    self.browser.rename(message.old_path, message.new_path)
                    return {
                        "id": message.id,
                        "status": "ok",
                        "action": message.action,
                    }

        except (FileNotFoundError, PermissionError, ValueError, OSError) as e:
            return {
                "id": message.id,
                "status": "error",
                "action": message.action,
                "error": {
                    "code": _map_exception_to_error_code(e),
                    "message": str(e),
                },
            }
        except Exception as e:
            logger.error(f"Unexpected error handling message: {e}")
            return {
                "id": message.id,
                "status": "error",
                "action": message.action,
                "error": {
                    "code": ErrorCode.CONNECTION_ERROR,
                    "message": str(e),
                },
            }
