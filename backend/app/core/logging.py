"""
Centralized logging configuration for H.I.R.E.

This module is the single logging interface for the entire backend.
Every module in the application should obtain its logger via
`get_logger(__name__)` rather than calling `logging.getLogger()` or
configuring handlers directly, so that formatting, log level, and
output destinations (console + file) remain consistent across the
codebase.

Usage:
    from app.core.logging import get_logger

    logger = get_logger(__name__)
    logger.info("Something happened.")
    logger.exception("Something failed.")
"""

import logging
import sys
from pathlib import Path

from app.core.config import settings

# Resolve the backend project root (the directory containing app/) so that
# the log location is independent of the current working directory, i.e.
# consistent regardless of where Uvicorn/Python is launched from.
# This file lives at app/core/logging.py, so parents[0]=app/core,
# parents[1]=app, parents[2]=backend project root.
BASE_DIR = Path(__file__).resolve().parents[2]

# Log output location. Created automatically on first configuration.
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "hire.log"

# Consistent format shared by both the console and file handlers:
# <timestamp> | <level> | <module> | <message>
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _configure_root_logger() -> None:
    """
    Attach a console handler and a file handler to the root logger.

    The active log level is derived from settings.DEBUG:
    DEBUG=True -> logging.DEBUG, otherwise -> logging.INFO.

    This function is idempotent. It inspects the root logger's existing
    handlers and returns immediately if any are already attached, which
    prevents duplicate log lines when get_logger() is called from
    multiple modules during application startup.
    """
    root_logger = logging.getLogger()

    if root_logger.handlers:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    root_logger.setLevel(log_level)

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(filename=str(LOG_FILE), encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Return a logger configured with H.I.R.E.'s standard console and
    file handlers.

    The root logger is configured on first use and reused for every
    subsequent call, so repeated imports across the application do not
    create duplicate handlers or duplicate log lines.

    Args:
        name: Name to scope the logger to, typically the calling
            module's `__name__` so log lines can be traced back to
            their source.

    Returns:
        A standard library `logging.Logger` instance.
    """
    _configure_root_logger()
    return logging.getLogger(name)