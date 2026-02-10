"""Amptimal Shared Library - Common utilities for Amptimal services."""

from amptimal_shared.auth import (
    RequestUser,
    get_current_user,
    require_permission,
    require_role,
)
from amptimal_shared.config import BaseServiceSettings
from amptimal_shared.health import HealthServer, create_health_app
from amptimal_shared.logging import get_logger, setup_logging
from amptimal_shared.metrics import instrument_app
from amptimal_shared.rate_limit import RateLimitConfig, rate_limit, setup_rate_limiting
from amptimal_shared.redis_client import close_redis, get_async_redis, ping_redis
from amptimal_shared.retry import calculate_backoff, retry_with_backoff
from amptimal_shared.secrets import clear_cache as clear_secrets_cache
from amptimal_shared.secrets import get_secret

__version__ = "0.4.0"


def get_service_version(package_name: str) -> str:
    """Get installed package version from metadata."""
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _version

    try:
        return _version(package_name)
    except PackageNotFoundError:
        return "0.0.0-dev"


__all__ = [
    # Auth
    "get_current_user",
    "require_role",
    "require_permission",
    "RequestUser",
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
    # Rate Limiting
    "setup_rate_limiting",
    "rate_limit",
    "RateLimitConfig",
    # Secrets
    "get_secret",
    "clear_secrets_cache",
    # Version
    "get_service_version",
]
