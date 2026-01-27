"""Tests for configuration utilities."""
import os
from unittest.mock import patch

from pydantic import Field

from amptimal_shared.config import BaseServiceSettings, get_env_or_default


class TestBaseServiceSettings:
    def test_default_values(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = BaseServiceSettings()

            assert settings.log_level == "INFO"
            assert settings.log_format == "text"
            assert settings.service_name == "service"
            assert settings.max_retry_attempts == 3
            assert settings.max_backoff_seconds == 300
            assert settings.health_port == 8080

    def test_loads_from_env_vars(self):
        env = {
            "LOG_LEVEL": "DEBUG",
            "LOG_FORMAT": "json",
            "SERVICE_NAME": "my-service",
            "MAX_RETRY_ATTEMPTS": "5",
            "MAX_BACKOFF_SECONDS": "600",
            "HEALTH_PORT": "9000",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = BaseServiceSettings()

            assert settings.log_level == "DEBUG"
            assert settings.log_format == "json"
            assert settings.service_name == "my-service"
            assert settings.max_retry_attempts == 5
            assert settings.max_backoff_seconds == 600
            assert settings.health_port == 9000

    def test_case_insensitive_env_vars(self):
        env = {
            "log_level": "WARNING",
            "Log_Format": "json",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = BaseServiceSettings()

            assert settings.log_level == "WARNING"
            assert settings.log_format == "json"

    def test_subclass_with_custom_fields(self):
        class MyServiceSettings(BaseServiceSettings):
            api_key: str = Field(default="default-key")
            poll_interval: int = Field(default=60)

        env = {
            "API_KEY": "secret-key",
            "POLL_INTERVAL": "120",
            "LOG_LEVEL": "DEBUG",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = MyServiceSettings()

            assert settings.api_key == "secret-key"
            assert settings.poll_interval == 120
            assert settings.log_level == "DEBUG"

    def test_subclass_uses_defaults(self):
        class MyServiceSettings(BaseServiceSettings):
            custom_field: str = Field(default="default-value")

        with patch.dict(os.environ, {}, clear=True):
            settings = MyServiceSettings()

            assert settings.custom_field == "default-value"
            assert settings.log_level == "INFO"  # Inherited default

    def test_required_fields_in_subclass(self):
        class RequiredFieldSettings(BaseServiceSettings):
            required_api_key: str = Field(...)  # Required field

        with patch.dict(os.environ, {"REQUIRED_API_KEY": "my-key"}, clear=True):
            settings = RequiredFieldSettings()
            assert settings.required_api_key == "my-key"

    def test_type_conversion(self):
        env = {
            "MAX_RETRY_ATTEMPTS": "10",
            "HEALTH_PORT": "8080",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = BaseServiceSettings()

            assert settings.max_retry_attempts == 10
            assert isinstance(settings.max_retry_attempts, int)
            assert settings.health_port == 8080
            assert isinstance(settings.health_port, int)


class TestGetEnvOrDefault:
    def test_returns_env_var_when_set(self):
        with patch.dict(os.environ, {"MY_VAR": "my-value"}):
            result = get_env_or_default("MY_VAR")
            assert result == "my-value"

    def test_returns_default_when_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("UNSET_VAR", None)
            result = get_env_or_default("UNSET_VAR", "default-value")
            assert result == "default-value"

    def test_returns_none_when_not_set_and_no_default(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MISSING_VAR", None)
            result = get_env_or_default("MISSING_VAR")
            assert result is None

    def test_empty_string_is_returned(self):
        with patch.dict(os.environ, {"EMPTY_VAR": ""}):
            result = get_env_or_default("EMPTY_VAR", "default")
            assert result == ""

    def test_does_not_modify_env(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("NEW_VAR", None)
            get_env_or_default("NEW_VAR", "default")
            assert "NEW_VAR" not in os.environ
