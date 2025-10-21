"""Logging configuration for Claude Code Launcher."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from utils.constants import CONFIG_DIR, LOG_FILE


def setup_logging(level: int = logging.INFO) -> None:
    """
    Set up logging with rotating file handler.

    Args:
        level: Logging level (default: INFO)
    """
    # Ensure config directory exists
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler with rotation (3 files, 1MB each)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=1048576,  # 1MB
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # Console handler for warnings and errors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Prevent duplicate logs
    root_logger.propagate = False

    # Log startup
    logging.info("=" * 60)
    logging.info("Claude Code Launcher - Logging initialized")
    logging.info(f"Log file: {LOG_FILE}")
    logging.info("=" * 60)


def get_log_folder() -> Path:
    """
    Get the path to the log folder for "Open Log Folder" button.

    Returns:
        Path to the ~/.claude directory
    """
    return CONFIG_DIR


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)