"""
Error response models for standardized API error handling.

These models ensure consistent error responses across all endpoints,
supporting the Security-First principle by preventing information leakage.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_serializer


class ValidationErrorDetail(BaseModel):
    """
    Individual field-level validation error.

    Used when request validation fails to provide specific details about
    which field has an issue and why.

    Attributes:
        field: JSON path to the field with error (e.g., "user.email")
        message: Human-readable error message
        type: Error type classification (value_error, type_error, required_error, constraint_error)

    Example:
        {
            "field": "email",
            "message": "Invalid email format",
            "type": "value_error"
        }
    """

    field: str = Field(description="Field path with validation error")
    message: str = Field(description="Error message for this field")
    type: str = Field(description="Error type classification")


class ErrorResponse(BaseModel):
    """
    Standardized error response for all API endpoints.

    Provides consistent error format across the service, supporting
    distributed tracing via correlation_id.

    Attributes:
        detail: Human-readable error description (no internal details)
        error_code: Machine-readable error code (UPPERCASE_WITH_UNDERSCORES)
        timestamp: ISO 8601 timestamp when error occurred
        correlation_id: Unique identifier for request tracing across services
        errors: Optional list of field-level validation errors

    Example:
        {
            "detail": "Request validation failed",
            "error_code": "VALIDATION_ERROR",
            "timestamp": "2025-12-04T14:30:45.123Z",
            "correlation_id": "req-550e8400-e29b-41d4-a716-446655440000",
            "errors": [
                {
                    "field": "email",
                    "message": "Invalid email format",
                    "type": "value_error"
                }
            ]
        }
    """

    detail: str = Field(description="Error description (no internal details)")
    error_code: str = Field(description="Machine-readable error code")
    timestamp: datetime = Field(description="Error timestamp (ISO 8601)")
    correlation_id: str = Field(description="Request correlation ID for tracing")
    errors: Optional[List[ValidationErrorDetail]] = Field(
        default=None, description="Field-level validation errors if applicable"
    )

    @field_serializer('timestamp')
    def serialize_timestamp(self, value: datetime) -> str:
        """Serialize timestamp to ISO 8601 format with Z suffix."""
        return value.isoformat().replace('+00:00', 'Z')

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "detail": "Request validation failed",
                "error_code": "VALIDATION_ERROR",
                "timestamp": "2025-12-04T14:30:45.123000Z",
                "correlation_id": "req-550e8400-e29b-41d4-a716-446655440000",
                "errors": [
                    {
                        "field": "email",
                        "message": "Invalid email format",
                        "type": "value_error",
                    }
                ],
            }
        }
