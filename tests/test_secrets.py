"""Tests for AWS Secrets Manager with caching and env-var fallback."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from amptimal_shared.secrets import (
    _fetch_from_env,
    clear_cache,
    get_secret,
)


@pytest.fixture(autouse=True)
def reset_secrets_cache():
    """Clear the secrets cache between tests."""
    clear_cache()
    yield
    clear_cache()


class TestGetSecret:
    def test_fetches_from_aws_and_caches(self):
        secret_data = {"host": "smtp.gmail.com", "port": "587"}
        with patch("amptimal_shared.secrets._fetch_from_aws", return_value=secret_data) as mock_aws:
            result = get_secret("amptimal/smtp")
            assert result == secret_data
            mock_aws.assert_called_once_with("amptimal/smtp", "us-east-1")

            # Second call should use cache, not call AWS again
            result2 = get_secret("amptimal/smtp")
            assert result2 == secret_data
            mock_aws.assert_called_once()  # Still just one call

    def test_falls_back_to_env_when_aws_fails(self):
        env_data = {"user": "local-user", "password": "local-pass"}
        env = {"AMPTIMAL_SMTP": json.dumps(env_data)}

        with patch("amptimal_shared.secrets._fetch_from_aws", return_value=None):
            with patch.dict(os.environ, env, clear=True):
                result = get_secret("amptimal/smtp")
                assert result == env_data

    def test_returns_none_when_no_source_available(self):
        with patch("amptimal_shared.secrets._fetch_from_aws", return_value=None):
            with patch.dict(os.environ, {}, clear=True):
                result = get_secret("amptimal/nonexistent")
                assert result is None

    def test_caches_none_result(self):
        """Even None results should be cached to avoid repeated lookups."""
        with patch("amptimal_shared.secrets._fetch_from_aws", return_value=None) as mock_aws:
            with patch.dict(os.environ, {}, clear=True):
                result1 = get_secret("amptimal/missing")
                result2 = get_secret("amptimal/missing")

                assert result1 is None
                assert result2 is None
                mock_aws.assert_called_once()

    def test_custom_region(self):
        with patch("amptimal_shared.secrets._fetch_from_aws", return_value={"key": "val"}) as mock_aws:
            get_secret("amptimal/test", region="eu-west-1")
            mock_aws.assert_called_once_with("amptimal/test", "eu-west-1")

    def test_env_fallback_caches_result(self):
        env_data = {"token": "abc123"}
        env = {"AMPTIMAL_SLACK": json.dumps(env_data)}

        with patch("amptimal_shared.secrets._fetch_from_aws", return_value=None):
            with patch.dict(os.environ, env, clear=True):
                result1 = get_secret("amptimal/slack")
                assert result1 == env_data

                # Even with env changed, cache should persist
                with patch.dict(os.environ, {}, clear=True):
                    result2 = get_secret("amptimal/slack")
                    assert result2 == env_data


class TestClearCache:
    def test_clear_cache_enables_refetch(self):
        with patch("amptimal_shared.secrets._fetch_from_aws") as mock_aws:
            mock_aws.return_value = {"version": "1"}
            get_secret("amptimal/test")
            mock_aws.assert_called_once()

            mock_aws.return_value = {"version": "2"}
            clear_cache()
            result = get_secret("amptimal/test")

            assert result == {"version": "2"}
            assert mock_aws.call_count == 2


class TestFetchFromEnv:
    def test_parses_json_env_var(self):
        data = {"host": "localhost", "port": 5432}
        with patch.dict(os.environ, {"AMPTIMAL_DB": json.dumps(data)}):
            result = _fetch_from_env("amptimal/db")
            assert result == data

    def test_wraps_non_json_as_value(self):
        with patch.dict(os.environ, {"AMPTIMAL_TOKEN": "plain-text-token"}):
            result = _fetch_from_env("amptimal/token")
            assert result == {"value": "plain-text-token"}

    def test_returns_none_when_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            result = _fetch_from_env("amptimal/missing")
            assert result is None

    def test_secret_name_conversion(self):
        """Verify slash-to-underscore and uppercase conversion."""
        with patch.dict(os.environ, {"MY_APP_DB_CREDS": '{"user":"admin"}'}):
            result = _fetch_from_env("my/app/db/creds")
            assert result == {"user": "admin"}

    def test_empty_json_object(self):
        with patch.dict(os.environ, {"AMPTIMAL_EMPTY": "{}"}):
            result = _fetch_from_env("amptimal/empty")
            assert result == {}


class TestFetchFromAws:
    def test_handles_import_error(self):
        """When boto3 is not installed, returns None gracefully."""
        from amptimal_shared.secrets import _fetch_from_aws

        with patch.dict("sys.modules", {"boto3": None}):
            # This should handle ImportError gracefully
            with patch("amptimal_shared.secrets.json"):
                # Force ImportError by patching the import mechanism
                import builtins
                original_import = builtins.__import__

                def mock_import(name, *args, **kwargs):
                    if name == "boto3":
                        raise ImportError("No module named 'boto3'")
                    return original_import(name, *args, **kwargs)

                with patch("builtins.__import__", side_effect=mock_import):
                    result = _fetch_from_aws("amptimal/test", "us-east-1")
                    assert result is None

    def test_handles_client_error(self):
        """When AWS call fails, returns None gracefully."""
        from amptimal_shared.secrets import _fetch_from_aws

        mock_client = MagicMock()
        mock_client.get_secret_value.side_effect = Exception("Access denied")

        with patch("amptimal_shared.secrets.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_client
            result = _fetch_from_aws("amptimal/test", "us-east-1")
            assert result is None

    def test_successful_string_secret(self):
        """Fetches and parses a JSON string secret."""
        from amptimal_shared.secrets import _fetch_from_aws

        secret_data = {"host": "rds.example.com", "port": "5432"}
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            "SecretString": json.dumps(secret_data)
        }

        with patch("amptimal_shared.secrets.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_client
            result = _fetch_from_aws("amptimal/db", "us-east-1")
            assert result == secret_data

    def test_successful_binary_secret(self):
        """Fetches a binary secret and wraps it."""
        from amptimal_shared.secrets import _fetch_from_aws

        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {
            "SecretBinary": b"binary-secret-data"
        }

        with patch("amptimal_shared.secrets.boto3") as mock_boto3:
            mock_boto3.client.return_value = mock_client
            result = _fetch_from_aws("amptimal/cert", "us-east-1")
            assert result == {"value": "binary-secret-data"}
