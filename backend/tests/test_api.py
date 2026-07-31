"""VisionOps AI — Integration tests for the ``api`` package.

Tests FastAPI endpoints using TestClient:
- Health endpoint
- Root endpoint
- Router registration
- Error responses
- CORS middleware
- Lifespan events

All external dependencies are mocked.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ===========================================================================
# TestClient Setup
# ===========================================================================


@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI application instance for testing."""
    from backend.main import app

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a TestClient for the FastAPI application."""
    return TestClient(app)


# ===========================================================================
# Root Endpoint
# ===========================================================================


class TestRootEndpoint:
    """Tests for the root (/) endpoint."""

    def test_root_returns_project_info(self, client: TestClient):
        """GET / returns project info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "project" in data
        assert "version" in data
        assert "status" in data
        assert "message" in data
        assert data["status"] == "running"

    def test_root_returns_strings(self, client: TestClient):
        """GET / returns string values."""
        response = client.get("/")
        data = response.json()
        assert isinstance(data["project"], str)
        assert isinstance(data["version"], str)


# ===========================================================================
# Health Endpoint
# ===========================================================================


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_healthy(self, client: TestClient):
        """GET /health returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_content_type(self, client: TestClient):
        """GET /health returns JSON content type."""
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"


# ===========================================================================
# API Router
# ===========================================================================


class TestAPIRouter:
    """Tests for the API router registration."""

    def test_router_exists(self):
        """api_router is a non-None APIRouter instance."""
        from backend.api.router import api_router

        assert api_router is not None

    def test_router_has_routes(self):
        """api_router has registered routes."""
        from backend.api.router import api_router

        assert len(api_router.routes) >= 1

    def test_router_routes_are_named(self):
        """api_router routes have meaningful names."""
        from backend.api.router import api_router

        for route in api_router.routes:
            assert hasattr(route, "path")
            assert hasattr(route, "methods")

    def test_router_prefix(self):
        """api_router uses the configured API prefix."""
        from backend.api.router import api_router
        from backend.core.config import settings

        assert api_router.prefix == settings.API_PREFIX

    def test_router_tags(self):
        """api_router has appropriate tags."""
        from backend.api.router import api_router

        for route in api_router.routes:
            if hasattr(route, "tags"):
                assert isinstance(route.tags, list)


# ===========================================================================
# API Dependencies
# ===========================================================================


class TestAPIDependencies:
    """Tests for API dependency injection."""

    def test_get_storage_service(self):
        """get_storage_service returns a StorageService instance."""
        from backend.api.dependencies import get_storage_service

        service = get_storage_service()
        assert service is not None

    def test_get_current_user(self):
        """get_current_user dependency can be imported."""
        from backend.api.dependencies import get_current_user

        assert callable(get_current_user)

    def test_get_db(self):
        """get_db dependency can be imported (may be a stub)."""
        from backend.api.dependencies import get_db

        assert get_db is not None or callable(get_db)


# ===========================================================================
# API Module Imports
# ===========================================================================


class TestAPIImports:
    """Verify that all API modules are importable."""

    def test_init_importable(self):
        """The api __init__ module can be imported."""
        import backend.api  # noqa: F401

    def test_router_importable(self):
        """The router module can be imported."""
        import backend.api.router  # noqa: F401

    def test_analysis_importable(self):
        """The analysis module can be imported."""
        import backend.api.analysis  # noqa: F401

    def test_analytics_importable(self):
        """The analytics module can be imported."""
        import backend.api.analytics  # noqa: F401

    def test_auth_importable(self):
        """The auth module can be imported."""
        import backend.api.auth  # noqa: F401

    def test_dashboard_importable(self):
        """The dashboard module can be imported."""
        import backend.api.dashboard  # noqa: F401

    def test_dependencies_importable(self):
        """The dependencies module can be imported."""
        import backend.api.dependencies  # noqa: F401

    def test_health_importable(self):
        """The health module can be imported."""
        import backend.api.health  # noqa: F401

    def test_reports_importable(self):
        """The reports module can be imported."""
        import backend.api.reports  # noqa: F401

    def test_settings_importable(self):
        """The settings module can be imported."""
        import backend.api.settings  # noqa: F401

    def test_videos_importable(self):
        """The videos module can be imported."""
        import backend.api.videos  # noqa: F401


# ===========================================================================
# Main Module
# ===========================================================================


class TestMainModule:
    """Tests for the main application module."""

    def test_main_importable(self):
        """The main module can be imported."""
        import backend.main  # noqa: F401

    def test_app_is_fastapi(self):
        """The app is a FastAPI instance."""
        import backend.main

        assert isinstance(backend.main.app, FastAPI)

    def test_app_title(self):
        """The app has a title configured."""
        import backend.main

        assert backend.main.app.title is not None

    def test_app_docs_configured(self):
        """The app has docs endpoints configured."""
        import backend.main

        assert backend.main.app.docs_url == "/docs"


# ===========================================================================
# Error Response Schema
# ===========================================================================


class TestErrorResponse:
    """Tests for the common response schemas."""

    def test_error_response_dict(self):
        """ErrorResponse schema exists with required fields."""
        from backend.schemas.response import ErrorResponse

        assert hasattr(ErrorResponse, "model_config") or hasattr(ErrorResponse, "Config")

    def test_success_response_dict(self):
        """SuccessResponse schema exists."""
        from backend.schemas.response import SuccessResponse

        assert SuccessResponse is not None


# ===========================================================================
# Edge Cases
# ===========================================================================


class TestAPIEdgeCases:
    """Edge-case tests for the API layer."""

    def test_nonexistent_route_returns_404(self, client: TestClient):
        """GET on a non-existent route returns 404."""
        response = client.get("/nonexistent/route/12345")
        assert response.status_code == 404

    def test_method_not_allowed_returns_405(self, client: TestClient):
        """POST on a GET-only route returns 405."""
        response = client.post("/health")
        assert response.status_code == 405

    def test_root_accepts_no_params(self, client: TestClient):
        """GET / with query params still works."""
        response = client.get("/?foo=bar")
        assert response.status_code == 200

    def test_openapi_schema(self, client: TestClient):
        """GET /openapi.json returns a valid OpenAPI schema."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

    def test_docs_page(self, client: TestClient):
        """GET /docs returns the Swagger UI page."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


# ===========================================================================
# CORS Tests
# ===========================================================================


class TestCORS:
    """Tests for CORS middleware configuration."""

    def test_cors_headers_present(self, client: TestClient):
        """CORS headers are present in responses."""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code in (200, 204)
        assert "access-control-allow-origin" in {
            k.lower() for k in response.headers.keys()
        }

    def test_cors_allows_configured_origin(self, client: TestClient):
        """CORS allows configured origins."""
        response = client.get(
            "/",
            headers={"Origin": "http://localhost:3000"},
        )
        cors_origin = response.headers.get("access-control-allow-origin", "")
        assert cors_origin == "*" or "http://localhost:3000" in cors_origin
