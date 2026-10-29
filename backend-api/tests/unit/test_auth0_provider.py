"""
Unit tests for Auth0 Provider

Tests the Auth0Provider class for fetching user information.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from src.providers.auth0_provider import Auth0Provider, get_auth0_provider


@pytest.fixture
def auth0_provider():
    """Create an Auth0Provider instance for testing"""
    return Auth0Provider(domain="masjidconnect.auth0.com")


@pytest.fixture
def mock_user_info():
    """Sample user info response from Auth0"""
    return {
        "sub": "auth0|1234567890",
        "name": "John Doe",
        "email": "john.doe@example.com",
        "email_verified": True,
        "picture": "https://example.com/photo.jpg",
        "updated_at": "2024-01-15T10:30:00.000Z",
        "https://masjidconnect.auth0.com/roles": ["user", "donor"]
    }


@pytest.mark.asyncio
async def test_get_user_info_success(auth0_provider, mock_user_info):
    """Test successful user info retrieval"""
    
    with patch("httpx.AsyncClient") as mock_client:
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_user_info
        mock_response.raise_for_status = MagicMock()
        
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        
        # Call method
        access_token = "valid_token_123"
        result = await auth0_provider.get_user_info(access_token)
        
        # Assertions
        assert result == mock_user_info
        assert result["sub"] == "auth0|1234567890"
        assert result["email"] == "john.doe@example.com"


@pytest.mark.asyncio
async def test_get_user_info_missing_token(auth0_provider):
    """Test error when access token is missing"""
    
    with pytest.raises(ValueError, match="Access token is required"):
        await auth0_provider.get_user_info("")


@pytest.mark.asyncio
async def test_get_user_info_http_error(auth0_provider):
    """Test handling of HTTP errors"""
    
    with patch("httpx.AsyncClient") as mock_client:
        # Setup mock to raise HTTP error
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )
        
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )
        
        # Call method and expect exception
        with pytest.raises(httpx.HTTPStatusError):
            await auth0_provider.get_user_info("invalid_token")


@pytest.mark.asyncio
async def test_get_user_info_network_error(auth0_provider):
    """Test handling of network errors"""
    
    with patch("httpx.AsyncClient") as mock_client:
        # Setup mock to raise network error
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.RequestError("Network error")
        )
        
        # Call method and expect exception
        with pytest.raises(httpx.RequestError):
            await auth0_provider.get_user_info("valid_token")


@pytest.mark.asyncio
async def test_get_user_email_success(auth0_provider, mock_user_info):
    """Test successful email retrieval"""
    
    with patch.object(auth0_provider, "get_user_info", return_value=mock_user_info):
        email = await auth0_provider.get_user_email("valid_token")
        assert email == "john.doe@example.com"


@pytest.mark.asyncio
async def test_get_user_email_error(auth0_provider):
    """Test email retrieval when get_user_info fails"""
    
    with patch.object(
        auth0_provider, 
        "get_user_info", 
        side_effect=Exception("API error")
    ):
        email = await auth0_provider.get_user_email("valid_token")
        assert email is None


@pytest.mark.asyncio
async def test_get_user_profile_success(auth0_provider, mock_user_info):
    """Test successful profile retrieval"""
    
    with patch.object(auth0_provider, "get_user_info", return_value=mock_user_info):
        profile = await auth0_provider.get_user_profile("valid_token")
        
        assert profile["user_id"] == "auth0|1234567890"
        assert profile["email"] == "john.doe@example.com"
        assert profile["name"] == "John Doe"
        assert profile["email_verified"] is True
        assert profile["picture"] == "https://example.com/photo.jpg"


@pytest.mark.asyncio
async def test_get_user_profile_error(auth0_provider):
    """Test profile retrieval when get_user_info fails"""
    
    with patch.object(
        auth0_provider, 
        "get_user_info", 
        side_effect=Exception("API error")
    ):
        with pytest.raises(Exception, match="API error"):
            await auth0_provider.get_user_profile("valid_token")


def test_auth0_provider_initialization():
    """Test Auth0Provider initialization"""
    
    provider = Auth0Provider(domain="test.auth0.com")
    
    assert provider.domain == "test.auth0.com"
    assert provider.userinfo_url == "https://test.auth0.com/userinfo"


def test_get_auth0_provider_factory():
    """Test factory function for creating Auth0Provider"""
    
    with patch("src.providers.auth0_provider.settings") as mock_settings:
        mock_settings.AUTH0_DOMAIN = "masjidconnect.auth0.com"
        
        provider = get_auth0_provider()
        
        assert isinstance(provider, Auth0Provider)
        assert provider.domain == "masjidconnect.auth0.com"


def test_get_auth0_provider_missing_domain():
    """Test factory function raises error when domain is not configured"""
    
    with patch("src.providers.auth0_provider.settings") as mock_settings:
        mock_settings.AUTH0_DOMAIN = None
        
        with pytest.raises(ValueError, match="AUTH0_DOMAIN must be configured"):
            get_auth0_provider()


@pytest.mark.asyncio
async def test_userinfo_request_headers(auth0_provider, mock_user_info):
    """Test that correct headers are sent in the request"""
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.json.return_value = mock_user_info
        mock_response.raise_for_status = MagicMock()
        
        mock_get = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.get = mock_get
        
        # Call method
        access_token = "test_token_abc123"
        await auth0_provider.get_user_info(access_token)
        
        # Verify correct headers were used
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        
        assert call_args[1]["headers"]["Authorization"] == f"Bearer {access_token}"
        assert call_args[1]["headers"]["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_userinfo_url_construction(auth0_provider):
    """Test that the userinfo URL is correctly constructed"""
    
    assert auth0_provider.userinfo_url == "https://masjidconnect.auth0.com/userinfo"
    
    # Test with different domain
    provider2 = Auth0Provider(domain="custom.auth0.com")
    assert provider2.userinfo_url == "https://custom.auth0.com/userinfo"
