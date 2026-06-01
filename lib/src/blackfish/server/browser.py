"""WebSocket-based remote file browser.

This module provides a WebSocket endpoint for browsing remote file systems
via SFTP. The underlying SSH+SFTP connection is held by
:mod:`blackfish.server.remote`'s session pool — the WebSocket handler
acquires it per message rather than holding a dedicated connection for
the session's lifetime.
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
from litestar import WebSocket
from litestar.handlers import WebsocketListener

from blackfish.server import remote
from blackfish.server.logger import logger
from blackfish.server.models.profile import (
    SlurmProfile,
    deserialize_profile,
)
from blackfish.server.config import config as blackfish_config

if TYPE_CHECKING:
    from blackfish.server.remote import RemoteSession

# WebSocket close codes (RFC 6455)
WS_CLOSE_NORMAL = 1000  # Normal closure
WS_CLOSE_POLICY_VIOLATION = 1008  # Policy violation (invalid profile, etc.)


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
    limit: int = 1000
    offset: int = 0


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


def _list_directory_entries(
    sess: "RemoteSession",
    path: str,
    show_hidden: bool = False,
    limit: int = 1000,
    offset: int = 0,
) -> tuple[list[FileEntry], int]:
    """List directory contents as :class:`FileEntry` models with pagination.

    Returns ``(entries, total_count)`` — ``total_count`` reflects the count
    after the ``show_hidden`` filter but before pagination, so the caller
    can render an accurate "X of Y" indicator.
    """
    try:
        attrs = sess.sftp.listdir_attr(path)
    except (FileNotFoundError, PermissionError):
        raise
    except Exception as e:
        logger.error(f"SFTP listdir error: {e}")
        raise OSError(str(e)) from e

    if not show_hidden:
        attrs = [a for a in attrs if not a.filename.startswith(".")]

    total_count = len(attrs)
    page = attrs[offset : offset + limit]

    return [
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
        for attr in page
    ], total_count


def _stat_entry(sess: "RemoteSession", path: str) -> FileEntry:
    """Stat ``path`` and return a :class:`FileEntry`."""
    attr = sess.stat(path)
    return FileEntry(
        name=os.path.basename(path),
        path=path,
        is_dir=stat.S_ISDIR(attr.st_mode) if attr.st_mode else False,
        size=attr.st_size or 0,
        modified_at=(
            datetime.fromtimestamp(attr.st_mtime) if attr.st_mtime else datetime.now()
        ),
        permissions=(
            _format_permissions(attr.st_mode & 0o777) if attr.st_mode else "rwxrwxrwx"
        ),
    )


class RemoteFileBrowserSession(WebsocketListener):
    """WebSocket handler for remote file browsing.

    The underlying SSH+SFTP connection is held by the shared pool in
    :mod:`blackfish.server.remote`; each message acquires the pooled
    session for the duration of one operation. Between user actions
    the connection sits idle in the pool, available to other consumers.
    """

    path = "/ws/files/{profile_name:str}"

    profile: SlurmProfile | None = None
    profile_name: str | None = None

    async def on_accept(
        self, socket: WebSocket[Any, Any, Any], profile_name: str
    ) -> None:
        """Validate the profile and probe the connection."""
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
            await socket.close(code=WS_CLOSE_POLICY_VIOLATION)
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
            await socket.close(code=WS_CLOSE_POLICY_VIOLATION)
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
            await socket.close(code=WS_CLOSE_POLICY_VIOLATION)
            return

        # Probe by acquiring the pooled session and reading the home dir;
        # this surfaces auth/connection errors immediately on connect rather
        # than on the first user message.
        def _probe() -> str:
            with remote.acquire(profile.host, profile.user) as sess:
                return sess.home_dir()

        try:
            home_dir = await asyncio.to_thread(_probe)
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
            await socket.close(code=WS_CLOSE_NORMAL)
            return

        self.profile = profile
        await socket.send_json(
            {
                "status": "connected",
                "profile": profile_name,
                "home_dir": home_dir,
            }
        )

    async def on_disconnect(self, socket: WebSocket[Any, Any, Any]) -> None:
        """Pool manages connection lifecycle; nothing to release here."""
        logger.info(f"WebSocket disconnected for profile {self.profile_name}")
        self.profile = None

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
        profile = self.profile
        if profile is None:
            return {
                "status": "error",
                "error": {
                    "code": ErrorCode.CONNECTION_ERROR,
                    "message": "SFTP connection not established",
                },
            }

        try:
            with remote.acquire(profile.host, profile.user) as sess:
                match message:
                    case ListMessage():
                        entries, total = _list_directory_entries(
                            sess,
                            message.path,
                            show_hidden=message.show_hidden,
                            limit=message.limit,
                            offset=message.offset,
                        )
                        return {
                            "id": message.id,
                            "status": "ok",
                            "action": message.action,
                            "entries": [e.model_dump(mode="json") for e in entries],
                            "total": total,
                            "limit": message.limit,
                            "offset": message.offset,
                        }

                    case StatMessage():
                        entry = _stat_entry(sess, message.path)
                        return {
                            "id": message.id,
                            "status": "ok",
                            "action": message.action,
                            "entry": entry.model_dump(mode="json"),
                        }

                    case ExistsMessage():
                        exists = sess.exists(message.path)
                        return {
                            "id": message.id,
                            "status": "ok",
                            "action": message.action,
                            "data": {"exists": exists},
                        }

                    case MkdirMessage():
                        sess.mkdir(message.path)
                        return {
                            "id": message.id,
                            "status": "ok",
                            "action": message.action,
                        }

                    case DeleteMessage():
                        sess.delete(message.path)
                        return {
                            "id": message.id,
                            "status": "ok",
                            "action": message.action,
                        }

                    case RenameMessage():
                        sess.rename(message.old_path, message.new_path)
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
