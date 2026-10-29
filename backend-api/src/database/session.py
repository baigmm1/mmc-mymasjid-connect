"""AsyncSession factory for dependency injection and lifecycle management."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.core.logging import get_logger
from src.config import settings

logger = get_logger(__name__, level=settings.LOG_LEVEL)


class SessionFactory:
    """
    Factory for creating AsyncSession instances.

    Handles session lifecycle, transaction management, and error handling.
    """

    def __init__(self, engine: AsyncEngine):
        """
        Initialize with AsyncEngine.

        Args:
            engine: SQLAlchemy AsyncEngine instance
        """
        self.engine = engine
        self.async_session = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        logger.info("Session factory initialized")

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an AsyncSession for dependency injection.

        Yields:
            AsyncSession: Active database session

        Notes:
            - Must be used with async context manager or dependency injection
            - Automatically rolls back on exception
            - Ensures cleanup (close) in all cases

        Usage:
            async def endpoint(session: AsyncSession = Depends(get_db_session)):
                result = await session.execute(select(...))
                return result.scalars().all()
        """
        async with self.async_session() as session:
            try:
                logger.debug("Database session created")
                yield session
                logger.debug("Database session completed successfully")
            except Exception as e:
                logger.error(
                    f"Database session error, rolling back: {str(e)}",
                    extra={"error": str(e), "error_type": type(e).__name__},
                    exc_info=True
                )
                await session.rollback()
                raise
            finally:
                await session.close()
                logger.debug("Database session closed")

    async def close(self):
        """
        Close engine and dispose all connections.

        Must be called during application shutdown.
        """
        logger.info("Disposing database engine...")
        await self.engine.dispose()
        logger.info("Database engine disposed successfully")
