"""
Rate limiting utilities for Amptimal FastAPI services.

Wraps slowapi to provide consistent rate limiting across all services,
with Redis-backed storage (production) and in-memory fallback (development).

Example:
    from amptimal_shared.rate_limit import setup_rate_limiting, rate_limit

    app = FastAPI()
    limiter = setup_rate_limiting(app, redis_url="redis://localhost:6379/0")

    @app.get("/api/v1/data")
    @rate_limit("10/minute")
    async def get_data():
        ...

Configuration via Pydantic model:
    from amptimal_shared.rate_limit import RateLimitConfig, setup_rate_limiting

    config = RateLimitConfig(
        default_limit="120/minute",
        redis_url="redis://localhost:6379/0",
    )
    limiter = setup_rate_limiting(app, config=config)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, TypeVar

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    _SLOWAPI_AVAILABLE = True
except ImportError:
    _SLOWAPI_AVAILABLE = False

F = TypeVar("F", bound=Callable[..., Any])

# Module-level limiter reference, set by setup_rate_limiting()
_limiter: Optional[Any] = None


class RateLimitConfig(BaseModel):
    """Configuration model for rate limiting.

    Attributes:
        default_limit: Default rate limit for unauthenticated requests (e.g., "60/minute").
        authenticated_limit: Rate limit for authenticated requests (e.g., "120/minute").
        admin_limit: Rate limit for admin users (e.g., "300/minute").
        redis_url: Redis URL for distributed rate limiting. None uses in-memory storage.
        enabled: Whether rate limiting is active. When False, all requests pass through.

    Example:
        config = RateLimitConfig(
            default_limit="100/minute",
            redis_url="redis://localhost:6379/0",
        )
    """

    default_limit: str = Field("60/minute", description="Default rate limit string")
    authenticated_limit: str = Field("120/minute", description="Rate limit for authenticated users")
    admin_limit: str = Field("300/minute", description="Rate limit for admin users")
    redis_url: Optional[str] = Field(None, description="Redis URL for distributed rate limiting")
    enabled: bool = Field(True, description="Whether rate limiting is enabled")


def _get_key_func() -> Callable:
    """Return a key function that extracts user ID from headers or falls back to IP.

    The key function checks for an X-User-ID header first. If not present,
    it falls back to the client's remote address (IP).

    Returns:
        A callable that takes a Request and returns a string key.
    """

    def key_func(request: Any) -> str:
        """Extract rate limit key from request.

        Priority:
            1. X-User-ID header (authenticated user)
            2. Remote IP address (anonymous user)
        """
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return str(user_id)

        if _SLOWAPI_AVAILABLE:
            return get_remote_address(request)

        # Fallback: try to get client host directly
        if hasattr(request, "client") and request.client:
            return request.client.host
        return "unknown"

    return key_func


def setup_rate_limiting(
    app: Any,
    redis_url: Optional[str] = None,
    default_limit: str = "60/minute",
    config: Optional[RateLimitConfig] = None,
) -> Any:
    """Configure rate limiting for a FastAPI application.

    Sets up slowapi with the given configuration, registers the exception handler,
    and stores the limiter on the app state for use by rate_limit decorators.

    If Redis is specified but unavailable, falls back to in-memory storage
    with a warning. If slowapi is not installed, logs an error and returns
    a no-op stub.

    Args:
        app: The FastAPI application to configure.
        redis_url: Redis URL for distributed rate limiting. Overridden by config.redis_url.
        default_limit: Default rate limit string (e.g., "60/minute"). Overridden by config.
        config: Optional RateLimitConfig for full configuration. Takes precedence over
            individual arguments.

    Returns:
        The configured Limiter instance, or None if slowapi is not available.

    Example:
        app = FastAPI()
        limiter = setup_rate_limiting(app, redis_url="redis://localhost:6379/0")

        # Or with config object:
        config = RateLimitConfig(default_limit="100/minute", enabled=True)
        limiter = setup_rate_limiting(app, config=config)
    """
    global _limiter

    if not _SLOWAPI_AVAILABLE:
        logger.error(
            "slowapi is not installed. Rate limiting is disabled. "
            "Install it with: pip install slowapi"
        )
        _limiter = None
        return None

    # Resolve configuration
    if config is not None:
        resolved_redis_url = config.redis_url
        resolved_default_limit = config.default_limit
        resolved_enabled = config.enabled
    else:
        resolved_redis_url = redis_url
        resolved_default_limit = default_limit
        resolved_enabled = True

    if not resolved_enabled:
        logger.info("Rate limiting is disabled by configuration")
        _limiter = None
        return None

    # Build storage URI
    storage_uri = None
    if resolved_redis_url:
        storage_uri = _try_redis_storage(resolved_redis_url)

    key_func = _get_key_func()

    limiter = Limiter(
        key_func=key_func,
        default_limits=[resolved_default_limit],
        storage_uri=storage_uri,
    )

    # Attach limiter to app state (slowapi convention)
    app.state.limiter = limiter

    # Register the rate limit exceeded exception handler
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    storage_type = "redis" if storage_uri else "in-memory"
    logger.info(
        "Rate limiting enabled: default=%s, storage=%s",
        resolved_default_limit,
        storage_type,
    )

    _limiter = limiter
    return limiter


def _try_redis_storage(redis_url: str) -> Optional[str]:
    """Attempt to use Redis for rate limit storage, falling back to in-memory.

    Tests the Redis connection. If it fails, logs a warning and returns None
    so that slowapi uses its default in-memory backend.

    Args:
        redis_url: Redis connection URL.

    Returns:
        The redis_url if connection succeeds, None otherwise.
    """
    try:
        import redis

        client = redis.from_url(redis_url, socket_connect_timeout=2)
        client.ping()
        client.close()
        logger.info("Rate limit storage: Redis at %s", redis_url)
        return redis_url
    except ImportError:
        logger.warning(
            "redis package not installed. Falling back to in-memory rate limiting. "
            "Install it with: pip install redis"
        )
        return None
    except Exception as e:
        logger.warning(
            "Redis unavailable at %s: %s. Falling back to in-memory rate limiting.",
            redis_url,
            e,
        )
        return None


def rate_limit(limit_string: str) -> Callable[[F], F]:
    """Decorator to apply a rate limit to a specific endpoint.

    Supports standard rate limit formats:
        - "10/second"
        - "60/minute"
        - "1000/hour"
        - "10000/day"

    If slowapi is not installed or rate limiting is disabled, the decorator
    is a no-op passthrough.

    Args:
        limit_string: Rate limit in "<count>/<period>" format.

    Returns:
        Decorated function with rate limiting applied.

    Example:
        @app.get("/api/v1/prices")
        @rate_limit("30/minute")
        async def get_prices(request: Request):
            ...

        @app.get("/api/v1/health")
        @rate_limit("10/second")
        async def health_check(request: Request):
            ...
    """

    def decorator(func: F) -> F:
        if not _SLOWAPI_AVAILABLE or _limiter is None:
            return func

        # Apply slowapi's limit decorator
        return _limiter.limit(limit_string)(func)  # type: ignore[return-value]

    return decorator


def get_limiter() -> Optional[Any]:
    """Return the current module-level Limiter instance.

    Useful for advanced usage where you need direct access to the limiter,
    such as applying dynamic limits or shared limits across endpoints.

    Returns:
        The Limiter instance if configured, None otherwise.
    """
    return _limiter
