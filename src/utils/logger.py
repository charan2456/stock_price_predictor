"""Structured logging for Market Sentiment Intelligence Engine.

Uses loguru for structured, colorful, file-rotated logging with
context injection for pipeline stage tracking.
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from src.utils.config import LOGS_DIR


def setup_logger(
    level: str = "INFO",
    log_dir: Path | None = None,
    rotation: str = "10 MB",
    retention: str = "30 days",
) -> None:
    """Configure application-wide logging.

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_dir: Directory for log files. Defaults to project logs/ dir.
        rotation: When to rotate log files (size or time-based).
        retention: How long to keep old log files.
    """
    log_dir = log_dir or LOGS_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    # Remove default handler
    logger.remove()

    # Console handler — colorful and concise
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level:<8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # File handler — detailed with rotation
    logger.add(
        log_dir / "mse_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} | {message}",
        rotation=rotation,
        retention=retention,
        compression="gz",
        enqueue=True,  # Thread-safe
    )

    # Error-only file for quick debugging
    logger.add(
        log_dir / "errors.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} | {message}\n{exception}",
        rotation=rotation,
        retention=retention,
        backtrace=True,
        diagnose=True,
    )

    logger.info("Logger initialized | level={} | log_dir={}", level, log_dir)


def get_logger(name: str) -> logger:
    """Get a contextualized logger for a specific module.

    Args:
        name: Module name (typically __name__).

    Returns:
        Logger instance with module context bound.
    """
    return logger.bind(module=name)
