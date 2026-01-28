# amptimal-shared

Shared utilities for Amptimal services, providing common patterns for:
- Logging (text and JSON formats)
- Health check servers with Prometheus metrics
- Retry logic with exponential backoff
- Configuration management with Pydantic

## Installation

```bash
# From GitHub
pip install git+https://github.com/drewgray/amptimal-shared.git

# For development
pip install -e ".[dev]"
```

## Modules

### Logging

```python
from amptimal_shared import setup_logging, get_logger

# Set up main logger
logger = setup_logging("my-service")
logger.info("Service started")

# Get child loggers
child_logger = get_logger("my-service.worker")

# JSON format (for production, set LOG_FORMAT=json)
logger = setup_logging("my-service", json_format=True)

# Override log level
logger = setup_logging("my-service", level="DEBUG")
```

### Health Server

Background HTTP server exposing `/health`, `/ready`, and `/metrics` endpoints.

```python
from amptimal_shared import HealthServer

def get_status():
    return {"items_processed": 42, "last_run": "2024-01-15T10:00:00Z"}

def check_deps():
    # Return True if dependencies are healthy
    return check_database_connection()

server = HealthServer(
    service_name="my-service",
    get_status=get_status,
    check_dependencies=check_deps,
    port=8090,
)
server.start()

# Endpoints:
# GET /health  - Liveness probe (always 200 if running)
# GET /ready   - Readiness probe (checks dependencies, returns status)
# GET /metrics - Prometheus metrics

# Access built-in metrics
server.metrics["requests_total"].labels(status="success").inc()
server.metrics["errors_total"].labels(error_type="timeout").inc()
server.metrics["current_operation"].set(1)  # Processing
server.metrics["last_success_timestamp"].set_to_current_time()

# Graceful shutdown
server.stop()
```

**Standalone FastAPI app** (for integration with existing servers):

```python
from amptimal_shared import create_health_app

app = create_health_app(
    service_name="my-service",
    get_status=lambda: {"count": 10},
    check_dependencies=lambda: True,
)
# Mount or run with uvicorn
```

### Retry with Backoff

```python
from amptimal_shared import retry_with_backoff, calculate_backoff

# As a decorator
@retry_with_backoff(
    max_attempts=5,
    retryable_exceptions=(TimeoutError, ConnectionError),
)
def fetch_data():
    ...

# With callback on retry
@retry_with_backoff(
    max_attempts=3,
    on_retry=lambda e, attempt: logger.warning(f"Retry {attempt}: {e}")
)
def api_call():
    ...

# Manual backoff calculation (2^attempt, capped at max)
calculate_backoff(attempt=0)  # 1 second
calculate_backoff(attempt=1)  # 2 seconds
calculate_backoff(attempt=2)  # 4 seconds
calculate_backoff(attempt=3)  # 8 seconds
calculate_backoff(attempt=10, max_backoff_seconds=300)  # 300 seconds (capped)
```

**Async version:**

```python
from amptimal_shared.retry import async_retry_with_backoff

result = await async_retry_with_backoff(
    fetch_async_data,
    max_attempts=5,
    retryable_exceptions=(aiohttp.ClientError,),
)
```

### Configuration

Pydantic-based settings with environment variable loading.

```python
from pydantic import Field
from amptimal_shared import BaseServiceSettings

class MySettings(BaseServiceSettings):
    api_key: str = Field(..., description="Required API key")
    poll_interval: int = Field(60, description="Poll interval in seconds")

    class Config:
        env_prefix = "MYSERVICE_"  # Optional prefix

settings = MySettings()  # Loads from environment variables
```

**Built-in fields** (from `BaseServiceSettings`):

| Field | Default | Description |
|-------|---------|-------------|
| `log_level` | INFO | Log level |
| `log_format` | text | Log format (text/json) |
| `service_name` | service | Service name for logging/metrics |
| `max_retry_attempts` | 3 | Default retry attempts |
| `max_backoff_seconds` | 300 | Default max backoff |
| `health_port` | 8080 | Health server port |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | text | Logging format (text or json) |

## Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=amptimal_shared --cov-report=term-missing

# Run specific test file
pytest tests/test_health.py

# Type checking
mypy src/

# Linting
ruff check src/
```

## License

MIT
