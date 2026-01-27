"""
Base configuration utilities using Pydantic Settings.

Provides a base class for service configuration with common patterns.
"""
import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class BaseServiceSettings(BaseSettings):
    """Base settings class for Amptimal services.

    Provides common configuration patterns:
    - Environment variable loading
    - Log level configuration
    - Service identification

    Example:
        class MyServiceSettings(BaseServiceSettings):
            api_key: str = Field(..., description="API key for external service")
            poll_interval: int = Field(60, description="Poll interval in seconds")

        settings = MyServiceSettings()
    """

    # Logging
    log_level: str = Field("INFO", description="Log level (DEBUG, INFO, WARNING, ERROR)")
    log_format: str = Field("text", description="Log format: 'text' or 'json'")

    # Service identification
    service_name: str = Field("service", description="Service name for logging/metrics")

    # Retry defaults
    max_retry_attempts: int = Field(3, description="Default max retry attempts")
    max_backoff_seconds: int = Field(300, description="Default max backoff in seconds")

    # Health server
    health_port: int = Field(8080, description="Port for health check server")

    class Config:
        env_prefix = ""  # No prefix for env vars by default
        case_sensitive = False


def get_env_or_default(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable with optional default.

    Args:
        key: Environment variable name
        default: Default value if not set

    Returns:
        Value or default
    """
    return os.getenv(key, default)
