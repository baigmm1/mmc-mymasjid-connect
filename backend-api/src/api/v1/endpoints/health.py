"""
Health check endpoint for application liveness and readiness probes.

The health endpoint is used by container orchestration systems (Kubernetes)
and load balancers to determine if the application is ready to serve requests.

Endpoint: GET /api/v1/health
Returns: HealthStatus with status (ok/degraded/unhealthy), timestamp, version, environment
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_engine, get_session, DatabaseHealth
from src.models.health import HealthStatus, DetailedHealthStatus, DatabaseStatus
from src.core.cache_manager import get_cache_stats

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthStatus,
    status_code=200,
    responses={
        200: {
            "description": "Backend API Application is healthy",
            "model": HealthStatus,
        }
    },
)
async def get_health() -> HealthStatus:
    """
    Get application health status.

    Returns current health status for Kubernetes probes and load balancers.
    This endpoint is intentionally simple and fast to minimize probe overhead.

    Returns:
        HealthStatus: Current health status with timestamp, version, and environment

    Example:
        GET /api/v1/health
        Response 200:
        {
            "application": "Masjid Connect API",
            "status": "ok",
            "timestamp": "2025-12-04T14:30:45.123Z",
            "version": "1.0.0",
            "environment": "development"
        }
    """
    return HealthStatus(
        application=settings.APP_NAME,
        status="ok",
        timestamp=datetime.now(timezone.utc),
        version=settings.API_VERSION,
        environment=settings.ENVIRONMENT,
        email_enabled=settings.SEND_EMAILS,
        cors_origins=settings.CORS_ORIGINS
    )


# Phase 3: Database health check endpoint

@router.get(
    "/health/db",
    response_model=DetailedHealthStatus,
    responses={
        200: {
            "description": "Application and database are healthy",
            "model": DetailedHealthStatus,
        },
        503: {
            "description": "Database is unavailable or degraded",
            "model": DetailedHealthStatus,
        }
    },
)
async def get_health_database(
    session: AsyncSession = Depends(get_session)
) -> DetailedHealthStatus:
    """
    Get detailed application health status including database connectivity.

    Performs a database connectivity check and returns detailed health information
    including connection pool statistics and query latency.

    Returns:
        DetailedHealthStatus: Comprehensive health status with database information

    Status Codes:
        200: Application and database are healthy
        503: Database is unavailable or degraded

    Example:
        GET /api/v1/health/db
        Response 200:
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
    # Check database connection
    db_health = await DatabaseHealth.check_connection(session)

    # Get connection pool info
    try:
        engine = await get_engine()
        pool_info = DatabaseHealth.get_pool_info(engine)
    except Exception:
        pool_info = {"status": "unknown"}

    # Build database status
    db_status = DatabaseStatus(
        status=db_health.get("status", "unknown"),
        latency_ms=db_health.get("latency_ms"),
        pool_size=pool_info.get("size"),
        active_connections=pool_info.get("checked_out"),
        idle_connections=pool_info.get("checked_in")
    )

    # Determine overall status
    if db_status.status == "connected":
        overall_status = "ok"
        status_code = http_status.HTTP_200_OK
        cache_stats = get_cache_stats()
    elif db_status.status == "degraded":
        overall_status = "degraded"
        status_code = http_status.HTTP_503_SERVICE_UNAVAILABLE
        cache_stats = None
    else:
        overall_status = "unhealthy"
        status_code = http_status.HTTP_503_SERVICE_UNAVAILABLE
        cache_stats = None
        
    return DetailedHealthStatus(
        application=settings.APP_NAME,
        status=overall_status,
        timestamp=datetime.now(timezone.utc),
        version=settings.API_VERSION,
        environment=settings.ENVIRONMENT,
        email_enabled=settings.SEND_EMAILS,
        cors_origins=settings.CORS_ORIGINS,
        database=db_status,
        cache_stats=cache_stats
    )
