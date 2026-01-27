# CLAUDE.md - AI Agent Quick Reference

## Overview

**amptimal-shared** is a shared Python library providing cross-cutting utilities for Amptimal services.

**Owner:** Amptimal Engineering
**License:** MIT
**Python:** 3.9+

## Quick Commands

```bash
# Install for development
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=amptimal_shared --cov-report=term-missing

# Linting
ruff check src/ tests/

# Type checking
mypy src/amptimal_shared --ignore-missing-imports

# All checks (CI equivalent)
ruff check src/ tests/ && mypy src/amptimal_shared --ignore-missing-imports && pytest --cov=amptimal_shared
```

## Architecture

### Modules

| Module | Purpose | Key Exports |
|--------|---------|-------------|
| `logging` | Structured logging (text/JSON) | `setup_logging`, `get_logger` |
| `health` | HTTP health/metrics server | `HealthServer`, `create_health_app` |
| `retry` | Exponential backoff retry | `retry_with_backoff`, `calculate_backoff` |
| `config` | Pydantic settings base | `BaseServiceSettings` |

### File Locations

| Path | Purpose |
|------|---------|
| `src/amptimal_shared/` | Source modules |
| `src/amptimal_shared/__init__.py` | Package exports, version |
| `tests/` | Test files (`test_<module>.py`) |
| `pyproject.toml` | Dependencies, tool config |
| `.github/workflows/test.yml` | CI test workflow |
| `.github/workflows/publish.yml` | Release workflow |

## Key Patterns

### Logging

```python
from amptimal_shared import setup_logging, get_logger

logger = setup_logging("my-service")  # Main logger
child = get_logger("my-service.worker")  # Child logger

# JSON format for production
logger = setup_logging("my-service", json_format=True)
```

### Health Server

```python
from amptimal_shared import HealthServer

server = HealthServer(
    service_name="my-service",
    get_status=lambda: {"count": 42},
    check_dependencies=lambda: True,
    port=8090,
)
server.start()  # Starts background thread
# Endpoints: /health, /ready, /metrics
server.stop()  # Graceful shutdown
```

### Retry with Backoff

```python
from amptimal_shared import retry_with_backoff

@retry_with_backoff(max_attempts=5, retryable_exceptions=(TimeoutError,))
def fetch_data():
    ...
```

### Configuration

```python
from amptimal_shared import BaseServiceSettings

class MySettings(BaseServiceSettings):
    api_key: str
    poll_interval: int = 60

settings = MySettings()  # Loads from env vars
```

## Dependencies

**Runtime:**
- fastapi >= 0.100.0
- uvicorn >= 0.23.0
- prometheus-client >= 0.17.0
- pydantic >= 2.0.0
- pydantic-settings >= 2.0.0

**Dev:**
- pytest, pytest-asyncio, pytest-cov
- httpx (test client)
- mypy, ruff

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | INFO | Logging level |
| `LOG_FORMAT` | text | Output format (text/json) |

## Consumer Repos

| Repo | Usage |
|------|-------|
| [amptimal-data](https://github.com/drewgray/amptimal-data) | 7+ microservices use logging, health, retry, config |
| [claude-pr-reviewer](https://github.com/drewgray/claude-pr-reviewer) | 2 services use logging, health, config |

## Gotchas

- **Health server runs in background thread** - Call `server.stop()` for graceful shutdown
- **Retry decorator vs function** - Use `@retry_with_backoff()` as decorator, `async_retry_with_backoff(fn, ...)` as function
- **BaseServiceSettings loads from env** - Set `env_prefix` in Config class to namespace variables
- **Version in two places** - Update both `__init__.py` and `pyproject.toml` when bumping

## Related Files

- `AGENTS.md` - Detailed agent workflows
- `CONTRIBUTING.md` - Contribution guidelines
- `CHANGELOG.md` - Version history
- `README.md` - Full documentation with examples
