"""Amptimal Shared Library - Common utilities for Amptimal services."""

from amptimal_shared.config import BaseServiceSettings
from amptimal_shared.health import HealthServer, create_health_app
from amptimal_shared.logging import get_logger, setup_logging
from amptimal_shared.metrics import instrument_app
from amptimal_shared.redis_client import close_redis, get_async_redis, ping_redis
from amptimal_shared.retry import calculate_backoff, retry_with_backoff
from amptimal_shared.secrets import clear_cache as clear_secrets_cache
from amptimal_shared.secrets import get_secret

__version__ = "0.2.0"

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
    # Redis
    "get_async_redis",
    "ping_redis",
    "close_redis",
    # Metrics
    "instrument_app",
    # Secrets
    "get_secret",
    "clear_secrets_cache",
]
