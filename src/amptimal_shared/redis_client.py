"""
Shared async Redis connection management.

Provides a lazy async connection factory with health checking and graceful shutdown.
All services should use get_async_redis() instead of creating their own connections.

Example:
    from amptimal_shared.redis_client import get_async_redis, close_redis

    async def my_handler():
        redis = await get_async_redis()
        await redis.set("key", "value")

    # On shutdown:
    await close_redis()
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_redis: Optional[aioredis.Redis] = None

DEFAULT_REDIS_URL = "redis://localhost:6379/0"


async def get_async_redis(
    url: Optional[str] = None,
    decode_responses: bool = True,
) -> aioredis.Redis:
    """Return (and lazily create) the shared async Redis connection.

    On first call, creates a connection using the provided URL or the
    REDIS_URL environment variable. Subsequent calls return the cached
    connection.

    Args:
        url: Redis URL. Defaults to REDIS_URL env var, then redis://localhost:6379/0.
        decode_responses: Whether to decode byte responses to strings (default: True).

    Returns:
        Async Redis client instance.
    """
    global _redis
    if _redis is None:
        resolved_url = url or os.getenv("REDIS_URL", DEFAULT_REDIS_URL)
        _redis = aioredis.from_url(resolved_url, decode_responses=decode_responses)
        logger.info("Async Redis connection created: %s", resolved_url)
    return _redis


async def ping_redis() -> bool:
    """Check if the Redis connection is alive.

    Returns:
        True if Redis responds to PING, False otherwise.
    """
    try:
        r = await get_async_redis()
        return await r.ping()
    except Exception as e:
        logger.warning("Redis ping failed: %s", e)
        return False


async def close_redis() -> None:
    """Gracefully close the Redis connection (call on shutdown)."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
        logger.info("Async Redis connection closed")
