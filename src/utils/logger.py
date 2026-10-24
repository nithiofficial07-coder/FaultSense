"""Centralized logging infrastructure for FaultSense.

Provides consistent, structured console and rotating file logging across
all ingestion, diagnosis, storage, and UI modules.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from config.settings import get_settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_INITIALIZED = False


def setup_logging(
    log_file: Optional[Path] = None,
    log_level: Optional[str] = None,
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 3,
) -> None:
    """Configures root logger with both console and rotating file output."""
    global _INITIALIZED
    if _INITIALIZED:
        return

    settings = get_settings()
    level_str = (log_level or settings.log_level).upper()
    level = getattr(logging, level_str, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers to avoid duplicates
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # 1. Console Stream Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 2. Rotating File Handler
    target_log_file = log_file or settings.log_file
    target_log_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        file_handler = RotatingFileHandler(
            filename=str(target_log_file),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as exc:
        logging.warning("Could not initialize file logger: %s", exc)

    _INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    """Returns a named logger instance with centralized formatting."""
    if not _INITIALIZED:
        setup_logging()
    return logging.getLogger(name)
