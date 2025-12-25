"""Logging configuration"""

import logging
import sys

from app.core.config import settings

# Create logger
logger = logging.getLogger("wumbo")


def setup_logging() -> None:
    """Configure application logging"""
    # Set log level
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    # Log initialization
    logger.info(f"Logging initialized at level {settings.LOG_LEVEL}")
