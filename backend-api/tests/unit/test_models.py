"""
Unit tests for Pydantic data models.

Tests verify model validation, serialization, and schema constraints
for HealthStatus, ErrorResponse, and ValidationErrorDetail models.

Test markers:
- @pytest.mark.unit: Unit test (isolated model testing)
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.models.error import ErrorResponse, ValidationErrorDetail
from src.models.health import HealthStatus


@pytest.mark.unit
class TestHealthStatusModel:
    """Unit tests for HealthStatus Pydantic model."""

    def test_health_status_valid_creation(self):
        """Test creating HealthStatus with valid data."""
        health = HealthStatus(
            status="ok",
            timestamp=datetime.utcnow(),
            version="1.0.0",
            environment="development",
        )
        assert health.status == "ok"
        assert health.version == "1.0.0"
        assert health.environment == "development"

    def test_health_status_enum_constraint_ok(self):
        """Test status field accepts 'ok' value."""
        health = HealthStatus(
            status="ok", timestamp=datetime.utcnow(), version="1.0.0"
        )
        assert health.status == "ok"

    def test_health_status_enum_constraint_degraded(self):
        """Test status field accepts 'degraded' value."""
        health = HealthStatus(
            status="degraded", timestamp=datetime.utcnow(), version="1.0.0"
        )
        assert health.status == "degraded"

    def test_health_status_enum_constraint_unhealthy(self):
        """Test status field accepts 'unhealthy' value."""
        health = HealthStatus(
            status="unhealthy", timestamp=datetime.utcnow(), version="1.0.0"
        )
        assert health.status == "unhealthy"

    def test_health_status_invalid_enum_value(self):
        """Test status field rejects invalid enum value."""
        with pytest.raises(ValidationError) as exc_info:
            HealthStatus(
                status="invalid", timestamp=datetime.utcnow(), version="1.0.0"
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("status",) for e in errors)

    def test_health_status_timestamp_required(self):
        """Test timestamp field is required."""
        with pytest.raises(ValidationError) as exc_info:
            HealthStatus(status="ok", version="1.0.0")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("timestamp",) for e in errors)

    def test_health_status_version_optional(self):
        """Test version field is optional."""
        health = HealthStatus(status="ok", timestamp=datetime.utcnow())
        assert health.version is None

    def test_health_status_environment_optional(self):
        """Test environment field is optional."""
        health = HealthStatus(status="ok", timestamp=datetime.utcnow())
        assert health.environment is None

    def test_health_status_serialization(self):
        """Test HealthStatus serializes to JSON correctly."""
        health = HealthStatus(
            status="ok",
            timestamp=datetime(2025, 12, 4, 14, 30, 45),
            version="1.0.0",
            environment="testing",
        )
        json_data = health.model_dump()
        assert json_data["status"] == "ok"
        assert json_data["version"] == "1.0.0"
        assert json_data["environment"] == "testing"
        assert "timestamp" in json_data


@pytest.mark.unit
class TestValidationErrorDetailModel:
    """Unit tests for ValidationErrorDetail Pydantic model."""

    def test_validation_error_detail_creation(self):
        """Test creating ValidationErrorDetail with valid data."""
        detail = ValidationErrorDetail(
            field="email", message="Invalid email format", type="value_error"
        )
        assert detail.field == "email"
        assert detail.message == "Invalid email format"
        assert detail.type == "value_error"

    def test_validation_error_detail_all_fields_required(self):
        """Test all fields are required."""
        with pytest.raises(ValidationError):
            ValidationErrorDetail(field="email")

    def test_validation_error_detail_serialization(self):
        """Test ValidationErrorDetail serializes correctly."""
        detail = ValidationErrorDetail(
            field="user.password", message="Password too short", type="constraint_error"
        )
        json_data = detail.model_dump()
        assert json_data["field"] == "user.password"
        assert json_data["message"] == "Password too short"
        assert json_data["type"] == "constraint_error"


@pytest.mark.unit
class TestErrorResponseModel:
    """Unit tests for ErrorResponse Pydantic model."""

    def test_error_response_creation(self):
        """Test creating ErrorResponse with valid data."""
        error = ErrorResponse(
            detail="Test error",
            error_code="TEST_ERROR",
            timestamp=datetime.utcnow(),
            correlation_id="test-123",
        )
        assert error.detail == "Test error"
        assert error.error_code == "TEST_ERROR"
        assert error.correlation_id == "test-123"

    def test_error_response_all_required_fields(self):
        """Test all required fields must be provided."""
        with pytest.raises(ValidationError) as exc_info:
            ErrorResponse(detail="Test error")
        errors = exc_info.value.errors()
        assert len(errors) >= 2  # Missing error_code, timestamp, correlation_id

    def test_error_response_errors_optional(self):
        """Test errors field is optional."""
        error = ErrorResponse(
            detail="Test error",
            error_code="TEST_ERROR",
            timestamp=datetime.utcnow(),
            correlation_id="test-123",
        )
        assert error.errors is None

    def test_error_response_with_validation_errors(self):
        """Test ErrorResponse with validation error details."""
        validation_errors = [
            ValidationErrorDetail(
                field="email", message="Invalid format", type="value_error"
            ),
            ValidationErrorDetail(
                field="password", message="Too short", type="constraint_error"
            ),
        ]
        error = ErrorResponse(
            detail="Validation failed",
            error_code="VALIDATION_ERROR",
            timestamp=datetime.utcnow(),
            correlation_id="test-123",
            errors=validation_errors,
        )
        assert len(error.errors) == 2
        assert error.errors[0].field == "email"
        assert error.errors[1].field == "password"

    def test_error_response_serialization(self):
        """Test ErrorResponse serializes to JSON correctly."""
        error = ErrorResponse(
            detail="Not found",
            error_code="NOT_FOUND",
            timestamp=datetime(2025, 12, 4, 14, 30, 45),
            correlation_id="req-123",
            errors=None,
        )
        json_data = error.model_dump()
        assert json_data["detail"] == "Not found"
        assert json_data["error_code"] == "NOT_FOUND"
        assert json_data["correlation_id"] == "req-123"
        assert json_data["errors"] is None

    def test_error_response_with_nested_errors_serialization(self):
        """Test ErrorResponse with nested errors serializes correctly."""
        error = ErrorResponse(
            detail="Validation failed",
            error_code="VALIDATION_ERROR",
            timestamp=datetime.utcnow(),
            correlation_id="req-456",
            errors=[
                ValidationErrorDetail(field="name", message="Required", type="required_error")
            ],
        )
        json_data = error.model_dump()
        assert len(json_data["errors"]) == 1
        assert json_data["errors"][0]["field"] == "name"
