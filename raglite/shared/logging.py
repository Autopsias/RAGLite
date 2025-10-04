"""Structured logging setup for RAGLite.

Provides configured loggers with JSON formatting for CloudWatch compatibility.
"""

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """Create a configured logger with structured JSON output.

    Args:
        name: Logger name (typically __name__ from calling module)

    Returns:
        Configured logging.Logger instance with JSON formatter

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Document ingested", extra={"doc_id": "123", "chunks": 42})
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger
