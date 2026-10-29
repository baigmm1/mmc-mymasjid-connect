"""
Database health check utilities.

Provides health check queries and connection pool monitoring for database status.
"""

import time
from typing import Dict, Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine

from src.core.logging import get_logger
from src.config import settings
from src.database.models.company import Company

logger = get_logger(__name__, level=settings.LOG_LEVEL)


class DatabaseHealth:
    """Database health check utilities."""

    @staticmethod
    async def check_connection(session: AsyncSession, timeout: int = 5) -> Dict[str, Any]:
        """
        Check database connectivity with latency measurement.

        Args:
            session: AsyncSession for database query
            timeout: Query timeout in seconds (default 5)

        Returns:
            Dict with status, latency, and optional error information

        Example:
            {
                "status": "connected",
                "latency_ms": 15.3
            }
        """
        try:
            start_time = time.time()

            # Query Company table to verify actual database access
            query = select(Company).limit(1)
            result = await session.execute(query)
            result.scalar_one_or_none()

            latency_ms = round((time.time() - start_time) * 1000, 2)

            logger.debug(f"Database health check passed (latency: {latency_ms}ms)")

            return {
                "status": "connected",
                "latency_ms": latency_ms
            }

        except Exception as e:
            logger.error(
                f"Database health check failed: {str(e)}",
                extra={"error": str(e), "error_type": type(e).__name__},
                exc_info=True
            )
            return {
                "status": "disconnected",
                "error": "Database connection unavailable"
            }

    @staticmethod
    def get_pool_info(engine: AsyncEngine) -> Dict[str, Any]:
        """
        Get connection pool statistics.

        Args:
            engine: AsyncEngine instance

        Returns:
            Dict with pool size, active connections, and idle connections

        Example:
            {
                "size": 10,
                "checked_out": 3,
                "checked_in": 7,
                "overflow": 0
            }
        """
        try:
            pool = engine.pool

            return {
                "size": pool.size(),
                "checked_out": pool.checkedout(),
                "checked_in": pool.checkedin(),
                "overflow": pool.overflow(),
                "status": "healthy" if pool.checkedin() > 0 else "degraded"
            }
        except Exception as e:
            logger.error(
                f"Failed to get pool info: {str(e)}",
                extra={"error": str(e), "error_type": type(e).__name__}
            )
            return {
                "status": "unknown",
                "error": "Unable to retrieve pool information"
            }

    @staticmethod
    async def check_query_performance(session: AsyncSession, query: str = "SELECT GETDATE()") -> Dict[str, Any]:
        """
        Test query performance with a simple query.

        Args:
            session: AsyncSession for database query
            query: SQL query to execute (default: SELECT GETDATE())

        Returns:
            Dict with query timing and result status

        Example:
            {
                "status": "ok",
                "execution_time_ms": 5.2
            }
        """
        try:
            start_time = time.time()

            result = await session.execute(text(query))
            result.fetchone()

            execution_time_ms = round((time.time() - start_time) * 1000, 2)

            return {
                "status": "ok",
                "execution_time_ms": execution_time_ms
            }
        except Exception as e:
            logger.error(
                f"Query performance test failed: {str(e)}",
                extra={"error": str(e), "error_type": type(e).__name__}
            )
            return {
                "status": "error",
                "error": "Query execution failed"
            }
