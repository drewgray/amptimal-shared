"""Tests for retry utilities."""
import pytest

from amptimal_shared.retry import (
    async_retry_with_backoff,
    calculate_backoff,
    retry_with_backoff,
)


class TestCalculateBackoff:
    def test_exponential_growth(self):
        assert calculate_backoff(0) == 1
        assert calculate_backoff(1) == 2
        assert calculate_backoff(2) == 4
        assert calculate_backoff(3) == 8
        assert calculate_backoff(4) == 16

    def test_respects_ceiling(self):
        assert calculate_backoff(10, max_backoff_seconds=300) == 300
        assert calculate_backoff(20, max_backoff_seconds=60) == 60

    def test_custom_base(self):
        assert calculate_backoff(2, base=3) == 9
        assert calculate_backoff(3, base=3) == 27


class TestRetryWithBackoff:
    def test_succeeds_on_first_try(self):
        call_count = 0

        @retry_with_backoff(max_attempts=3)
        def succeed():
            nonlocal call_count
            call_count += 1
            return "success"

        result = succeed()
        assert result == "success"
        assert call_count == 1

    def test_retries_on_failure(self):
        call_count = 0

        @retry_with_backoff(max_attempts=3, max_backoff_seconds=1)
        def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary failure")
            return "success"

        result = fail_twice()
        assert result == "success"
        assert call_count == 3

    def test_raises_after_max_attempts(self):
        @retry_with_backoff(max_attempts=2, max_backoff_seconds=1)
        def always_fail():
            raise ValueError("permanent failure")

        with pytest.raises(ValueError, match="permanent failure"):
            always_fail()

    def test_only_retries_specified_exceptions(self):
        @retry_with_backoff(
            max_attempts=3,
            retryable_exceptions=(ValueError,),
        )
        def raise_type_error():
            raise TypeError("not retryable")

        with pytest.raises(TypeError):
            raise_type_error()

    def test_on_retry_callback(self):
        retries = []

        def track_retry(exc, attempt):
            retries.append((str(exc), attempt))

        @retry_with_backoff(
            max_attempts=3,
            max_backoff_seconds=1,
            on_retry=track_retry,
        )
        def fail_twice():
            if len(retries) < 2:
                raise ValueError("temp")
            return "ok"

        result = fail_twice()
        assert result == "ok"
        assert len(retries) == 2
        assert retries[0] == ("temp", 0)
        assert retries[1] == ("temp", 1)


class TestAsyncRetryWithBackoff:
    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self):
        call_count = 0

        async def succeed():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await async_retry_with_backoff(succeed, max_attempts=3)
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure(self):
        call_count = 0

        async def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary failure")
            return "success"

        result = await async_retry_with_backoff(
            fail_twice, max_attempts=3, max_backoff_seconds=1
        )
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_attempts(self):
        async def always_fail():
            raise ValueError("permanent failure")

        with pytest.raises(ValueError, match="permanent failure"):
            await async_retry_with_backoff(
                always_fail, max_attempts=2, max_backoff_seconds=1
            )

    @pytest.mark.asyncio
    async def test_only_retries_specified_exceptions(self):
        async def raise_type_error():
            raise TypeError("not retryable")

        with pytest.raises(TypeError):
            await async_retry_with_backoff(
                raise_type_error,
                max_attempts=3,
                retryable_exceptions=(ValueError,),
            )

    @pytest.mark.asyncio
    async def test_on_retry_callback(self):
        retries = []
        call_count = 0

        def track_retry(exc, attempt):
            retries.append((str(exc), attempt))

        async def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temp")
            return "ok"

        result = await async_retry_with_backoff(
            fail_twice,
            max_attempts=3,
            max_backoff_seconds=1,
            on_retry=track_retry,
        )
        assert result == "ok"
        assert len(retries) == 2
        assert retries[0] == ("temp", 0)
        assert retries[1] == ("temp", 1)
