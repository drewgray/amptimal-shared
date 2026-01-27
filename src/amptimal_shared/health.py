"""
Health check HTTP server for background services.

Runs FastAPI in a background thread to expose /health, /ready, and /metrics
endpoints while the main thread does other work.
"""
import logging
import threading
from typing import Any, Callable, Dict, Optional

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)


def create_metrics(service_name: str) -> Dict[str, Any]:
    """Create Prometheus metrics for a service.

    Args:
        service_name: Name used in metric labels

    Returns:
        Dictionary of metric objects
    """
    prefix = service_name.replace("-", "_")
    return {
        "requests_total": Counter(
            f"{prefix}_requests_total",
            f"Total requests processed by {service_name}",
            ["status"],
        ),
        "errors_total": Counter(
            f"{prefix}_errors_total",
            f"Total errors in {service_name}",
            ["error_type"],
        ),
        "current_operation": Gauge(
            f"{prefix}_current_operation",
            f"Whether {service_name} is currently processing (1=yes, 0=no)",
        ),
        "last_success_timestamp": Gauge(
            f"{prefix}_last_success_timestamp",
            f"Unix timestamp of last successful operation in {service_name}",
        ),
    }


def create_health_app(
    service_name: str,
    get_status: Callable[[], Dict[str, Any]],
    check_dependencies: Optional[Callable[[], bool]] = None,
    metrics: Optional[Dict[str, Any]] = None,
) -> FastAPI:
    """Create a FastAPI app with health check endpoints.

    Args:
        service_name: Name of the service for health responses
        get_status: Callback to get current service status (must return dict)
        check_dependencies: Optional callback to verify dependencies (returns True if healthy)
        metrics: Optional dict of Prometheus metrics to include in /metrics

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(title=f"{service_name} Health", docs_url=None, redoc_url=None)

    @app.get("/health")
    async def health() -> Dict[str, str]:
        """Basic liveness probe - returns healthy if service is running."""
        return {"status": "healthy", "service": service_name}

    @app.get("/ready")
    async def ready() -> Any:
        """Readiness probe - verifies dependencies are connected."""
        try:
            deps_ok = True
            if check_dependencies:
                deps_ok = check_dependencies()

            if deps_ok:
                status = get_status()
                return {
                    "status": "ready",
                    "service": service_name,
                    **status,
                }
            else:
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "not_ready",
                        "service": service_name,
                        "reason": "dependencies_unavailable",
                    },
                )
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "service": service_name,
                    "error": str(e),
                },
            )

    @app.get("/metrics")
    async def metrics_endpoint() -> Response:
        """Prometheus metrics endpoint."""
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


class HealthServer:
    """Background HTTP server for health checks.

    Runs in a daemon thread so it doesn't block shutdown.

    Example:
        server = HealthServer(
            service_name="pr-reviewer",
            get_status=lambda: {"prs_reviewed": 42},
            port=8090,
        )
        server.start()
        # ... do main work ...
        server.stop()
    """

    def __init__(
        self,
        service_name: str,
        get_status: Callable[[], Dict[str, Any]],
        check_dependencies: Optional[Callable[[], bool]] = None,
        host: str = "0.0.0.0",
        port: int = 8080,
    ):
        """Initialize health server.

        Args:
            service_name: Name of the service
            get_status: Callback to get current service status
            check_dependencies: Optional callback to check dependencies
            host: Host to bind to (default: 0.0.0.0)
            port: Port to listen on (default: 8080)
        """
        self.service_name = service_name
        self.host = host
        self.port = port
        self.metrics = create_metrics(service_name)
        self.app = create_health_app(
            service_name, get_status, check_dependencies, self.metrics
        )
        self._thread: Optional[threading.Thread] = None
        self._server: Optional[uvicorn.Server] = None

    def start(self) -> None:
        """Start the health server in a background thread."""
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="warning",
            access_log=False,
        )
        self._server = uvicorn.Server(config)

        self._thread = threading.Thread(
            target=self._server.run,
            daemon=True,
            name=f"{self.service_name}-health",
        )
        self._thread.start()
        logger.info(f"Health server started on {self.host}:{self.port}")

    def stop(self) -> None:
        """Stop the health server."""
        if self._server:
            self._server.should_exit = True
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Health server stopped")
