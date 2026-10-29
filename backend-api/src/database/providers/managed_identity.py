"""Managed Identity provider for Azure production environments."""

import asyncio
import time
from typing import Optional

from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ClientAuthenticationError

from src.core.logging import get_logger
from src.config import settings

from .base import CredentialProvider

logger = get_logger(__name__, level=settings.LOG_LEVEL)


class ManagedIdentityProvider(CredentialProvider):
    """
    Provides connection string using Azure Managed Identity.

    Acquires tokens from Azure metadata service and builds connection
    strings with token-based authentication. Used in production on Azure App Service.
    """

    def __init__(
        self,
        server: str,
        database: str,
        client_id: Optional[str] = None,
    ):
        """
        Initialize with server details.

        Args:
            server: SQL Database server name (e.g., 'myserver.database.windows.net')
            database: Database name (e.g., 'masjiddb')
            client_id: Optional user-assigned identity client ID

        Raises:
            ValueError: If server or database is None/empty
        """
        if not server:
            raise ValueError("server parameter cannot be None or empty")
        if not database:
            raise ValueError("database parameter cannot be None or empty")

        self.server = server
        self.database = database
        self.client_id = client_id
        self.credential = DefaultAzureCredential(
            managed_identity_client_id=client_id
        )
        self.token_cache = None
        self.token_expiry = None
        
        logger.info(
            "Managed Identity provider initialized",
            extra={
                "server": server,
                "database": database,
                "has_client_id": client_id is not None
            }
        )

    async def get_connection_string(self) -> str:
        """
        Get connection string with current MSI token.

        Acquires token from metadata service and builds connection string.
        Handles token refresh automatically with caching.

        Returns:
            str: Connection string with MSI token as password

        Raises:
            ClientAuthenticationError: If unable to acquire token from metadata service
            TimeoutError: If metadata service doesn't respond within 10 seconds
        """
        logger.debug("Building connection string with Managed Identity authentication")
        
        # Build connection string with ActiveDirectoryMsi authentication
        # Note: For Managed Identity, use Authentication=ActiveDirectoryMsi
        # The ODBC driver handles token acquisition automatically
        conn_str = (
            f"Driver={{ODBC Driver 18 for SQL Server}};"
            f"Server=tcp:{self.server},1433;"
            f"Database={self.database};"
            f"Authentication=ActiveDirectoryMsi;"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
            f"MARS_Connection=yes;"
        )
        
        # If a specific client ID is provided, add it to the connection string
        if self.client_id:
            conn_str += f"UID={self.client_id};"
            logger.debug(f"Using user-assigned managed identity with client ID")
        else:
            logger.debug("Using system-assigned managed identity")
        
        return conn_str

    async def _get_token(self) -> str:
        """
        Get MSI token with caching and refresh.

        Returns:
            str: Access token for Azure SQL Database

        Raises:
            ClientAuthenticationError: If unable to acquire token
            TimeoutError: If token request times out
        """
        # Check if cached token is still valid (with 5-minute buffer)
        if self.token_cache and not self._token_expired(buffer_seconds=300):
            logger.debug("Using cached MSI token")
            return self.token_cache

        try:
            logger.info("Requesting new MSI token from metadata service...")
            # Request new token from MSI endpoint with timeout
            token_response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.credential.get_token,
                    "https://database.windows.net/.default",
                ),
                timeout=10.0,
            )

            self.token_cache = token_response.token
            self.token_expiry = token_response.expires_on
            logger.info(
                "MSI token acquired successfully",
                extra={"expires_at": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.token_expiry))}
            )
            return self.token_cache

        except asyncio.TimeoutError:
            logger.error("Timeout acquiring MSI token from metadata service (10s)")
            raise TimeoutError(
                "Timeout acquiring MSI token from metadata service (10s). "
                "Verify App Service has Managed Identity enabled."
            )
        except ClientAuthenticationError as e:
            logger.error(
                f"Failed to acquire MSI token: {str(e)}",
                extra={"error": str(e), "error_type": type(e).__name__},
                exc_info=True
            )
            raise ClientAuthenticationError(
                f"Failed to acquire MSI token: {str(e)}. "
                "Verify App Service Managed Identity is enabled and properly configured."
            ) from e

    def _token_expired(self, buffer_seconds: int = 300) -> bool:
        """
        Check if token has expired (with buffer).

        Args:
            buffer_seconds: Number of seconds before actual expiry to consider expired.
                          Default 300 (5 minutes) for preemptive refresh.

        Returns:
            bool: True if token is expired or close to expiry
        """
        if self.token_expiry is None:
            return True
        return time.time() > (self.token_expiry - buffer_seconds)

    async def close(self):
        """Close credential provider and cleanup resources."""
        logger.info("Closing managed identity credential provider")
        self.credential.close()
        logger.debug("Managed identity credential provider closed")
