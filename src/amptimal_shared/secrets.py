"""
AWS Secrets Manager with caching and environment variable fallback.

Fetches secrets from AWS Secrets Manager on first access and caches them
in memory. When AWS is not available (local development), falls back to
environment variables.

Example:
    from amptimal_shared.secrets import get_secret

    # Fetches from AWS Secrets Manager (or env var fallback)
    smtp_config = get_secret("amptimal/smtp")
    # {"host": "smtp.gmail.com", "port": "587", ...}

    # Cached on subsequent calls
    smtp_config = get_secret("amptimal/smtp")  # No AWS call
"""

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_cache: Dict[str, Optional[Dict[str, Any]]] = {}


def get_secret(
    secret_name: str,
    region: str = "us-east-1",
) -> Optional[Dict[str, Any]]:
    """Fetch a secret from AWS Secrets Manager with caching and env-var fallback.

    On first call for a given secret_name, attempts to fetch from AWS Secrets
    Manager. The result is cached in memory for subsequent calls. If AWS is
    unreachable (e.g., local development without credentials), falls back to
    an environment variable named after the secret (slashes replaced with
    underscores, uppercased).

    Args:
        secret_name: The secret identifier in AWS Secrets Manager
            (e.g., "amptimal/smtp").
        region: AWS region (default: "us-east-1").

    Returns:
        Secret data as a dictionary, or None if not found.

    Example:
        # Tries AWS first, falls back to env var AMPTIMAL_SMTP
        config = get_secret("amptimal/smtp")
    """
    if secret_name in _cache:
        return _cache[secret_name]

    # Try AWS Secrets Manager
    secret = _fetch_from_aws(secret_name, region)
    if secret is not None:
        _cache[secret_name] = secret
        return secret

    # Fall back to environment variable
    secret = _fetch_from_env(secret_name)
    _cache[secret_name] = secret
    return secret


def clear_cache() -> None:
    """Clear the secrets cache. Useful for testing or forced refresh."""
    _cache.clear()
    logger.info("Secrets cache cleared")


def _fetch_from_aws(secret_name: str, region: str) -> Optional[Dict[str, Any]]:
    """Attempt to fetch a secret from AWS Secrets Manager.

    Args:
        secret_name: AWS secret identifier.
        region: AWS region.

    Returns:
        Secret data as a dictionary, or None on failure.
    """
    try:
        import boto3
        from botocore.exceptions import ClientError

        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=secret_name)

        if "SecretString" in response:
            secret = json.loads(response["SecretString"])
            logger.debug("Fetched secret from AWS: %s", secret_name)
            return secret
        else:
            # Binary secret
            return {"value": response["SecretBinary"].decode("utf-8")}

    except ImportError:
        logger.debug("boto3 not installed, skipping AWS Secrets Manager")
        return None
    except Exception as e:
        logger.debug("AWS Secrets Manager unavailable for %s: %s", secret_name, e)
        return None


def _fetch_from_env(secret_name: str) -> Optional[Dict[str, Any]]:
    """Fall back to environment variable for local development.

    Converts the secret name to an env var name by replacing slashes with
    underscores and uppercasing (e.g., "amptimal/smtp" -> "AMPTIMAL_SMTP").

    The env var value is expected to be a JSON string. If it is not valid
    JSON, it is returned as {"value": <raw_string>}.

    Args:
        secret_name: The secret name to convert to an env var lookup.

    Returns:
        Parsed secret data, or None if the env var is not set.
    """
    env_key = secret_name.replace("/", "_").upper()
    raw = os.getenv(env_key)
    if raw is None:
        logger.debug("No env var fallback found for secret %s (tried %s)", secret_name, env_key)
        return None

    try:
        secret = json.loads(raw)
        logger.debug("Loaded secret from env var %s", env_key)
        return secret
    except (json.JSONDecodeError, TypeError):
        logger.debug("Env var %s is not JSON, wrapping as {value: ...}", env_key)
        return {"value": raw}
