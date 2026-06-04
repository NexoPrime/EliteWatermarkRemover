"""Logging configuration for the application.

Sets up structured logging with console output and optional file output.
All modules should use `logging.getLogger(__name__)` to get their logger.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
) -> None:
    """Configure application-wide logging.

    Sets up a root logger with a console handler and optional file handler.
    Uses a consistent format across all handlers.

    Args:
        level: The minimum logging level (default: INFO).
        log_file: Optional path to a log file. If provided, a
            FileHandler is added alongside the console handler.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers to avoid duplicates on re-init
    root_logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Optional file handler
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("PyQt5").setLevel(logging.WARNING)
