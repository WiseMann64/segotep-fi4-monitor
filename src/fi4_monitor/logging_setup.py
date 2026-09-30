"""File logging suitable for a headless portable app."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import default_app_dir


def configure_logging(enabled: bool = True, log_dir: Path | None = None) -> logging.Logger:
    logger = logging.getLogger("fi4_monitor")
    debug_enabled = os.environ.get("FI4_LOG_LEVEL", "").strip().upper() == "DEBUG"
    logger.setLevel(logging.DEBUG if debug_enabled else logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    if not enabled:
        logger.addHandler(logging.NullHandler())
        return logger

    target_dir = log_dir or default_app_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        target_dir / "fi4monitor.log",
        maxBytes=1_048_576,
        backupCount=2,
        encoding="utf-8",
    )
    handler.setLevel(logging.DEBUG if debug_enabled else logging.INFO)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    return logger
