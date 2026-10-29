"""
Unit tests for custom exception classes.

Tests verify exception creation, error code mapping, HTTP status codes,
and exception attributes for all custom exception types.

Test markers:
- @pytest.mark.unit: Unit test (isolated exception testing)
"""

import pytest

from src.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    InternalServerError,
    NotFoundError,
    ServiceUnavailableError,
    MasjidConnectException,
    ValidationError,
)


@pytest.mark.unit
class TestMasjidConnectException:
    """Unit tests for base MasjidConnectException class."""

    def test_masjidconnect_exception_creation(self):
        """Test creating MasjidConnectException with all parameters."""
        exc = MasjidConnectException(
            detail="Test error",
            error_code="TEST_ERROR",
            status_code=500,
            errors=None,
        )
        assert exc.detail == "Test error"
        assert exc.error_code == "TEST_ERROR"
        assert exc.status_code == 500
        assert exc.errors is None

    def test_masjidconnect_exception_default_status_code(self):
        """Test MasjidConnectException defaults to 500 status code."""
        exc = MasjidConnectException(detail="Test", error_code="TEST")
        assert exc.status_code == 500

    def test_masjidconnect_exception_with_errors(self):
        """Test MasjidConnectException with validation errors."""
        errors = [{"field": "email", "message": "Invalid"}]
        exc = MasjidConnectException(
            detail="Test", error_code="TEST", status_code=400, errors=errors
        )
        assert exc.errors == errors
        assert len(exc.errors) == 1

    def test_masjidconnect_exception_is_exception(self):
        """Test MasjidConnectException inherits from Exception."""
        exc = MasjidConnectException(detail="Test", error_code="TEST")
        assert isinstance(exc, Exception)

    def test_masjidconnect_exception_str_representation(self):
        """Test MasjidConnectException string representation."""
        exc = MasjidConnectException(detail="Test error message", error_code="TEST")
        assert str(exc) == "Test error message"


@pytest.mark.unit
class TestValidationError:
    """Unit tests for ValidationError exception."""

    def test_validation_error_creation(self):
        """Test creating ValidationError."""
        exc = ValidationError(detail="Invalid input")
        assert exc.detail == "Invalid input"
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.status_code == 400

    def test_validation_error_with_errors(self):
        """Test ValidationError with field-level errors."""
        errors = [
            {"field": "email", "message": "Invalid format", "type": "value_error"}
        ]
        exc = ValidationError(detail="Validation failed", errors=errors)
        assert exc.errors == errors
        assert exc.status_code == 400

    def test_validation_error_inherits_from_masjidconnect(self):
        """Test ValidationError inherits from MasjidConnectException."""
        exc = ValidationError(detail="Test")
        assert isinstance(exc, MasjidConnectException)


@pytest.mark.unit
class TestAuthenticationError:
    """Unit tests for AuthenticationError exception."""

    def test_authentication_error_creation(self):
        """Test creating AuthenticationError."""
        exc = AuthenticationError()
        assert exc.detail == "Authentication required"
        assert exc.error_code == "AUTHENTICATION_ERROR"
        assert exc.status_code == 401

    def test_authentication_error_custom_detail(self):
        """Test AuthenticationError with custom detail."""
        exc = AuthenticationError(detail="Invalid token")
        assert exc.detail == "Invalid token"
        assert exc.status_code == 401

    def test_authentication_error_inherits_from_masjidconnect(self):
        """Test AuthenticationError inherits from MasjidConnectException."""
        exc = AuthenticationError()
        assert isinstance(exc, MasjidConnectException)


@pytest.mark.unit
class TestAuthorizationError:
    """Unit tests for AuthorizationError exception."""

    def test_authorization_error_creation(self):
        """Test creating AuthorizationError."""
        exc = AuthorizationError()
        assert exc.detail == "Insufficient permissions"
        assert exc.error_code == "AUTHORIZATION_ERROR"
        assert exc.status_code == 403

    def test_authorization_error_custom_detail(self):
        """Test AuthorizationError with custom detail."""
        exc = AuthorizationError(detail="Access denied")
        assert exc.detail == "Access denied"
        assert exc.status_code == 403

    def test_authorization_error_inherits_from_masjidconnect(self):
        """Test AuthorizationError inherits from MasjidConnectException."""
        exc = AuthorizationError()
        assert isinstance(exc, MasjidConnectException)


@pytest.mark.unit
class TestNotFoundError:
    """Unit tests for NotFoundError exception."""

    def test_not_found_error_creation(self):
        """Test creating NotFoundError."""
        exc = NotFoundError()
        assert exc.detail == "Resource not found"
        assert exc.error_code == "NOT_FOUND_ERROR"
        assert exc.status_code == 404

    def test_not_found_error_custom_detail(self):
        """Test NotFoundError with custom detail."""
        exc = NotFoundError(detail="User not found")
        assert exc.detail == "User not found"
        assert exc.status_code == 404

    def test_not_found_error_inherits_from_masjidconnect(self):
        """Test NotFoundError inherits from MasjidConnectException."""
        exc = NotFoundError()
        assert isinstance(exc, MasjidConnectException)


@pytest.mark.unit
class TestConflictError:
    """Unit tests for ConflictError exception."""

    def test_conflict_error_creation(self):
        """Test creating ConflictError."""
        exc = ConflictError()
        assert exc.detail == "Resource conflict"
        assert exc.error_code == "CONFLICT_ERROR"
        assert exc.status_code == 409

    def test_conflict_error_custom_detail(self):
        """Test ConflictError with custom detail."""
        exc = ConflictError(detail="Email already exists")
        assert exc.detail == "Email already exists"
        assert exc.status_code == 409

    def test_conflict_error_inherits_from_masjidconnect(self):
        """Test ConflictError inherits from MasjidConnectException."""
        exc = ConflictError()
        assert isinstance(exc, MasjidConnectException)


@pytest.mark.unit
class TestInternalServerError:
    """Unit tests for InternalServerError exception."""

    def test_internal_server_error_creation(self):
        """Test creating InternalServerError."""
        exc = InternalServerError()
        assert exc.detail == "Internal server error"
        assert exc.error_code == "INTERNAL_SERVER_ERROR"
        assert exc.status_code == 500

    def test_internal_server_error_custom_detail(self):
        """Test InternalServerError with custom detail."""
        exc = InternalServerError(detail="Database connection failed")
        assert exc.detail == "Database connection failed"
        assert exc.status_code == 500

    def test_internal_server_error_inherits_from_masjidconnect(self):
        """Test InternalServerError inherits from MasjidConnectException."""
        exc = InternalServerError()
        assert isinstance(exc, MasjidConnectException)


@pytest.mark.unit
class TestServiceUnavailableError:
    """Unit tests for ServiceUnavailableError exception."""

    def test_service_unavailable_error_creation(self):
        """Test creating ServiceUnavailableError."""
        exc = ServiceUnavailableError()
        assert exc.detail == "Service temporarily unavailable"
        assert exc.error_code == "SERVICE_UNAVAILABLE_ERROR"
        assert exc.status_code == 503

    def test_service_unavailable_error_custom_detail(self):
        """Test ServiceUnavailableError with custom detail."""
        exc = ServiceUnavailableError(detail="Maintenance mode")
        assert exc.detail == "Maintenance mode"
        assert exc.status_code == 503

    def test_service_unavailable_error_inherits_from_masjidconnect(self):
        """Test ServiceUnavailableError inherits from MasjidConnectException."""
        exc = ServiceUnavailableError()
        assert isinstance(exc, MasjidConnectException)


@pytest.mark.unit
class TestExceptionErrorCodeMapping:
    """Tests for exception to error code mapping."""

    def test_all_exceptions_have_unique_error_codes(self):
        """Test all exception types have unique error codes."""
        error_codes = {
            ValidationError(detail="test").error_code,
            AuthenticationError().error_code,
            AuthorizationError().error_code,
            NotFoundError().error_code,
            ConflictError().error_code,
            InternalServerError().error_code,
            ServiceUnavailableError().error_code,
        }
        # Should be 7 unique error codes
        assert len(error_codes) == 7

    def test_http_status_code_mapping(self):
        """Test HTTP status codes are correct for each exception."""
        assert ValidationError(detail="test").status_code == 400
        assert AuthenticationError().status_code == 401
        assert AuthorizationError().status_code == 403
        assert NotFoundError().status_code == 404
        assert ConflictError().status_code == 409
        assert InternalServerError().status_code == 500
        assert ServiceUnavailableError().status_code == 503
