# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2024-01-15

### Added

- **Logging module** (`amptimal_shared.logging`)
  - `setup_logging()` - Configure structured logging with text or JSON output
  - `get_logger()` - Get child loggers with consistent formatting
  - Environment variable support (`LOG_LEVEL`, `LOG_FORMAT`)

- **Health server module** (`amptimal_shared.health`)
  - `HealthServer` - Background HTTP server with `/health`, `/ready`, `/metrics` endpoints
  - `create_health_app()` - Standalone FastAPI app for integration with existing servers
  - Built-in Prometheus metrics (requests_total, errors_total, current_operation, last_success_timestamp)

- **Retry module** (`amptimal_shared.retry`)
  - `retry_with_backoff()` - Decorator for retry logic with exponential backoff
  - `async_retry_with_backoff()` - Async version for coroutines
  - `calculate_backoff()` - Manual backoff calculation utility

- **Configuration module** (`amptimal_shared.config`)
  - `BaseServiceSettings` - Pydantic-based settings with common service fields
  - Built-in fields: log_level, log_format, service_name, max_retry_attempts, max_backoff_seconds, health_port

- **CI/CD workflows**
  - Test workflow with pytest, ruff, mypy across Python 3.9-3.11
  - Publish workflow for GitHub releases

- **Documentation**
  - README with installation and usage examples
  - CONTRIBUTING guidelines
  - AGENTS.md for AI agent workflows
  - CLAUDE.md for AI quick reference

[Unreleased]: https://github.com/drewgray/amptimal-shared/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/drewgray/amptimal-shared/releases/tag/v0.1.0
