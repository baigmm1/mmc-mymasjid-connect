"""Abstract base class for database credential providers."""

from abc import ABC, abstractmethod


class CredentialProvider(ABC):
    """
    Abstract base class for credential/connection string providers.

    Implementations provide connection strings using different authentication
    methods (connection string or Managed Identity).
    """

    @abstractmethod
    async def get_connection_string(self) -> str:
        """
        Get a valid connection string for Azure SQL Database.

        Returns:
            str: A connection string ready for SQLAlchemy to use.

        Raises:
            ValueError: If credentials are not configured.
            Exception: If unable to acquire credentials.
        """
        pass

    @abstractmethod
    async def close(self):
        """
        Clean up any resources held by the provider.

        This should be called during application shutdown.
        """
        pass
