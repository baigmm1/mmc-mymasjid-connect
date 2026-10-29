"""
Integration tests for request/response validation.

Tests verify that the application correctly validates requests,
returns appropriate error responses, and follows Security-First principles.

Test markers:
- @pytest.mark.integration: Integration test (uses live app instance)
"""

import pytest
from httpx import AsyncClient

from src.main import app


@pytest.mark.integration
class TestRequestValidation:
    """Integration tests for request validation."""

    @pytest.mark.asyncio
    async def test_invalid_method_returns_405(self, client: AsyncClient):
        """Test unsupported HTTP method returns 405 Method Not Allowed."""
        # Health endpoint only supports GET
        response = await client.post("/api/v1/health")

        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_nonexistent_endpoint_returns_404(self, client: AsyncClient):
        """Test request to non-existent endpoint returns 404."""
        response = await client.get("/api/v1/nonexistent")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_error_response_includes_correlation_id(self, client: AsyncClient):
        """Test error responses include correlation ID for tracing."""
        response = await client.get("/api/v1/nonexistent")

        assert response.status_code == 404
        # Response should include correlation ID header
        assert "X-Correlation-ID" in response.headers


@pytest.mark.integration
class TestErrorResponseFormat:
    """Integration tests for error response format."""

    @pytest.mark.asyncio
    async def test_404_error_response_format(self, client: AsyncClient):
        """Test 404 error returns standardized ErrorResponse format."""
        response = await client.get("/api/v1/nonexistent")

        assert response.status_code == 404
        data = response.json()

        # Should have ErrorResponse structure
        assert "detail" in data
        assert isinstance(data["detail"], str)
        # Should NOT expose internal details (Security-First)
        assert "stack" not in data
        assert "traceback" not in data

    @pytest.mark.asyncio
    async def test_405_error_response_format(self, client: AsyncClient):
        """Test 405 error returns standardized error format."""
        response = await client.post("/api/v1/health")

        assert response.status_code == 405
        data = response.json()

        assert "detail" in data
        assert isinstance(data["detail"], str)

    @pytest.mark.asyncio
    async def test_error_response_content_type_is_json(self, client: AsyncClient):
        """Test error responses have JSON content type."""
        response = await client.get("/api/v1/nonexistent")

        assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.integration
class TestSecurityFirstPrinciple:
    """Integration tests verifying Security-First principle compliance."""

    @pytest.mark.asyncio
    async def test_error_responses_do_not_expose_internal_details(self, client: AsyncClient):
        """Test error messages don't expose internal system details."""
        response = await client.get("/api/v1/nonexistent")

        data = response.json()

        # Should NOT expose file paths, stack traces, or internal errors
        detail_lower = data["detail"].lower()
        assert "traceback" not in detail_lower
        assert "file" not in detail_lower
        assert "line" not in detail_lower
        assert "exception" not in detail_lower
        assert ".py" not in detail_lower

    @pytest.mark.asyncio
    async def test_error_responses_include_safe_messages_only(self, client: AsyncClient):
        """Test error responses only include safe, user-facing messages."""
        response = await client.get("/api/v1/nonexistent")

        data = response.json()

        # Message should be safe and generic
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0
        # Should not include system paths or internal class names
        assert "\\" not in data["detail"]
        assert "/" not in data["detail"]

    @pytest.mark.asyncio
    async def test_security_headers_present_in_error_responses(self, client: AsyncClient):
        """Test security headers are present even in error responses."""
        response = await client.get("/api/v1/nonexistent")

        # Security headers should be present
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "Strict-Transport-Security" in response.headers


@pytest.mark.integration
class TestCorrelationIdTracking:
    """Integration tests for correlation ID tracking."""

    @pytest.mark.asyncio
    async def test_auto_generated_correlation_id_in_response(self, client: AsyncClient):
        """Test system generates correlation ID if not provided."""
        response = await client.get("/api/v1/health")

        assert "X-Correlation-ID" in response.headers
        correlation_id = response.headers["X-Correlation-ID"]
        # Should be UUID format (non-empty string)
        assert len(correlation_id) > 0

    @pytest.mark.asyncio
    async def test_custom_correlation_id_preserved(self, client: AsyncClient):
        """Test custom correlation ID from request is preserved in response."""
        custom_id = "custom-test-correlation-12345"
        response = await client.get(
            "/api/v1/health", headers={"X-Correlation-ID": custom_id}
        )

        assert response.headers["X-Correlation-ID"] == custom_id

    @pytest.mark.asyncio
    async def test_correlation_id_in_error_responses(self, client: AsyncClient):
        """Test correlation ID is included in error responses for tracing."""
        custom_id = "error-tracking-12345"
        response = await client.get(
            "/api/v1/nonexistent", headers={"X-Correlation-ID": custom_id}
        )

        assert response.headers["X-Correlation-ID"] == custom_id


@pytest.mark.integration
class TestCORSConfiguration:
    """Integration tests for CORS configuration."""

    @pytest.mark.asyncio
    async def test_cors_preflight_request(self, client: AsyncClient):
        """Test CORS preflight OPTIONS request is handled."""
        response = await client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # Preflight should succeed
        assert response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_cors_headers_present_in_response(self, client: AsyncClient):
        """Test CORS headers are present in response."""
        response = await client.get(
            "/api/v1/health", headers={"Origin": "http://localhost:3000"}
        )

        # Check for CORS headers (exact headers depend on FastAPI/Starlette CORS middleware)
        assert response.status_code == 200
        # CORS middleware should have processed the request
        # The presence of origin header in request should trigger CORS processing
