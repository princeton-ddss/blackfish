"""Utility functions for the Blackfish programmatic interface."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, TypeVar, ParamSpec, cast
from functools import wraps

from blackfish.server.logger import logger


P = ParamSpec("P")
T = TypeVar("T")


def set_logging_level(level: str = "WARNING") -> None:
    """Set the global Blackfish logging level.

    This function controls the logging level for all Blackfish operations.
    By default, the programmatic interface uses WARNING level to reduce
    verbose output. Use this function to change the logging level globally.

    Args:
        level: Logging level string. Must be one of: "DEBUG", "INFO", "WARNING",
               "ERROR", or "CRITICAL". Case-insensitive.

    Examples:
        ```pycon
        >>> import blackfish
        >>> blackfish.set_logging_level("INFO")  # Show info logs
        >>> blackfish.set_logging_level("DEBUG")  # Show all logs including debug
        >>> blackfish.set_logging_level("WARNING")  # Only warnings and errors (default)
        ```
    """
    numeric_level = getattr(logging, level.upper(), None)
    if numeric_level is None:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        raise ValueError(
            f"Invalid logging level: {level}. Must be one of: {', '.join(valid_levels)}"
        )

    for handler in logger.handlers:
        handler.setLevel(numeric_level)


def _async_to_sync(async_func: Callable[P, Any]) -> Callable[P, T]:
    """Decorator to convert async methods to sync by running them in event loop."""

    @wraps(async_func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            # Try to get the running loop
            _ = asyncio.get_running_loop()
            # If we're already in an async context, just call the async function
            raise RuntimeError(
                f"Cannot call sync version of {async_func.__name__} from async context. "
                "Use the async version instead (prefix with 'a')."
            )
        except RuntimeError:
            # No running loop, we can create one
            return cast(T, asyncio.run(async_func(*args, **kwargs)))

    return wrapper
