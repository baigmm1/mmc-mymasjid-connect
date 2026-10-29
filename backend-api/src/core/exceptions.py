"""
Core custom exceptions for Masjid Connect application.

These exceptions are mapped to appropriate HTTP status codes and serialized
to standardized error responses following the Security-First principle.
"""

from typing import List, Optional


class MasjidConnectException(Exception):
    """
    Base exception for all Masjid Connect-specific errors.

    All custom exceptions inherit from this to enable uniform handling.

    Attributes:
        detail: Human-readable error message (no internal details for security)
        error_code: Machine-readable error code (UPPERCASE_WITH_UNDERSCORES)
        status_code: HTTP status code to return
        errors: Optional list of validation error details
    """

    def __init__(
        self,
        detail: str,
        error_code: str,
        status_code: int = 500,
        errors: Optional[List[dict]] = None,
    ):
        """
        Initialize Masjid Connect exception.

        Args:
            detail: User-friendly error message
            error_code: Machine-readable error code
            status_code: HTTP status code (default 500)
            errors: Optional list of field-level error details
        """
        self.detail = detail
        self.error_code = error_code
        self.status_code = status_code
        self.errors = errors
        super().__init__(self.detail)


class ValidationError(MasjidConnectException):
    """Request validation error (HTTP 400)."""

    def __init__(self, detail: str, errors: Optional[List[dict]] = None):
        """
        Initialize validation error.

        Args:
            detail: Description of validation failure
            errors: List of field-level error details
        """
        super().__init__(
            detail=detail,
            error_code="VALIDATION_ERROR",
            status_code=400,
            errors=errors,
        )


class AuthenticationError(MasjidConnectException):
    """Missing or invalid authentication (HTTP 401)."""

    def __init__(self, detail: str = "Authentication required"):
        """Initialize authentication error."""
        super().__init__(
            detail=detail, error_code="AUTHENTICATION_ERROR", status_code=401
        )


class AuthorizationError(MasjidConnectException):
    """Insufficient permissions (HTTP 403)."""

    def __init__(self, detail: str = "Insufficient permissions"):
        """Initialize authorization error."""
        super().__init__(
            detail=detail, error_code="AUTHORIZATION_ERROR", status_code=403
        )


class NotFoundError(MasjidConnectException):
    """Resource not found (HTTP 404)."""

    def __init__(self, detail: str = "Resource not found"):
        """Initialize not found error."""
        super().__init__(detail=detail, error_code="NOT_FOUND_ERROR", status_code=404)


class ConflictError(MasjidConnectException):
    """Resource conflict (HTTP 409)."""

    def __init__(self, detail: str = "Resource conflict"):
        """Initialize conflict error."""
        super().__init__(detail=detail, error_code="CONFLICT_ERROR", status_code=409)


class InternalServerError(MasjidConnectException):
    """Internal server error (HTTP 500)."""

    def __init__(self, detail: str = "Internal server error"):
        """Initialize internal server error."""
        super().__init__(
            detail=detail, error_code="INTERNAL_SERVER_ERROR", status_code=500
        )


class ServiceUnavailableError(MasjidConnectException):
    """Service temporarily unavailable (HTTP 503)."""

    def __init__(self, detail: str = "Service temporarily unavailable"):
        """Initialize service unavailable error."""
        super().__init__(
            detail=detail, error_code="SERVICE_UNAVAILABLE_ERROR", status_code=503
        )
