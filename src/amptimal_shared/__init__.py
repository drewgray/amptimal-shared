"""Amptimal Shared Library - Common utilities for Amptimal services."""

from amptimal_shared.config import BaseServiceSettings
from amptimal_shared.health import HealthServer, create_health_app
from amptimal_shared.logging import get_logger, setup_logging
from amptimal_shared.retry import calculate_backoff, retry_with_backoff

__version__ = "0.1.0"

__all__ = [
    # Logging
    "setup_logging",
    "get_logger",
    # Health
    "HealthServer",
    "create_health_app",
    # Retry
    "retry_with_backoff",
    "calculate_backoff",
    # Config
    "BaseServiceSettings",
]
