"""SQLAlchemy AsyncEngine factory for database connections."""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from src.core.logging import get_logger
from src.config import settings

logger = get_logger(__name__, level=settings.LOG_LEVEL)


class DatabaseEngine:
    """
    Factory for creating SQLAlchemy AsyncEngine with aioodbc.

    Manages connection pool configuration and engine lifecycle.
    Uses aioodbc (async ODBC driver) for async SQL Server operations.
    """

    def __init__(
        self,
        connection_string: str,
        echo: bool = False,
        pool_size: int = 10,
        max_overflow: int = 10,
        pool_recycle: int = 300,
        connect_timeout: int = 30,
    ):
        """
        Initialize engine factory with configuration.

        Args:
            connection_string: Connection string for SQL Server
            echo: Log all SQL statements (for debugging)
            pool_size: Minimum connections to maintain
            max_overflow: Additional connections beyond pool_size
            pool_recycle: Recycle connections after N seconds
            connect_timeout: Connection timeout in seconds
        """
        self.connection_string = connection_string
        self.echo = echo
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_recycle = pool_recycle
        self.connect_timeout = connect_timeout
        
        logger.info(
            "Database engine factory initialized",
            extra={
                "pool_size": pool_size,
                "max_overflow": max_overflow,
                "pool_recycle": pool_recycle,
                "connect_timeout": connect_timeout,
                "echo": echo
            }
        )

    async def create_engine(self) -> AsyncEngine:
        """
        Create and return configured AsyncEngine.

        Returns:
            AsyncEngine: Ready to use async SQLAlchemy engine

        Raises:
            sqlalchemy.exc.ArgumentError: If connection string invalid
            sqlalchemy.exc.OperationalError: If initial connection fails
        """
        try:
            logger.info("Creating database engine...")
            
            # Create async engine with aioodbc driver (async version of pyodbc)
            engine = create_async_engine(
                f"mssql+aioodbc:///?odbc_connect={self.connection_string}",
                echo=self.echo,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_recycle=self.pool_recycle,
                pool_pre_ping=True,  # Test connections before using
                connect_args={"timeout": self.connect_timeout},
            )
            
            logger.info("Database engine created successfully")
            return engine
            
        except Exception as e:
            logger.error(
                f"Failed to create database engine: {str(e)}",
                extra={"error": str(e), "error_type": type(e).__name__},
                exc_info=True
            )
            raise
