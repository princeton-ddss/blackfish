from typing import Literal
from enum import StrEnum
from datetime import datetime
from pydantic import BaseModel
from litestar import WebSocket
from litestar.handlers import WebsocketListener

from blackfish.server.models.profile import BlackfishProfile


class ListMessage(BaseModel):
    action: Literal["list"]
    path: str
    show_hidden: bool = False


class StatMessage(BaseModel):
    action: Literal["stat"]
    path: str


class MkdirMessage(BaseModel):
    action: Literal["mkdir"]
    path: str


class Deletemessage(BaseModel):
    action: Literal["delete"]
    path: str


class RenameMessage(BaseModel):
    action: Literal["rename"]
    old_path: str
    new_path: str


BrowserMessage = (
    ListMessage | StatMessage | MkdirMessage | Deletemessage | RenameMessage
)


class FileEntry(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: int
    modified_at: datetime
    permissions: str  # TODO: use class?


class SuccessResponse(BaseModel):
    status: Literal["ok"]
    entries: list[FileEntry] | None = None
    entry: FileEntry | None = None


class ErrorCode(StrEnum):
    INVALID_PROFILE = "invalid_profile"
    CONNECTION_ERROR = "connection_error"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    INVALID_PATH = "invalid_path"
    UNKNOWN_ACTION = "unknown_action"


class ErrorResponse(BaseModel):
    status: Literal["error"]
    code: ErrorCode
    message: str


BrowserResponse = SuccessResponse | ErrorResponse


class RemoteFileBrowser:
    def __init__(self, profile: BlackfishProfile):
        self.profile = profile

    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def list_dir(self, path: str, show_hidden: bool = False) -> list[FileEntry]:
        pass

    def stat(self, path: str) -> FileEntry:
        pass

    def mkdir(self, path: str) -> None:
        pass

    def delete(self, path: str) -> None:
        pass

    def rename(self, old_path: str, new_path: str) -> None:
        pass


class RemoteFileBrowserSession(WebsocketListener):
    path = "/ws/files"

    browser: RemoteFileBrowser | None = None
    profile_name: str | None = None

    async def on_accept(self, socket: WebSocket) -> None:
        pass

    async def on_disconnect(self, socket: WebSocket) -> None:
        pass

    async def on_receive(self, data: BrowserMessage) -> BrowserResponse:
        pass

    def handle_message(self, message: BrowserMessage) -> BrowserResponse:
        pass
