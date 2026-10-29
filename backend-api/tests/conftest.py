"""
Shared pytest fixtures for all tests.

This module provides fixtures that can be used across unit, integration,
and contract tests to set up common test infrastructure.

Path Configuration:
    Automatically adds the backend-api directory to sys.path so tests can
    be run from the backend-api directory without setting PYTHONPATH:
        pytest tests/
        pytest tests/unit/
        pytest tests/integration/
"""

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

# Automatically configure Python path for imports
# This allows running tests from backend-api directory without PYTHONPATH setup
backend_api_dir = Path(__file__).parent.parent.resolve()
if str(backend_api_dir) not in sys.path:
    sys.path.insert(0, str(backend_api_dir))

# Now we can import from src
from src.main import create_app


@pytest.fixture
def test_env(monkeypatch):
    """
    Fixture to set test environment variables.

    Provides isolation for environment-based configuration changes.
    """
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("DEBUG", "True")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("API_VERSION", "v1")
    yield
    # Cleanup is automatic with monkeypatch


@pytest.fixture
def sample_health_status():
    """
    Fixture providing sample HealthStatus data.

    Useful for tests that need pre-built health status responses.
    """
    from datetime import datetime

    from src.models.health import HealthStatus

    return HealthStatus(
        status="ok",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        environment="testing",
    )


@pytest.fixture
def sample_error_response():
    """
    Fixture providing sample ErrorResponse data.

    Useful for tests that need pre-built error responses.
    """
    from datetime import datetime

    from src.models.error import ErrorResponse

    return ErrorResponse(
        detail="Test error",
        error_code="TEST_ERROR",
        timestamp=datetime.utcnow(),
        correlation_id="test-correlation-id",
        errors=None,
    )


@pytest.fixture
async def client():
    """
    Fixture providing an async HTTP client for testing.

    Creates a FastAPI app instance with an ASGI transport for httpx AsyncClient.
    This allows tests to make HTTP requests to the application without running
    a real server.

    Usage:
        async def test_endpoint(client):
            response = await client.get("/api/v1/health")
            assert response.status_code == 200
    """
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
