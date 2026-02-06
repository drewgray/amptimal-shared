"""Tests for async Redis client module."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from amptimal_shared.redis_client import (
    DEFAULT_REDIS_URL,
    close_redis,
    get_async_redis,
    ping_redis,
)


@pytest.fixture(autouse=True)
def reset_redis_global():
    """Reset the module-level _redis singleton between tests."""
    import amptimal_shared.redis_client as mod

    mod._redis = None
    yield
    mod._redis = None


class TestGetAsyncRedis:
    @pytest.mark.asyncio
    async def test_creates_connection_with_default_url(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("amptimal_shared.redis_client.aioredis") as mock_aioredis:
                mock_client = MagicMock()
                mock_aioredis.from_url.return_value = mock_client

                result = await get_async_redis()

                mock_aioredis.from_url.assert_called_once_with(
                    DEFAULT_REDIS_URL, decode_responses=True
                )
                assert result is mock_client

    @pytest.mark.asyncio
    async def test_uses_redis_url_env_var(self):
        env = {"REDIS_URL": "redis://custom:6380/1"}
        with patch.dict(os.environ, env, clear=True):
            with patch("amptimal_shared.redis_client.aioredis") as mock_aioredis:
                mock_client = MagicMock()
                mock_aioredis.from_url.return_value = mock_client

                result = await get_async_redis()

                mock_aioredis.from_url.assert_called_once_with(
                    "redis://custom:6380/1", decode_responses=True
                )
                assert result is mock_client

    @pytest.mark.asyncio
    async def test_explicit_url_overrides_env(self):
        env = {"REDIS_URL": "redis://from-env:6379/0"}
        with patch.dict(os.environ, env, clear=True):
            with patch("amptimal_shared.redis_client.aioredis") as mock_aioredis:
                mock_client = MagicMock()
                mock_aioredis.from_url.return_value = mock_client

                result = await get_async_redis(url="redis://explicit:6379/2")

                mock_aioredis.from_url.assert_called_once_with(
                    "redis://explicit:6379/2", decode_responses=True
                )
                assert result is mock_client

    @pytest.mark.asyncio
    async def test_returns_cached_connection(self):
        with patch("amptimal_shared.redis_client.aioredis") as mock_aioredis:
            mock_client = MagicMock()
            mock_aioredis.from_url.return_value = mock_client

            first = await get_async_redis()
            second = await get_async_redis()

            assert first is second
            mock_aioredis.from_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_decode_responses_false(self):
        with patch("amptimal_shared.redis_client.aioredis") as mock_aioredis:
            mock_client = MagicMock()
            mock_aioredis.from_url.return_value = mock_client

            await get_async_redis(decode_responses=False)

            mock_aioredis.from_url.assert_called_once_with(
                DEFAULT_REDIS_URL, decode_responses=False
            )


class TestPingRedis:
    @pytest.mark.asyncio
    async def test_ping_success(self):
        with patch("amptimal_shared.redis_client.aioredis") as mock_aioredis:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_aioredis.from_url.return_value = mock_client

            result = await ping_redis()
            assert result is True

    @pytest.mark.asyncio
    async def test_ping_failure(self):
        with patch("amptimal_shared.redis_client.aioredis") as mock_aioredis:
            mock_client = AsyncMock()
            mock_client.ping.side_effect = ConnectionError("Connection refused")
            mock_aioredis.from_url.return_value = mock_client

            result = await ping_redis()
            assert result is False


class TestCloseRedis:
    @pytest.mark.asyncio
    async def test_close_active_connection(self):
        import amptimal_shared.redis_client as mod

        mock_client = AsyncMock()
        mod._redis = mock_client

        await close_redis()

        mock_client.aclose.assert_awaited_once()
        assert mod._redis is None

    @pytest.mark.asyncio
    async def test_close_when_no_connection(self):
        import amptimal_shared.redis_client as mod

        mod._redis = None

        # Should not raise
        await close_redis()
        assert mod._redis is None

    @pytest.mark.asyncio
    async def test_can_reconnect_after_close(self):
        with patch("amptimal_shared.redis_client.aioredis") as mock_aioredis:
            mock_client1 = AsyncMock()
            mock_client2 = MagicMock()
            mock_aioredis.from_url.side_effect = [mock_client1, mock_client2]

            first = await get_async_redis()
            assert first is mock_client1

            await close_redis()

            second = await get_async_redis()
            assert second is mock_client2
            assert mock_aioredis.from_url.call_count == 2
