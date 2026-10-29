"""
API contract tests for health endpoint.

Contract tests verify the API contract - the shape and format of requests/responses.
These tests ensure the API adheres to OpenAPI specification and client expectations.

Test markers:
- @pytest.mark.contract: Contract/API test (verifies API shape)
"""

import pytest
from httpx import AsyncClient

from src.main import app


@pytest.mark.contract
class TestHealthEndpointContract:
    """Contract tests verifying health endpoint API shape."""

    @pytest.mark.asyncio
    async def test_health_response_schema_status_field(self, client: AsyncClient):
        """Verify response schema includes status field with valid value."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert data["status"] in ["ok", "degraded", "unhealthy"]

    @pytest.mark.asyncio
    async def test_health_response_schema_timestamp_field(self, client: AsyncClient):
        """Verify response schema includes ISO 8601 timestamp."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert "timestamp" in data
        timestamp = data["timestamp"]
        assert isinstance(timestamp, str)
        # Should be ISO 8601 format (with Z suffix)
        assert timestamp.endswith("Z")

    @pytest.mark.asyncio
    async def test_health_response_schema_version_field(self, client: AsyncClient):
        """Verify response schema includes version field."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert "version" in data
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

    @pytest.mark.asyncio
    async def test_health_response_schema_environment_field(self, client: AsyncClient):
        """Verify response schema includes environment field."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert "environment" in data
        assert data["environment"] in ["development", "testing", "production"]

    @pytest.mark.asyncio
    async def test_health_endpoint_http_method_get(self, client: AsyncClient):
        """Verify health endpoint only accepts GET requests."""
        # GET should work
        response = await client.get("/api/v1/health")
        assert response.status_code == 200

        # POST should not work
        response = await client.post("/api/v1/health")
        assert response.status_code == 405  # Method Not Allowed

        # PUT should not work
        response = await client.put("/api/v1/health")
        assert response.status_code == 405

        # DELETE should not work
        response = await client.delete("/api/v1/health")
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_health_endpoint_path_is_versioned(self, client: AsyncClient):
        """Verify health endpoint uses versioned path /api/v1/health."""
        # Versioned path should work
        response = await client.get("/api/v1/health")
        assert response.status_code == 200

        # Root path should not work
        response = await client.get("/health")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_health_response_no_extra_fields(self, client: AsyncClient):
        """Verify response only contains contract fields."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        # Only these fields should be present
        expected_fields = {"status", "timestamp", "version", "environment"}
        actual_fields = set(data.keys())

        assert actual_fields == expected_fields

    @pytest.mark.asyncio
    async def test_health_response_content_type_json(self, client: AsyncClient):
        """Verify response content type is JSON."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_health_endpoint_openapi_documented(self, client: AsyncClient):
        """Verify health endpoint is documented in OpenAPI schema."""
        response = await client.get("/openapi.json")

        assert response.status_code == 200
        openapi_schema = response.json()

        # Check health endpoint is documented
        paths = openapi_schema.get("paths", {})
        assert "/api/v1/health" in paths

        health_path = paths["/api/v1/health"]
        assert "get" in health_path

        # Check response schema
        get_operation = health_path["get"]
        assert "responses" in get_operation
        assert "200" in get_operation["responses"]

    @pytest.mark.asyncio
    async def test_health_endpoint_response_headers_match_contract(self, client: AsyncClient):
        """Verify response includes required headers."""
        response = await client.get("/api/v1/health")

        assert response.status_code == 200

        # Check for correlation ID (required for tracing)
        assert "X-Correlation-ID" in response.headers
        assert len(response.headers["X-Correlation-ID"]) > 0

        # Check for security headers (required per spec)
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
        ]
        for header in required_headers:
            assert header in response.headers, f"Missing required header: {header}"
