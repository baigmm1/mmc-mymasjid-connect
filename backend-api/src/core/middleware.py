"""
Middleware for Taskify FastAPI application.

Provides cross-cutting concerns: correlation ID injection, error handling,
security headers, and request/response logging.
"""

import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.exceptions import MasjidConnectException
from src.core.logging import CorrelationIdFilter
from src.models.error import ErrorResponse, ValidationErrorDetail

from src.config import settings

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to inject correlation ID for distributed request tracing.

    Generates a unique correlation ID for each request and makes it available
    to all downstream handlers and other middleware. Enables tracing requests
    across microservices.

    The correlation ID is:
    - Generated if not provided in request headers (X-Correlation-ID)
    - Injected into response headers for client reference
    - Made available to loggers via CorrelationIdFilter
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and inject correlation ID.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response with correlation ID
        """
        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

        # Make available to loggers
        CorrelationIdFilter.set_correlation_id(correlation_id)

        try:
            # Process request
            response = await call_next(request)

            # Inject into response headers
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        finally:
            # Clean up
            CorrelationIdFilter.clear_correlation_id()


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for standardized error handling.

    Catches MasjidConnectException instances and converts them to standardized
    error responses. Prevents sensitive information leakage by catching
    all exceptions and returning safe error messages.

    Follows Security-First principle: errors never expose internal details.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and handle errors.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response or error response
        """
        correlation_id = CorrelationIdFilter.get_correlation_id() or "unknown"

        try:
            return await call_next(request)
        except MasjidConnectException as exc:
            # Handle known Masjid Connect exceptions
            error_details = None
            if exc.errors:
                error_details = [
                    ValidationErrorDetail(**err) if isinstance(err, dict) else err
                    for err in exc.errors
                ]

            error_response = ErrorResponse(
                detail=exc.detail,
                error_code=exc.error_code,
                timestamp=__import__("datetime").datetime.utcnow(),
                correlation_id=correlation_id,
                errors=error_details,
            )
            return JSONResponse(
                status_code=exc.status_code, content=error_response.model_dump()
            )
        except Exception as exc:
            # Handle unexpected exceptions (never expose details)            
            error_response = ErrorResponse(
                detail="An unexpected error occurred",
                error_code="INTERNAL_SERVER_ERROR",
                timestamp=__import__("datetime").datetime.utcnow(),
                correlation_id=correlation_id,
                errors=None,
            )
            if settings.ENVIRONMENT != "production":
                error_response.detail = f": {str(exc)}"
                
            return JSONResponse(status_code=500, content=error_response.model_dump())


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Implements HTTP security headers as per OWASP recommendations:
    - X-Content-Type-Options: Prevent MIME type sniffing
    - X-Frame-Options: Prevent clickjacking
    - X-XSS-Protection: Legacy XSS protection
    - Strict-Transport-Security: HTTPS enforcement
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add security headers.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response with security headers
        """
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Legacy XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # HTTPS enforcement (set to large value in production)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
