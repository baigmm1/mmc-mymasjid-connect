"""
Health status models for application health checks.

The HealthStatus model represents the current state of the application,
useful for liveness and readiness probes in Kubernetes and load balancers.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_serializer


class HealthStatus(BaseModel):
    """
    Health status response model.

    Represents the current health state of the application.

    Attributes:
        application: Name of the application
        status: Current health status (ok, degraded, unhealthy)
        timestamp: ISO 8601 timestamp of the status check
        version: Application semantic version
        environment: Current deployment environment (development, testing, production)

    Example:
        {
            "application": "Masjid Connect API",
            "status": "ok",
            "timestamp": "2025-12-04T14:30:45.123Z",
            "version": "1.0.0",
            "environment": "development"
        }
    """
    application: str = Field(description="Application name")
    status: Literal["ok", "degraded", "unhealthy"] = Field(
        default="ok", description="Current health status"
    )
    timestamp: datetime = Field(description="Time of health check (ISO 8601)")
    version: Optional[str] = Field(default=None, description="Application version")
    environment: Optional[str] = Field(
        default=None, description="Current environment (development/testing/production)"
    )
    email_enabled: Optional[bool] = Field(
        default=None, description="Indicates if email sending is enabled"   
    )
    cors_origins: Optional[list[str]] = Field(  
        default=None, description="List of allowed CORS origins"   
    )

    @field_serializer('timestamp')
    def serialize_timestamp(self, value: datetime) -> str:
        """Serialize timestamp to ISO 8601 format with Z suffix."""
        return value.isoformat().replace('+00:00', 'Z')


# Phase 3: Enhanced health status with database information

class DatabaseStatus(BaseModel):
    """
    Database health status information.

    Attributes:
        status: Connection status (connected, disconnected, degraded)
        latency_ms: Query latency in milliseconds (if connected)
        pool_size: Connection pool size
        active_connections: Number of active connections
        idle_connections: Number of idle connections
    """
    status: Literal["connected", "disconnected", "degraded", "unknown"] = Field(
        description="Database connection status"
    )
    latency_ms: Optional[float] = Field(None, description="Query latency in milliseconds")
    pool_size: Optional[int] = Field(None, description="Connection pool size")
    active_connections: Optional[int] = Field(None, alias="activeConnections", description="Active connections")
    idle_connections: Optional[int] = Field(None, alias="idleConnections", description="Idle connections")

    model_config = {"from_attributes": True, "populate_by_name": True}


class DetailedHealthStatus(BaseModel):
    """
    Detailed health status response with database information.

    Extends basic health status with database connectivity details.

    Attributes:
        application: Name of the application
        status: Overall health status (ok, degraded, unhealthy)
        timestamp: ISO 8601 timestamp of the status check
        version: Application semantic version
        environment: Current deployment environment
        database: Database health status information

    Example:
        {
            "application": "Masjid Connect API",
            "status": "ok",
            "timestamp": "2025-12-09T20:45:00.123Z",
            "version": "1.0.0",
            "environment": "development",
            "database": {
                "status": "connected",
                "latency_ms": 15.3,
                "pool_size": 10,
                "activeConnections": 2,
                "idleConnections": 8
            }
        }
    """
    application: str = Field(description="Application name")
    status: Literal["ok", "degraded", "unhealthy"] = Field(
        description="Overall health status"
    )
    timestamp: datetime = Field(description="Time of health check (ISO 8601)")
    version: Optional[str] = Field(None, description="Application version")
    environment: Optional[str] = Field(None, description="Current environment")
    email_enabled: Optional[bool] = Field(
        default=None, description="Indicates if email sending is enabled"   
    )
    cors_origins: Optional[list[str]] = Field(  
        default=None, description="List of allowed CORS origins"   
    )
    database: DatabaseStatus = Field(description="Database health status")
    
    cache_stats: Optional[dict] = Field(
        default=None, description="Cache statistics information"
    )

    @field_serializer('timestamp')
    def serialize_timestamp(self, value: datetime) -> str:
        """Serialize timestamp to ISO 8601 format with Z suffix."""
        return value.isoformat().replace('+00:00', 'Z')

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "application": "Masjid Connect API",
                "status": "ok",
                "timestamp": "2025-12-04T14:30:45.123000Z",
                "version": "1.0.0",
                "environment": "development",
            }
        }
