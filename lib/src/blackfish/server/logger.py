from __future__ import annotations

from copy import copy
import logging
from typing import Any
import colorlog
from blackfish.server.config import config as app_config
import os


class CustomFormatter(colorlog.ColoredFormatter):
    def formatMessage(self, record: logging.LogRecord) -> str:
        recordcopy = copy(record)
        separator = " " * (9 - len(recordcopy.levelname))
        recordcopy.__dict__["separator"] = separator
        return super().formatMessage(recordcopy)


logger = colorlog.getLogger("blackfish")
logger.setLevel(logging.DEBUG)
stream_handler = colorlog.StreamHandler()
custom_formatter = CustomFormatter(
    (
        "%(log_color)s%(levelname)s%(white)s:%(separator)s%(message)s"
        " %(thin)s[%(asctime)s.%(msecs)03d]"
    ),
    log_colors={
        "DEBUG": "blue",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    },
    datefmt="%Y-%m-%d %H:%M:%S",
)
stream_handler.setFormatter(custom_formatter)
stream_handler.setLevel(logging.DEBUG if app_config.DEBUG else logging.INFO)
logger.addHandler(stream_handler)


class _LazyFileHandler(logging.FileHandler):
    """A `FileHandler` that tolerates a missing app directory.

    The handler is constructed at import time, but `HOME_DIR` is only created
    later by `bootstrap()` — and `bootstrap()` cannot run first, because
    importing `blackfish` at all pulls in this module. `delay=True` keeps the
    constructor from touching the filesystem; this subclass then keeps the
    first write from raising if the directory still isn't there, and disables
    itself so the failure is reported once rather than on every record.

    The log is created 0600: it captures whatever the server logs, on a shared
    filesystem where the default mode would be world-readable.
    """

    def _open(self) -> Any:
        fd = os.open(self.baseFilename, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
        return os.fdopen(fd, self.mode, encoding=self.encoding)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except OSError:
            # Left attached but inert: re-raising here would surface as
            # `--- Logging error ---` noise on every subsequent record.
            self.setLevel(logging.CRITICAL + 1)


if not app_config.DEBUG:
    log_path = os.path.join(app_config.HOME_DIR, "logs")
    file_handler = _LazyFileHandler(log_path, delay=True)
    formatter = logging.Formatter(
        "[%(asctime)s.%(msecs)03d] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    # Existing logs predate the 0600 creation above and may hold tokens that
    # were written world-readable. Tighten them in place on startup.
    try:
        if os.path.isfile(log_path):
            os.chmod(log_path, 0o600)
    except OSError:
        pass
