"""
Unit tests for Stripe HTTP Provider.

Tests verify direct HTTP API calls to Stripe endpoints without using the SDK.

Test markers:
- @pytest.mark.unit: Unit test (isolated component testing)
"""

from unittest.mock import AsyncMock, patch
from datetime import datetime
import pytest
import httpx

from src.providers.stripe_http_provider import StripeHTTPProvider, create_stripe_http_provider
from src.providers.stripe_provider_factory import (
    create_stripe_provider, 
    create_stripe_sdk_provider,
    create_stripe_http_provider as factory_create_http,
    ProviderType
)
from src.models.stripe.subscription import SubscriptionModel


@pytest.mark.unit
class TestStripeHTTPProvider:
    """Unit tests for Stripe HTTP provider."""

    @pytest.fixture
    def mock_subscription_data(self):
        """Sample Stripe subscription data from HTTP API."""
        return {
            "id": "sub_test_123",
            "object": "subscription",
            "customer": "cus_test_456",
            "created": 1640995200,  # Jan 1, 2022
            "status": "active",
            "cancel_at": 1707320190,  # Feb 8, 2024
            "default_payment_method": {
                "id": "pm_test_789",
                "type": "card"
            },
            "latest_invoice": {
                "id": "in_test_101",
                "payment_intent": {
                    "id": "pi_test_202"
                }
            }
        }

    @pytest.fixture
    def http_provider(self):
        """Create HTTP provider for testing."""
        return StripeHTTPProvider("sk_test_fake_key")

    @pytest.mark.asyncio
    async def test_get_subscription_success(self, http_provider, mock_subscription_data):
        """Test successful subscription retrieval via HTTP API."""
        with patch.object(http_provider.client, 'get') as mock_get:
            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_subscription_data
            mock_response.content = b'{"test": "data"}'
            mock_get.return_value = mock_response

            result = await http_provider.get_subscription("sub_test_123")

            assert result == mock_subscription_data
            mock_get.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_get_subscription_as_model(self, http_provider, mock_subscription_data):
        """Test subscription retrieval and conversion to SubscriptionModel."""
        with patch.object(http_provider, 'get_subscription') as mock_get_sub:
            mock_get_sub.return_value = mock_subscription_data

            result = await http_provider.get_subscription_as_model("sub_test_123")

            assert isinstance(result, SubscriptionModel)
            assert result.id == "sub_test_123"
            assert result.customer == "cus_test_456"
            assert result.created == 1640995200
            assert result.created_datetime is not None
            assert result.cancel_at_datetime is not None
            assert result.payment_method_desc == "pm_test_789"
            assert result.latest_invoice_id == "in_test_101"
            assert result.payment_intent_id == "pi_test_202"

    @pytest.mark.asyncio
    async def test_get_subscription_http_error(self, http_provider):
        """Test handling of HTTP errors from Stripe API."""
        with patch.object(http_provider.client, 'get') as mock_get:
            # Mock error response
            mock_response = AsyncMock()
            mock_response.status_code = 404
            mock_response.json.return_value = {
                "error": {
                    "type": "invalid_request_error",
                    "code": "resource_missing",
                    "message": "No such subscription: sub_invalid"
                }
            }
            mock_response.text = "Error response text"
            mock_get.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                await http_provider.get_subscription("sub_invalid")
            
            assert "No such subscription" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_subscription_network_error(self, http_provider):
        """Test handling of network errors."""
        with patch.object(http_provider.client, 'get') as mock_get:
            mock_get.side_effect = httpx.RequestError("Connection failed")

            with pytest.raises(Exception) as exc_info:
                await http_provider.get_subscription("sub_test_123")
            
            assert "Network error" in str(exc_info.value)

    def test_extract_payment_method_id_string(self, http_provider):
        """Test extracting payment method ID when it's a string."""
        subscription_data = {"default_payment_method": "pm_test_123"}
        result = http_provider._extract_payment_method_id(subscription_data)
        assert result == "pm_test_123"

    def test_extract_payment_method_id_object(self, http_provider):
        """Test extracting payment method ID when it's an object."""
        subscription_data = {
            "default_payment_method": {"id": "pm_test_456", "type": "card"}
        }
        result = http_provider._extract_payment_method_id(subscription_data)
        assert result == "pm_test_456"

    def test_extract_payment_method_id_none(self, http_provider):
        """Test extracting payment method ID when it's None."""
        subscription_data = {"default_payment_method": None}
        result = http_provider._extract_payment_method_id(subscription_data)
        assert result is None

    def test_create_stripe_http_provider_factory(self):
        """Test the factory function creates HTTP provider."""
        provider = create_stripe_http_provider("sk_test_key")
        assert isinstance(provider, StripeHTTPProvider)
        assert provider.api_key == "sk_test_key"


@pytest.mark.unit
class TestStripeProviderFactory:
    """Unit tests for Stripe provider factory."""

    def test_create_stripe_provider_http_type_enum(self):
        """Test factory creates HTTP provider when using enum."""
        provider = create_stripe_provider("sk_test_key", ProviderType.HTTP)
        assert isinstance(provider, StripeHTTPProvider)

    def test_create_stripe_provider_sdk_type_enum(self):
        """Test factory creates SDK provider when using enum."""
        from src.providers.stripe_payment_provider import StripePaymentProvider
        provider = create_stripe_provider("sk_test_key", ProviderType.SDK, "merchant_123")
        assert isinstance(provider, StripePaymentProvider)

    def test_create_stripe_provider_http_type_string(self):
        """Test factory creates HTTP provider when using string."""
        provider = create_stripe_provider("sk_test_key", "http")
        assert isinstance(provider, StripeHTTPProvider)

    def test_create_stripe_provider_sdk_type_string(self):
        """Test factory creates SDK provider when using string."""
        from src.providers.stripe_payment_provider import StripePaymentProvider
        provider = create_stripe_provider("sk_test_key", "sdk", "merchant_123")
        assert isinstance(provider, StripePaymentProvider)

    def test_create_stripe_provider_default(self):
        """Test factory creates SDK provider by default."""
        from src.providers.stripe_payment_provider import StripePaymentProvider
        provider = create_stripe_provider("sk_test_key")  # No provider type specified
        assert isinstance(provider, StripePaymentProvider)

    def test_create_stripe_provider_invalid_string(self):
        """Test factory defaults to SDK provider with invalid string."""
        from src.providers.stripe_payment_provider import StripePaymentProvider
        provider = create_stripe_provider("sk_test_key", "invalid_type")
        assert isinstance(provider, StripePaymentProvider)

    def test_create_stripe_sdk_provider_direct(self):
        """Test direct SDK provider creation."""
        from src.providers.stripe_payment_provider import StripePaymentProvider
        provider = create_stripe_sdk_provider("sk_test_key", "merchant_123")
        assert isinstance(provider, StripePaymentProvider)

    def test_create_stripe_http_provider_direct(self):
        """Test direct HTTP provider creation."""
        provider = factory_create_http("sk_test_key")
        assert isinstance(provider, StripeHTTPProvider)