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

## Usage

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
```

### Health Server

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

# Endpoints available:
# GET /health - Liveness probe (always 200 if running)
# GET /ready  - Readiness probe (checks dependencies)
# GET /metrics - Prometheus metrics
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

# Manual backoff calculation
delay = calculate_backoff(attempt=3)  # Returns 8 seconds
```

### Configuration

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

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | INFO | Logging level |
| `LOG_FORMAT` | text | Logging format (text or json) |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/

# Linting
ruff check src/
```

## License

MIT
