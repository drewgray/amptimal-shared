"""
Retry utilities with exponential backoff.

Provides both a decorator and utility functions for implementing
retry logic with configurable backoff strategies.
"""
import functools
import logging
import time
from typing import Any, Callable, Optional, Tuple, Type

logger = logging.getLogger(__name__)


def calculate_backoff(
    attempt: int,
    max_backoff_seconds: int = 300,
    base: int = 2,
) -> int:
    """Calculate exponential backoff delay.

    Formula: min(base^attempt, max_backoff_seconds)

    Args:
        attempt: Current attempt number (0-indexed)
        max_backoff_seconds: Maximum backoff ceiling (default: 300s = 5 minutes)
        base: Exponential base (default: 2)

    Returns:
        Backoff delay in seconds

    Example:
        attempt 0: 1s
        attempt 1: 2s
        attempt 2: 4s
        attempt 3: 8s
        ...
        attempt 8+: 300s (capped)
    """
    return int(min(base**attempt, max_backoff_seconds))


def retry_with_backoff(
    max_attempts: int = 3,
    max_backoff_seconds: int = 300,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable:
    """Decorator for retry with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        max_backoff_seconds: Maximum backoff ceiling (default: 300s)
        retryable_exceptions: Tuple of exception types to retry on
        on_retry: Optional callback(exception, attempt) called before each retry

    Returns:
        Decorated function

    Example:
        @retry_with_backoff(max_attempts=5, retryable_exceptions=(TimeoutError, IOError))
        def fetch_data():
            ...

        @retry_with_backoff(
            max_attempts=3,
            on_retry=lambda e, a: logger.warning(f"Retry {a}: {e}")
        )
        def api_call():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Optional[Exception] = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        delay = calculate_backoff(attempt, max_backoff_seconds)
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_attempts}): {e}. "
                            f"Retrying in {delay}s..."
                        )

                        if on_retry:
                            on_retry(e, attempt)

                        time.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )

            # Raise the last exception if all retries failed
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


async def async_retry_with_backoff(
    func: Callable,
    max_attempts: int = 3,
    max_backoff_seconds: int = 300,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Any:
    """Async version of retry with exponential backoff.

    Args:
        func: Async function to call
        max_attempts: Maximum number of attempts
        max_backoff_seconds: Maximum backoff ceiling
        retryable_exceptions: Tuple of exception types to retry on
        on_retry: Optional callback(exception, attempt) called before each retry

    Returns:
        Result of the function call

    Example:
        result = await async_retry_with_backoff(
            fetch_async_data,
            max_attempts=5,
            retryable_exceptions=(aiohttp.ClientError,),
        )
    """
    import asyncio

    last_exception: Optional[Exception] = None

    for attempt in range(max_attempts):
        try:
            return await func()
        except retryable_exceptions as e:
            last_exception = e

            if attempt < max_attempts - 1:
                delay = calculate_backoff(attempt, max_backoff_seconds)
                logger.warning(
                    f"Async call failed (attempt {attempt + 1}/{max_attempts}): {e}. "
                    f"Retrying in {delay}s..."
                )

                if on_retry:
                    on_retry(e, attempt)

                await asyncio.sleep(delay)
            else:
                logger.error(f"Async call failed after {max_attempts} attempts: {e}")

    if last_exception:
        raise last_exception
