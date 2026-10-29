"""Tests for credential providers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time

from src.database.providers import (
    ConnectionStringProvider,
    ManagedIdentityProvider,
)


class TestConnectionStringProvider:
    """Tests for ConnectionStringProvider."""

    def test_init_with_valid_connection_string(self):
        """Test initialization with valid connection string."""
        conn_str = "Server=tcp:localhost;Database=test;uid=sa;pwd=pass"
        provider = ConnectionStringProvider(conn_str)
        assert provider.connection_string == conn_str

    def test_init_with_none_raises_error(self):
        """Test initialization with None raises ValueError."""
        with pytest.raises(ValueError, match="DB_CONNECTION_STRING not configured"):
            ConnectionStringProvider(None)

    def test_init_with_empty_string_raises_error(self):
        """Test initialization with empty string raises ValueError."""
        with pytest.raises(ValueError, match="DB_CONNECTION_STRING not configured"):
            ConnectionStringProvider("")

    @pytest.mark.asyncio
    async def test_get_connection_string(self):
        """Test getting connection string."""
        conn_str = "Server=tcp:localhost;Database=test"
        provider = ConnectionStringProvider(conn_str)
        result = await provider.get_connection_string()
        assert result == conn_str

    @pytest.mark.asyncio
    async def test_close(self):
        """Test close method (should be no-op)."""
        provider = ConnectionStringProvider("Server=tcp:localhost;Database=test")
        # Should not raise
        await provider.close()


class TestManagedIdentityProvider:
    """Tests for ManagedIdentityProvider."""

    def test_init_with_valid_parameters(self):
        """Test initialization with valid server and database."""
        with patch("src.database.providers.managed_identity.DefaultAzureCredential"):
            provider = ManagedIdentityProvider(
                server="test.database.windows.net",
                database="testdb"
            )
            assert provider.server == "test.database.windows.net"
            assert provider.database == "testdb"
            assert provider.client_id is None

    def test_init_with_user_assigned_identity(self):
        """Test initialization with user-assigned identity."""
        with patch("src.database.providers.managed_identity.DefaultAzureCredential"):
            provider = ManagedIdentityProvider(
                server="test.database.windows.net",
                database="testdb",
                client_id="12345678-1234-1234-1234-123456789012"
            )
            assert provider.client_id == "12345678-1234-1234-1234-123456789012"

    def test_init_with_none_server_raises_error(self):
        """Test initialization with None server raises ValueError."""
        with patch("src.database.providers.managed_identity.DefaultAzureCredential"):
            with pytest.raises(ValueError, match="server parameter cannot be None"):
                ManagedIdentityProvider(server=None, database="testdb")

    def test_init_with_none_database_raises_error(self):
        """Test initialization with None database raises ValueError."""
        with patch("src.database.providers.managed_identity.DefaultAzureCredential"):
            with pytest.raises(ValueError, match="database parameter cannot be None"):
                ManagedIdentityProvider(server="test.database.windows.net", database=None)

    @pytest.mark.asyncio
    async def test_get_connection_string_success(self):
        """Test successful token acquisition and connection string building."""
        mock_token = MagicMock()
        mock_token.token = "test_token_xyz_123"
        mock_token.expires_on = time.time() + 3600

        with patch("src.database.providers.managed_identity.DefaultAzureCredential") as mock_cred_class:
            mock_cred = MagicMock()
            mock_cred.get_token = MagicMock(return_value=mock_token)
            mock_cred_class.return_value = mock_cred

            provider = ManagedIdentityProvider(
                server="test.database.windows.net",
                database="testdb"
            )

            # Mock the async call
            with patch("asyncio.wait_for", new_callable=AsyncMock) as mock_wait_for:
                mock_wait_for.return_value = mock_token

                conn_str = await provider.get_connection_string()

                assert "test_token_xyz_123" in conn_str
                assert "test.database.windows.net" in conn_str
                assert "testdb" in conn_str
                assert "Encrypt=yes" in conn_str
                assert "TrustServerCertificate=no" in conn_str

    @pytest.mark.asyncio
    async def test_get_connection_string_uses_cached_token(self):
        """Test that valid cached token is reused."""
        mock_token = MagicMock()
        mock_token.token = "cached_token"
        mock_token.expires_on = time.time() + 3600

        with patch("src.database.providers.managed_identity.DefaultAzureCredential") as mock_cred_class:
            mock_cred = MagicMock()
            mock_cred.get_token = MagicMock(return_value=mock_token)
            mock_cred_class.return_value = mock_cred

            provider = ManagedIdentityProvider(
                server="test.database.windows.net",
                database="testdb"
            )

            # Manually set cache
            provider.token_cache = "cached_token"
            provider.token_expiry = time.time() + 3600

            with patch("asyncio.wait_for") as mock_wait_for:
                conn_str = await provider.get_connection_string()

                # Should NOT call wait_for since token is cached
                mock_wait_for.assert_not_called()
                assert "cached_token" in conn_str

    @pytest.mark.asyncio
    async def test_token_refresh_on_expiry(self):
        """Test that token is refreshed when close to expiry."""
        old_token = MagicMock()
        old_token.token = "old_token"
        old_token.expires_on = time.time() - 100  # Expired

        new_token = MagicMock()
        new_token.token = "new_token"
        new_token.expires_on = time.time() + 3600

        with patch("src.database.providers.managed_identity.DefaultAzureCredential") as mock_cred_class:
            mock_cred = MagicMock()
            mock_cred.get_token = MagicMock(return_value=new_token)
            mock_cred_class.return_value = mock_cred

            provider = ManagedIdentityProvider(
                server="test.database.windows.net",
                database="testdb"
            )

            # Set expired cache
            provider.token_cache = "old_token"
            provider.token_expiry = time.time() - 100

            with patch("asyncio.wait_for", new_callable=AsyncMock) as mock_wait_for:
                mock_wait_for.return_value = new_token

                conn_str = await provider.get_connection_string()

                # Should call wait_for to get new token
                mock_wait_for.assert_called_once()
                assert "new_token" in conn_str

    @pytest.mark.asyncio
    async def test_get_connection_string_timeout(self):
        """Test timeout during token acquisition."""
        import asyncio

        with patch("src.database.providers.managed_identity.DefaultAzureCredential"):
            provider = ManagedIdentityProvider(
                server="test.database.windows.net",
                database="testdb"
            )

            with patch("asyncio.wait_for", new_callable=AsyncMock) as mock_wait_for:
                mock_wait_for.side_effect = asyncio.TimeoutError()

                with pytest.raises(TimeoutError, match="Timeout acquiring MSI token"):
                    await provider.get_connection_string()

    @pytest.mark.asyncio
    async def test_get_connection_string_auth_error(self):
        """Test authentication error during token acquisition."""
        from azure.core.exceptions import ClientAuthenticationError

        with patch("src.database.providers.managed_identity.DefaultAzureCredential"):
            provider = ManagedIdentityProvider(
                server="test.database.windows.net",
                database="testdb"
            )

            with patch("asyncio.wait_for", new_callable=AsyncMock) as mock_wait_for:
                mock_wait_for.side_effect = ClientAuthenticationError("Auth failed")

                with pytest.raises(ClientAuthenticationError, match="Failed to acquire MSI token"):
                    await provider.get_connection_string()

    def test_token_expired_returns_true_when_expired(self):
        """Test _token_expired returns True for expired token."""
        with patch("src.database.providers.managed_identity.DefaultAzureCredential"):
            provider = ManagedIdentityProvider(
                server="test.database.windows.net",
                database="testdb"
            )
            provider.token_expiry = time.time() - 100  # Expired
            assert provider._token_expired(buffer_seconds=0) is True

    def test_token_expired_returns_true_with_buffer(self):
        """Test _token_expired returns True when within buffer."""
        with patch("src.database.providers.managed_identity.DefaultAzureCredential"):
            provider = ManagedIdentityProvider(
                server="test.database.windows.net",
                database="testdb"
            )
            provider.token_expiry = time.time() + 100  # Expires in 100 seconds
            assert provider._token_expired(buffer_seconds=300) is True  # 300s buffer

    def test_token_expired_returns_false_when_valid(self):
        """Test _token_expired returns False for valid token."""
        with patch("src.database.providers.managed_identity.DefaultAzureCredential"):
            provider = ManagedIdentityProvider(
                server="test.database.windows.net",
                database="testdb"
            )
            provider.token_expiry = time.time() + 3600  # Valid for 1 hour
            assert provider._token_expired(buffer_seconds=300) is False

    def test_token_expired_returns_true_when_none(self):
        """Test _token_expired returns True when token_expiry is None."""
        with patch("src.database.providers.managed_identity.DefaultAzureCredential"):
            provider = ManagedIdentityProvider(
                server="test.database.windows.net",
                database="testdb"
            )
            provider.token_expiry = None
            assert provider._token_expired() is True

    @pytest.mark.asyncio
    async def test_close(self):
        """Test close method."""
        with patch("src.database.providers.managed_identity.DefaultAzureCredential") as mock_cred_class:
            mock_cred = MagicMock()
            mock_cred.close = MagicMock()
            mock_cred_class.return_value = mock_cred

            provider = ManagedIdentityProvider(
                server="test.database.windows.net",
                database="testdb"
            )
            await provider.close()

            mock_cred.close.assert_called_once()
