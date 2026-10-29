"""
Unit tests for middleware components.

Tests verify correlation ID generation, error handling, and security headers
in isolation without running the full application.

Test markers:
- @pytest.mark.unit: Unit test (isolated middleware testing)
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from starlette.responses import Response

from src.core.exceptions import NotFoundError, ValidationError
from src.core.logging import CorrelationIdFilter
from src.core.middleware import (
    CorrelationIdMiddleware,
    ErrorHandlerMiddleware,
    SecurityHeadersMiddleware,
)


@pytest.mark.unit
class TestCorrelationIdMiddleware:
    """Unit tests for CorrelationIdMiddleware."""

    @pytest.mark.asyncio
    async def test_generates_correlation_id_when_not_provided(self):
        """Test middleware generates correlation ID if not in request headers."""
        middleware = CorrelationIdMiddleware(app=None)

        # Create mock request without correlation ID
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = None

        # Create mock response
        mock_response = Response()
        mock_response.headers = {}

        # Mock call_next
        async def mock_call_next(request):
            return mock_response

        # Execute middleware
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Should have generated and added correlation ID to response
        assert "X-Correlation-ID" in response.headers
        # Should be UUID format
        correlation_id = response.headers["X-Correlation-ID"]
        assert uuid.UUID(correlation_id)  # Will raise if not valid UUID

    @pytest.mark.asyncio
    async def test_uses_existing_correlation_id_from_header(self):
        """Test middleware uses correlation ID from request header if provided."""
        middleware = CorrelationIdMiddleware(app=None)

        custom_id = "custom-correlation-12345"
        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = custom_id

        mock_response = Response()
        mock_response.headers = {}

        async def mock_call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Should use the provided correlation ID
        assert response.headers["X-Correlation-ID"] == custom_id

    @pytest.mark.asyncio
    async def test_makes_correlation_id_available_to_loggers(self):
        """Test middleware sets correlation ID for logging filter."""
        middleware = CorrelationIdMiddleware(app=None)

        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = "test-id-123"

        mock_response = Response()
        mock_response.headers = {}

        correlation_id_captured = None

        async def mock_call_next(request):
            # Capture correlation ID during request processing
            nonlocal correlation_id_captured
            correlation_id_captured = CorrelationIdFilter.get_correlation_id()
            return mock_response

        await middleware.dispatch(mock_request, mock_call_next)

        # Should have been set during request processing
        assert correlation_id_captured == "test-id-123"

    @pytest.mark.asyncio
    async def test_cleans_up_correlation_id_after_request(self):
        """Test middleware cleans up correlation ID after request completes."""
        middleware = CorrelationIdMiddleware(app=None)

        mock_request = MagicMock(spec=Request)
        mock_request.headers.get.return_value = "cleanup-test"

        mock_response = Response()
        mock_response.headers = {}

        async def mock_call_next(request):
            return mock_response

        await middleware.dispatch(mock_request, mock_call_next)

        # Should be cleaned up after request
        assert CorrelationIdFilter.get_correlation_id() is None


@pytest.mark.unit
class TestErrorHandlerMiddleware:
    """Unit tests for ErrorHandlerMiddleware."""

    @pytest.mark.asyncio
    async def test_passes_through_successful_requests(self):
        """Test middleware passes through requests that don't raise exceptions."""
        middleware = ErrorHandlerMiddleware(app=None)

        mock_request = MagicMock(spec=Request)
        mock_response = Response(content="Success", status_code=200)

        async def mock_call_next(request):
            return mock_response

        # Set correlation ID
        CorrelationIdFilter.set_correlation_id("test-123")

        try:
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200
            assert response.body == b"Success"
        finally:
            CorrelationIdFilter.clear_correlation_id()

    @pytest.mark.asyncio
    async def test_catches_masjidconnect_exceptions(self):
        """Test middleware catches MasjidConnectException and returns error response."""
        middleware = ErrorHandlerMiddleware(app=None)

        mock_request = MagicMock(spec=Request)

        async def mock_call_next(request):
            raise NotFoundError(detail="Resource not found")

        # Set correlation ID
        CorrelationIdFilter.set_correlation_id("error-test-123")

        try:
            response = await middleware.dispatch(mock_request, mock_call_next)

            # Should return 404
            assert response.status_code == 404

            # Should be JSON response
            import json

            body = json.loads(response.body)
            assert body["detail"] == "Resource not found"
            assert body["error_code"] == "NOT_FOUND_ERROR"
            assert body["correlation_id"] == "error-test-123"
        finally:
            CorrelationIdFilter.clear_correlation_id()

    @pytest.mark.asyncio
    async def test_catches_validation_errors_with_field_details(self):
        """Test middleware handles ValidationError with field-level errors."""
        middleware = ErrorHandlerMiddleware(app=None)

        mock_request = MagicMock(spec=Request)

        errors = [{"field": "email", "message": "Invalid format", "type": "value_error"}]

        async def mock_call_next(request):
            raise ValidationError(detail="Validation failed", errors=errors)

        CorrelationIdFilter.set_correlation_id("validation-test")

        try:
            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.status_code == 400

            import json

            body = json.loads(response.body)
            assert body["detail"] == "Validation failed"
            assert body["error_code"] == "VALIDATION_ERROR"
            assert len(body["errors"]) == 1
            assert body["errors"][0]["field"] == "email"
        finally:
            CorrelationIdFilter.clear_correlation_id()

    @pytest.mark.asyncio
    async def test_catches_unexpected_exceptions(self):
        """Test middleware catches unexpected exceptions and returns generic error."""
        middleware = ErrorHandlerMiddleware(app=None)

        mock_request = MagicMock(spec=Request)

        async def mock_call_next(request):
            raise Exception("Unexpected database error")

        CorrelationIdFilter.set_correlation_id("unexpected-error")

        try:
            response = await middleware.dispatch(mock_request, mock_call_next)

            # Should return 500
            assert response.status_code == 500

            import json

            body = json.loads(response.body)
            # Should NOT expose internal error details (Security-First)
            assert body["detail"] == "An unexpected error occurred"
            assert body["error_code"] == "INTERNAL_SERVER_ERROR"
            assert "database" not in body["detail"].lower()
        finally:
            CorrelationIdFilter.clear_correlation_id()

    @pytest.mark.asyncio
    async def test_includes_correlation_id_in_error_responses(self):
        """Test error responses include correlation ID for tracing."""
        middleware = ErrorHandlerMiddleware(app=None)

        mock_request = MagicMock(spec=Request)

        async def mock_call_next(request):
            raise NotFoundError()

        test_correlation = "correlation-id-test"
        CorrelationIdFilter.set_correlation_id(test_correlation)

        try:
            response = await middleware.dispatch(mock_request, mock_call_next)

            import json

            body = json.loads(response.body)
            assert body["correlation_id"] == test_correlation
        finally:
            CorrelationIdFilter.clear_correlation_id()


@pytest.mark.unit
class TestSecurityHeadersMiddleware:
    """Unit tests for SecurityHeadersMiddleware."""

    @pytest.mark.asyncio
    async def test_adds_x_content_type_options_header(self):
        """Test middleware adds X-Content-Type-Options header."""
        middleware = SecurityHeadersMiddleware(app=None)

        mock_request = MagicMock(spec=Request)
        mock_response = Response()
        mock_response.headers = {}

        async def mock_call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.headers["X-Content-Type-Options"] == "nosniff"

    @pytest.mark.asyncio
    async def test_adds_x_frame_options_header(self):
        """Test middleware adds X-Frame-Options header."""
        middleware = SecurityHeadersMiddleware(app=None)

        mock_request = MagicMock(spec=Request)
        mock_response = Response()
        mock_response.headers = {}

        async def mock_call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.headers["X-Frame-Options"] == "DENY"

    @pytest.mark.asyncio
    async def test_adds_x_xss_protection_header(self):
        """Test middleware adds X-XSS-Protection header."""
        middleware = SecurityHeadersMiddleware(app=None)

        mock_request = MagicMock(spec=Request)
        mock_response = Response()
        mock_response.headers = {}

        async def mock_call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.headers["X-XSS-Protection"] == "1; mode=block"

    @pytest.mark.asyncio
    async def test_adds_strict_transport_security_header(self):
        """Test middleware adds Strict-Transport-Security header."""
        middleware = SecurityHeadersMiddleware(app=None)

        mock_request = MagicMock(spec=Request)
        mock_response = Response()
        mock_response.headers = {}

        async def mock_call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert "Strict-Transport-Security" in response.headers
        assert "max-age=" in response.headers["Strict-Transport-Security"]

    @pytest.mark.asyncio
    async def test_adds_all_security_headers(self):
        """Test middleware adds all required security headers."""
        middleware = SecurityHeadersMiddleware(app=None)

        mock_request = MagicMock(spec=Request)
        mock_response = Response()
        mock_response.headers = {}

        async def mock_call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Check all security headers are present
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
        ]

        for header in required_headers:
            assert header in response.headers, f"Missing security header: {header}"
