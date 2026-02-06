"""
Prometheus instrumentation helper for FastAPI applications.

Provides a one-liner to add standard HTTP metrics to any FastAPI app
using prometheus_fastapi_instrumentator.

Example:
    from fastapi import FastAPI
    from amptimal_shared.metrics import instrument_app

    app = FastAPI()
    instrument_app(app)
"""

import logging
from typing import List, Optional

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

logger = logging.getLogger(__name__)


def instrument_app(
    app: FastAPI,
    metrics_path: str = "/metrics",
    excluded_handlers: Optional[List[str]] = None,
) -> Instrumentator:
    """Instrument a FastAPI application with Prometheus metrics.

    Adds standard HTTP request/response metrics (request count, latency,
    request size, response size) and exposes them at the given path.

    Args:
        app: The FastAPI application to instrument.
        metrics_path: URL path for the metrics endpoint (default: "/metrics").
        excluded_handlers: List of path patterns to exclude from instrumentation
            (default: ["/health", "/ready", "/metrics"]).

    Returns:
        The configured Instrumentator instance for further customization.

    Example:
        app = FastAPI()
        instrument_app(app)

        # Or with customization:
        instrumentator = instrument_app(app, metrics_path="/internal/metrics")
    """
    if excluded_handlers is None:
        excluded_handlers = ["/health", "/ready", "/metrics"]

    instrumentator = Instrumentator(
        excluded_handlers=excluded_handlers,
    )
    instrumentator.instrument(app).expose(app, endpoint=metrics_path)

    logger.info("Prometheus instrumentation enabled at %s", metrics_path)
    return instrumentator
