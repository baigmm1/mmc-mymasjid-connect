"""Database configuration and initialization."""

from .engine import DatabaseEngine
from .session import SessionFactory
from .providers import (
    CredentialProvider,
    ConnectionStringProvider,
    ManagedIdentityProvider,
)

# Phase 2: New models (stubs - do not affect masterdata models)
from .models.base import Base, BaseModel
from .models.organization import Organization
from .models.user import User
from .models.audit_log import AuditLog
from .models.company import Company
from .models.donation_type import DonationType

# Phase 3: Health check utilities
from .health import DatabaseHealth
from src.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__, level=settings.LOG_LEVEL)

# Global singleton instances
_engine = None
_session_factory = None


async def get_engine():
    """Get or create the global database engine.
    
    Returns:
        AsyncEngine: The global async database engine instance.
        
    Raises:
        ValueError: If unable to initialize engine with current configuration.
    """
    global _engine
    if _engine is None:
        from src.config import settings
        
        if settings.DB_CONNECTION_STRING:
            # Development mode - use connection string provider
            logger.info("Using connection string provider for development mode")
            provider = ConnectionStringProvider(settings.DB_CONNECTION_STRING)
        else:
            # Production mode - use Managed Identity provider
            logger.info(f"DB_CONNECTION_STRING not set, using Managed Identity provider using server: {settings.DB_SERVER}, database: {settings.DB_NAME} and client_id: {settings.DB_IDENTITY_CLIENT_ID}")
            
            provider = ManagedIdentityProvider(
                server=settings.DB_SERVER,
                database=settings.DB_NAME,
                client_id=settings.DB_IDENTITY_CLIENT_ID,
            )
        
        conn_string = await provider.get_connection_string()
        
        # Create DatabaseEngine wrapper and get actual AsyncEngine
        engine_factory = DatabaseEngine(
            conn_string,
            echo=settings.DB_ECHO_SQL,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_recycle=settings.DB_POOL_RECYCLE,
            connect_timeout=settings.DB_CONNECT_TIMEOUT,
        )
        _engine = await engine_factory.create_engine()
    return _engine


def get_session_factory(engine) -> SessionFactory:
    """Get or create the session factory.
    
    Args:
        engine: The AsyncEngine to use for sessions.
        
    Returns:
        SessionFactory: The session factory instance.
    """
    global _session_factory
    if _session_factory is None:
        _session_factory = SessionFactory(engine)
    return _session_factory


async def get_session():
    """Get a database session for dependency injection.
    
    This is designed to be used as a FastAPI Depends() argument.
    
    Usage:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session)):
            ...
    
    Yields:
        AsyncSession: A database session.
    """
    engine = await get_engine()
    factory = get_session_factory(engine)
    async for session in factory.get_session():
        yield session


__all__ = [
    # Engine and Session
    "DatabaseEngine",
    "SessionFactory",
    "get_engine",
    "get_session_factory",
    "get_session",
    # Providers
    "CredentialProvider",
    "ConnectionStringProvider",
    "ManagedIdentityProvider",
    # Phase 2 Models (stubs)
    "Base",
    "BaseModel",
    "Organization",
    "User",
    "AuditLog",
    "Company",
    "DonationType",
    # Phase 3: Health utilities
    "DatabaseHealth",
]
