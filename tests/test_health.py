"""Tests for health server."""
import pytest
from fastapi.testclient import TestClient

from amptimal_shared.health import create_health_app


class TestHealthApp:
    @pytest.fixture
    def status_callback(self):
        return lambda: {"items_processed": 42}

    @pytest.fixture
    def healthy_deps(self):
        return lambda: True

    @pytest.fixture
    def unhealthy_deps(self):
        return lambda: False

    @pytest.fixture
    def app(self, status_callback, healthy_deps):
        return create_health_app(
            "test-service",
            status_callback,
            healthy_deps,
        )

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "test-service"

    def test_ready_returns_200_when_deps_healthy(self, client):
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["items_processed"] == 42

    def test_ready_returns_503_when_deps_unhealthy(self, status_callback, unhealthy_deps):
        app = create_health_app("test-service", status_callback, unhealthy_deps)
        client = TestClient(app)

        response = client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"

    def test_metrics_returns_prometheus_format(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]


class TestHealthAppWithoutDependencyCheck:
    def test_ready_works_without_dep_check(self):
        app = create_health_app(
            "test-service",
            lambda: {"count": 10},
            check_dependencies=None,
        )
        client = TestClient(app)

        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json()["count"] == 10
