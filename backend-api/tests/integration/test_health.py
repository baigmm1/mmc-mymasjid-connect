"""
Integration tests for health check endpoint.

Tests verify that the health endpoint returns correct status, format,
and headers required for container orchestration and load balancers.

Test markers:
- @pytest.mark.integration: Integration test (uses live app instance)
"""

from datetime import datetime

import pytest
from httpx import AsyncClient

from src.main import app


@pytest.mark.integration
class TestHealthEndpoint:
    """Integration tests for GET /api/v1/health endpoint."""

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_ok_status(self, client: AsyncClient):
        """Test that health endpoint returns status 200 and ok status."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_timestamp(self, client: AsyncClient):
        """Test that health endpoint includes valid timestamp."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        # Verify timestamp can be parsed as ISO 8601
        timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        assert timestamp is not None

    @pytest.mark.asyncio
    async def test_health_endpoint_includes_version(self, client: AsyncClient):
        """Test that health endpoint includes API version."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert data["version"] is not None
        # Version should be semver (v1 or similar)
        assert len(data["version"]) > 0

    @pytest.mark.asyncio
    async def test_health_endpoint_includes_environment(self, client: AsyncClient):
        """Test that health endpoint includes deployment environment."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert "environment" in data
        assert data["environment"] in ["development", "testing", "production"]

    @pytest.mark.asyncio
    async def test_health_endpoint_response_format(self, client: AsyncClient):
        """Test that health endpoint response matches HealthStatus model."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields present
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "environment" in data

        # Verify field types
        assert isinstance(data["status"], str)
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["environment"], str)

    @pytest.mark.asyncio
    async def test_health_endpoint_includes_correlation_id_header(self, client: AsyncClient):
        """Test that response includes correlation ID header for tracing."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers

    @pytest.mark.asyncio
    async def test_health_endpoint_includes_security_headers(self, client: AsyncClient):
        """Test that response includes OWASP security headers."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200

        # Check for security headers
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "Strict-Transport-Security" in response.headers

    @pytest.mark.asyncio
    async def test_health_endpoint_content_type(self, client: AsyncClient):
        """Test that response has correct content type."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_health_endpoint_fast_response(self, client: AsyncClient):
        """Test that health endpoint responds quickly (< 100ms)."""
        import time

        start = time.time()
        response = await client.get("/api/v1/health")
        elapsed = (time.time() - start) * 1000  # Convert to ms

        assert response.status_code == 200
        assert elapsed < 100, f"Health endpoint took {elapsed}ms, expected < 100ms"

    @pytest.mark.asyncio
    async def test_health_endpoint_with_custom_correlation_id(self, client: AsyncClient):
        """Test that custom correlation ID is returned in response."""
        custom_id = "test-correlation-12345"
        response = await client.get(
            "/api/v1/health",
            headers={"X-Correlation-ID": custom_id},
        )

        assert response.status_code == 200
        assert response.headers.get("X-Correlation-ID") == custom_id

    @pytest.mark.asyncio
    async def test_health_endpoint_allows_cors_requests(self, client: AsyncClient):
        """Test that health endpoint supports CORS preflight."""
        response = await client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # CORS is handled by middleware, should return 200
        assert response.status_code in [200, 204]
