"""Blackfish - Programmatic interface for managing ML inference services."""

from __future__ import annotations

from blackfish.client import Blackfish
from blackfish.service import ManagedService
from blackfish.utils import set_logging_level
from blackfish.server.services.base import Service, ServiceStatus

__all__ = [
    "Blackfish",
    "ManagedService",
    "Service",
    "ServiceStatus",
    "set_logging_level",
]
