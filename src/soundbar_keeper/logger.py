from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .resources import LOG_FILE_PATH, ensure_runtime_dirs

LOGGER_NAME = "soundbar_keeper"


def configure_logging(level: str = "INFO") -> logging.Logger:
    """Configure the shared application logger."""
    ensure_runtime_dirs()

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(_normalize_level(level))
    logger.propagate = False

    if logger.handlers:
        for handler in logger.handlers:
            handler.setLevel(_normalize_level(level))
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(threadName)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        LOG_FILE_PATH,
        maxBytes=1_048_576,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(_normalize_level(level))
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(_normalize_level(level))
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger


def _normalize_level(level: str) -> int:
    return getattr(logging, level.upper(), logging.INFO)
