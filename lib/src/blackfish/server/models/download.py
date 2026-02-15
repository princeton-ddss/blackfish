from __future__ import annotations

from enum import StrEnum, auto
from typing import Optional

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy.orm import Mapped, mapped_column


class DownloadStatus(StrEnum):
    """Status of a model download task."""

    PENDING = auto()
    DOWNLOADING = auto()
    COMPLETED = auto()
    FAILED = auto()


class DownloadTask(UUIDAuditBase):
    """Track model download tasks for background processing."""

    __tablename__ = "download_task"

    repo_id: Mapped[str]  # e.g., "meta-llama/Llama-2-7b-hf"
    profile: Mapped[str]  # Profile name
    revision: Mapped[Optional[str]] = mapped_column(default=None)  # None = latest
    status: Mapped[str] = mapped_column(default=DownloadStatus.PENDING)
    error_message: Mapped[Optional[str]] = mapped_column(default=None)
    model_id: Mapped[Optional[str]] = mapped_column(default=None)  # Set when completed
