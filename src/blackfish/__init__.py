"""Blackfish - Programmatic interface for managing ML inference services."""

from __future__ import annotations

# Import public API
from blackfish.client import Blackfish
from blackfish.service import ManagedService
from blackfish.utils import set_logging_level

# Re-export types from app for convenience
from app.services.base import Service, ServiceStatus

__all__ = [
    "Blackfish",
    "ManagedService",
    "Service",
    "ServiceStatus",
    "set_logging_level",
]

__version__ = "0.2.1"
