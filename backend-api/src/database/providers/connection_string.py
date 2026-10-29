"""Connection string provider for development environments."""

from src.core.logging import get_logger
from src.config import settings

from .base import CredentialProvider

logger = get_logger(__name__, level=settings.LOG_LEVEL)


class ConnectionStringProvider(CredentialProvider):
    """
    Provides connection string from environment variables.

    Used in development environments where connection strings are stored in .env files.
    """

    def __init__(self, connection_string: str):
        """
        Initialize with connection string.

        Args:
            connection_string: Connection string from DB_CONNECTION_STRING env var

        Raises:
            ValueError: If connection_string is None or empty
        """
        if not connection_string:
            logger.error("DB_CONNECTION_STRING not configured")
            raise ValueError(
                "DB_CONNECTION_STRING not configured. "
                "Set DB_CONNECTION_STRING environment variable for development mode."
            )
        self.connection_string = connection_string
        logger.info("Connection string provider initialized (development mode)")

    async def get_connection_string(self) -> str:
        """
        Return the configured connection string.

        Returns:
            str: Connection string (unchanged from initialization)

        Examples:
            "Server=tcp:localhost;Database=masjiddb;uid=sa;pwd=Password123!"
        """
        logger.debug("Retrieving connection string from environment")
        return self.connection_string

    async def close(self):
        """No-op for connection string provider."""
        pass
