"""Tests for rate limiting utilities."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from amptimal_shared.rate_limit import RateLimitConfig, _get_key_func, get_limiter


@pytest.fixture(autouse=True)
def reset_limiter():
    """Reset the module-level _limiter singleton between tests."""
    import amptimal_shared.rate_limit as mod

    mod._limiter = None
    yield
    mod._limiter = None


class TestRateLimitConfig:
    def test_default_values(self):
        config = RateLimitConfig()
        assert config.default_limit == "60/minute"
        assert config.authenticated_limit == "120/minute"
        assert config.admin_limit == "300/minute"
        assert config.redis_url is None
        assert config.enabled is True

    def test_custom_values(self):
        config = RateLimitConfig(
            default_limit="100/minute",
            authenticated_limit="200/minute",
            admin_limit="500/minute",
            redis_url="redis://localhost:6379/1",
            enabled=False,
        )
        assert config.default_limit == "100/minute"
        assert config.authenticated_limit == "200/minute"
        assert config.admin_limit == "500/minute"
        assert config.redis_url == "redis://localhost:6379/1"
        assert config.enabled is False

    def test_limit_string_formats(self):
        """Verify different rate limit string formats are accepted."""
        for limit in ["10/second", "60/minute", "1000/hour", "10000/day"]:
            config = RateLimitConfig(default_limit=limit)
            assert config.default_limit == limit


class TestGetKeyFunc:
    def test_extracts_user_id_from_header(self):
        key_func = _get_key_func()
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "user-123"

        result = key_func(mock_request)

        assert result == "user-123"
        mock_request.headers.get.assert_called_once_with("X-User-ID")

    def test_falls_back_to_ip_when_no_user_id(self):
        key_func = _get_key_func()
        mock_request = MagicMock()
        mock_request.headers.get.return_value = None
        mock_request.client.host = "192.168.1.100"

        with patch("amptimal_shared.rate_limit._SLOWAPI_AVAILABLE", False):
            result = key_func(mock_request)

        assert result == "192.168.1.100"

    @patch("amptimal_shared.rate_limit._SLOWAPI_AVAILABLE", True)
    def test_uses_slowapi_get_remote_address_as_fallback(self):
        key_func = _get_key_func()
        mock_request = MagicMock()
        mock_request.headers.get.return_value = None

        with patch("amptimal_shared.rate_limit.get_remote_address", return_value="10.0.0.1"):
            result = key_func(mock_request)

        assert result == "10.0.0.1"

    def test_returns_unknown_when_no_client(self):
        key_func = _get_key_func()
        mock_request = MagicMock()
        mock_request.headers.get.return_value = None
        mock_request.client = None

        with patch("amptimal_shared.rate_limit._SLOWAPI_AVAILABLE", False):
            result = key_func(mock_request)

        assert result == "unknown"

    def test_user_id_takes_priority_over_ip(self):
        """When both X-User-ID header and IP are available, user ID wins."""
        key_func = _get_key_func()
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "user-456"
        mock_request.client.host = "192.168.1.1"

        result = key_func(mock_request)

        assert result == "user-456"


class TestSetupRateLimiting:
    @patch("amptimal_shared.rate_limit._SLOWAPI_AVAILABLE", True)
    def test_configures_app_with_defaults(self):
        from amptimal_shared.rate_limit import setup_rate_limiting

        mock_app = MagicMock()
        mock_limiter_instance = MagicMock()

        with patch("amptimal_shared.rate_limit.Limiter", return_value=mock_limiter_instance):
            with patch(
                "amptimal_shared.rate_limit.RateLimitExceeded"
            ) as mock_exc_class:
                result = setup_rate_limiting(mock_app)

        assert result is mock_limiter_instance
        assert mock_app.state.limiter is mock_limiter_instance
        mock_app.add_exception_handler.assert_called_once()

    @patch("amptimal_shared.rate_limit._SLOWAPI_AVAILABLE", True)
    def test_uses_config_object(self):
        from amptimal_shared.rate_limit import setup_rate_limiting

        mock_app = MagicMock()
        config = RateLimitConfig(
            default_limit="100/minute",
            redis_url=None,
            enabled=True,
        )

        with patch("amptimal_shared.rate_limit.Limiter") as MockLimiter:
            mock_limiter_instance = MagicMock()
            MockLimiter.return_value = mock_limiter_instance

            result = setup_rate_limiting(mock_app, config=config)

            MockLimiter.assert_called_once()
            call_kwargs = MockLimiter.call_args
            assert call_kwargs[1]["default_limits"] == ["100/minute"]
            assert result is mock_limiter_instance

    @patch("amptimal_shared.rate_limit._SLOWAPI_AVAILABLE", True)
    def test_config_overrides_individual_args(self):
        from amptimal_shared.rate_limit import setup_rate_limiting

        mock_app = MagicMock()
        config = RateLimitConfig(default_limit="200/minute")

        with patch("amptimal_shared.rate_limit.Limiter") as MockLimiter:
            MockLimiter.return_value = MagicMock()

            # Pass both individual args and config; config should win
            setup_rate_limiting(
                mock_app,
                redis_url="redis://should-be-ignored:6379/0",
                default_limit="50/minute",
                config=config,
            )

            call_kwargs = MockLimiter.call_args
            assert call_kwargs[1]["default_limits"] == ["200/minute"]

    @patch("amptimal_shared.rate_limit._SLOWAPI_AVAILABLE", True)
    def test_disabled_config_returns_none(self):
        from amptimal_shared.rate_limit import setup_rate_limiting

        mock_app = MagicMock()
        config = RateLimitConfig(enabled=False)

        result = setup_rate_limiting(mock_app, config=config)

        assert result is None
        # App should NOT have exception handler registered
        mock_app.add_exception_handler.assert_not_called()

    @patch("amptimal_shared.rate_limit._SLOWAPI_AVAILABLE", False)
    def test_returns_none_when_slowapi_not_installed(self):
        from amptimal_shared.rate_limit import setup_rate_limiting

        mock_app = MagicMock()

        result = setup_rate_limiting(mock_app)

        assert result is None
        mock_app.add_exception_handler.assert_not_called()

    @patch("amptimal_shared.rate_limit._SLOWAPI_AVAILABLE", True)
    def test_redis_storage_on_success(self):
        from amptimal_shared.rate_limit import setup_rate_limiting

        mock_app = MagicMock()

        with patch("amptimal_shared.rate_limit._try_redis_storage") as mock_try_redis:
            mock_try_redis.return_value = "redis://localhost:6379/0"

            with patch("amptimal_shared.rate_limit.Limiter") as MockLimiter:
                MockLimiter.return_value = MagicMock()

                setup_rate_limiting(mock_app, redis_url="redis://localhost:6379/0")

                call_kwargs = MockLimiter.call_args
                assert call_kwargs[1]["storage_uri"] == "redis://localhost:6379/0"

    @patch("amptimal_shared.rate_limit._SLOWAPI_AVAILABLE", True)
    def test_in_memory_fallback_when_no_redis_url(self):
        from amptimal_shared.rate_limit import setup_rate_limiting

        mock_app = MagicMock()

        with patch("amptimal_shared.rate_limit.Limiter") as MockLimiter:
            MockLimiter.return_value = MagicMock()

            setup_rate_limiting(mock_app)  # No redis_url

            call_kwargs = MockLimiter.call_args
            assert call_kwargs[1]["storage_uri"] is None

    @patch("amptimal_shared.rate_limit._SLOWAPI_AVAILABLE", True)
    def test_sets_module_level_limiter(self):
        from amptimal_shared.rate_limit import setup_rate_limiting

        mock_app = MagicMock()
        mock_limiter_instance = MagicMock()

        with patch("amptimal_shared.rate_limit.Limiter", return_value=mock_limiter_instance):
            setup_rate_limiting(mock_app)

        assert get_limiter() is mock_limiter_instance


class TestTryRedisStorage:
    def test_returns_url_on_successful_ping(self):
        from amptimal_shared.rate_limit import _try_redis_storage

        mock_client = MagicMock()
        mock_client.ping.return_value = True

        mock_redis_mod = MagicMock()
        mock_redis_mod.from_url.return_value = mock_client

        with patch.dict(sys.modules, {"redis": mock_redis_mod}):
            result = _try_redis_storage("redis://localhost:6379/0")

            assert result == "redis://localhost:6379/0"
            mock_redis_mod.from_url.assert_called_once_with(
                "redis://localhost:6379/0", socket_connect_timeout=2
            )
            mock_client.ping.assert_called_once()
            mock_client.close.assert_called_once()

    def test_returns_none_on_connection_failure(self):
        from amptimal_shared.rate_limit import _try_redis_storage

        mock_client = MagicMock()
        mock_client.ping.side_effect = ConnectionError("Connection refused")

        mock_redis_mod = MagicMock()
        mock_redis_mod.from_url.return_value = mock_client

        with patch.dict(sys.modules, {"redis": mock_redis_mod}):
            result = _try_redis_storage("redis://bad-host:6379/0")

            assert result is None

    def test_returns_none_when_redis_not_installed(self):
        from amptimal_shared.rate_limit import _try_redis_storage

        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "redis":
                raise ImportError("No module named 'redis'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = _try_redis_storage("redis://localhost:6379/0")

        assert result is None

    def test_returns_none_on_timeout(self):
        from amptimal_shared.rate_limit import _try_redis_storage

        mock_redis_mod = MagicMock()
        mock_redis_mod.from_url.side_effect = Exception("Connection timed out")

        with patch.dict(sys.modules, {"redis": mock_redis_mod}):
            result = _try_redis_storage("redis://slow-host:6379/0")

            assert result is None


class TestRateLimit:
    @patch("amptimal_shared.rate_limit._SLOWAPI_AVAILABLE", True)
    def test_applies_limit_when_limiter_configured(self):
        import amptimal_shared.rate_limit as mod
        from amptimal_shared.rate_limit import rate_limit

        mock_limiter = MagicMock()
        mock_decorated = MagicMock()
        mock_limiter.limit.return_value = lambda f: mock_decorated
        mod._limiter = mock_limiter

        @rate_limit("10/minute")
        async def my_endpoint():
            pass

        mock_limiter.limit.assert_called_once_with("10/minute")

    @patch("amptimal_shared.rate_limit._SLOWAPI_AVAILABLE", True)
    def test_passthrough_when_limiter_is_none(self):
        import amptimal_shared.rate_limit as mod
        from amptimal_shared.rate_limit import rate_limit

        mod._limiter = None

        async def my_endpoint():
            return "ok"

        decorated = rate_limit("10/minute")(my_endpoint)

        # Should be the original function, not wrapped
        assert decorated is my_endpoint

    @patch("amptimal_shared.rate_limit._SLOWAPI_AVAILABLE", False)
    def test_passthrough_when_slowapi_not_available(self):
        from amptimal_shared.rate_limit import rate_limit

        async def my_endpoint():
            return "ok"

        decorated = rate_limit("10/minute")(my_endpoint)

        assert decorated is my_endpoint

    @patch("amptimal_shared.rate_limit._SLOWAPI_AVAILABLE", True)
    def test_different_limit_formats(self):
        """Verify decorator accepts various rate limit string formats."""
        import amptimal_shared.rate_limit as mod
        from amptimal_shared.rate_limit import rate_limit

        mock_limiter = MagicMock()
        mock_limiter.limit.return_value = lambda f: f
        mod._limiter = mock_limiter

        for limit_str in ["10/second", "60/minute", "1000/hour", "10000/day"]:
            mock_limiter.limit.reset_mock()

            @rate_limit(limit_str)
            async def endpoint():
                pass

            mock_limiter.limit.assert_called_once_with(limit_str)


class TestGetLimiter:
    def test_returns_none_when_not_configured(self):
        assert get_limiter() is None

    def test_returns_limiter_when_configured(self):
        import amptimal_shared.rate_limit as mod

        mock_limiter = MagicMock()
        mod._limiter = mock_limiter

        assert get_limiter() is mock_limiter


class TestDisabledRateLimiting:
    """Test that disabled rate limiting passes through all requests."""

    @patch("amptimal_shared.rate_limit._SLOWAPI_AVAILABLE", True)
    def test_disabled_via_config_does_not_set_limiter(self):
        from amptimal_shared.rate_limit import setup_rate_limiting

        mock_app = MagicMock()
        config = RateLimitConfig(enabled=False)

        setup_rate_limiting(mock_app, config=config)

        assert get_limiter() is None

    @patch("amptimal_shared.rate_limit._SLOWAPI_AVAILABLE", True)
    def test_disabled_rate_limit_decorator_is_passthrough(self):
        import amptimal_shared.rate_limit as mod
        from amptimal_shared.rate_limit import rate_limit

        mod._limiter = None  # Simulates disabled state

        async def my_endpoint():
            return "data"

        decorated = rate_limit("1/second")(my_endpoint)

        assert decorated is my_endpoint


class TestGracefulDegradation:
    """Test graceful degradation when Redis is unavailable."""

    @patch("amptimal_shared.rate_limit._SLOWAPI_AVAILABLE", True)
    def test_falls_back_to_in_memory_on_redis_failure(self):
        from amptimal_shared.rate_limit import setup_rate_limiting

        mock_app = MagicMock()

        with patch("amptimal_shared.rate_limit._try_redis_storage", return_value=None):
            with patch("amptimal_shared.rate_limit.Limiter") as MockLimiter:
                MockLimiter.return_value = MagicMock()

                result = setup_rate_limiting(
                    mock_app, redis_url="redis://unreachable:6379/0"
                )

                # Limiter should still be created (in-memory)
                assert result is not None
                call_kwargs = MockLimiter.call_args
                assert call_kwargs[1]["storage_uri"] is None

    @patch("amptimal_shared.rate_limit._SLOWAPI_AVAILABLE", True)
    def test_redis_connection_error_does_not_raise(self):
        """Redis failure during setup should not crash the application."""
        from amptimal_shared.rate_limit import setup_rate_limiting

        mock_app = MagicMock()

        with patch("amptimal_shared.rate_limit._try_redis_storage") as mock_try:
            mock_try.return_value = None  # Simulates failed connection

            with patch("amptimal_shared.rate_limit.Limiter") as MockLimiter:
                MockLimiter.return_value = MagicMock()

                # Should not raise
                result = setup_rate_limiting(
                    mock_app, redis_url="redis://bad-host:6379/0"
                )

                assert result is not None
