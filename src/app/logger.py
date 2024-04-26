from __future__ import annotations

from copy import copy
import logging
import colorlog
from app.config import default_config as config
import os

class CustomFormatter(colorlog.ColoredFormatter):
    def formatMessage(self, record: logging.LogRecord) -> str:
        recordcopy = copy(record)
        seperator = " " * (9 - len(recordcopy.levelname))
        recordcopy.__dict__["seperator"] = seperator
        return super().formatMessage(recordcopy)

if config.BLACKFISH_DEBUG:
    handler = colorlog.StreamHandler()
    formatter = CustomFormatter(
        "%(log_color)s%(levelname)s%(white)s:%(seperator)s%(message)s %(thin)s[%(asctime)s.%(msecs)03d]",
        log_colors={
            "DEBUG": "blue",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    logger = colorlog.getLogger("blackfish")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
else:
    handler = logging.FileHandler(f"{os.path.join(config.BLACKFISH_HOME, 'logs')}")
    formatter = logging.Formatter(
        "[%(asctime)s.%(msecs)03d] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    logger = colorlog.getLogger("blackfish")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
