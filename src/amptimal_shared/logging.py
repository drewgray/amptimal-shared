"""
Shared logging configuration for all Amptimal services.

Supports both human-readable (development) and JSON (production) formats.
"""
import json
import logging
import os
import sys
from typing import Any, Dict, Optional


class JsonFormatter(logging.Formatter):
    """JSON log formatter for production/log aggregation."""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "service": self.service_name,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        # Include extra fields if present
        if hasattr(record, "extra") and record.extra:
            log_data.update(record.extra)
        return json.dumps(log_data)


def setup_logging(
    service_name: str,
    level: Optional[str] = None,
    json_format: Optional[bool] = None,
) -> logging.Logger:
    """
    Configure logging for a service.

    Args:
        service_name: Name of the service (used as logger name and in JSON output)
        level: Log level (default from LOG_LEVEL env var or INFO)
        json_format: Whether to use JSON format (default from LOG_FORMAT env var)

    Returns:
        Configured logger instance

    Example:
        logger = setup_logging("pr-reviewer")
        logger.info("Service started")
    """
    level = level or os.getenv("LOG_LEVEL", "INFO")
    if json_format is None:
        json_format = os.getenv("LOG_FORMAT", "text") == "json"

    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers = []

    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    if json_format:
        handler.setFormatter(JsonFormatter(service_name))
    else:
        # Human-readable format for development
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger.

    Args:
        name: Logger name (can be dotted for hierarchy)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
