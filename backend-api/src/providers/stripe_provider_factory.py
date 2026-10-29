"""
Stripe provider factory for selecting between SDK and HTTP providers.

This factory allows choosing between the traditional Stripe Python SDK
and the direct HTTP API provider based on explicit parameters rather
than configuration settings.
"""

from enum import Enum
from typing import Union

from src.core.logging import get_logger
from src.providers.stripe_payment_provider import StripePaymentProvider
from src.providers.stripe_http_provider import StripeHTTPProvider

logger = get_logger(__name__)


class ProviderType(Enum):
    """Enumeration for Stripe provider types."""
    SDK = "sdk"
    HTTP = "http"


def create_stripe_sdk_provider(api_key: str, merchant_id: str = "") -> StripePaymentProvider:
    """
    Create a Stripe SDK provider.
    
    Args:
        api_key: Stripe secret API key
        merchant_id: Merchant ID (used by SDK provider)
        
    Returns:
        StripePaymentProvider instance
    """
    logger.info("Creating Stripe SDK provider")
    return StripePaymentProvider(api_key, merchant_id)


def create_stripe_http_provider(api_key: str) -> StripeHTTPProvider:
    """
    Create a Stripe HTTP provider for direct API calls.
    
    Args:
        api_key: Stripe secret API key
        
    Returns:
        StripeHTTPProvider instance
    """
    logger.info("Creating Stripe HTTP provider for direct API calls")
    return StripeHTTPProvider(api_key)


def create_stripe_provider(
    api_key: str, 
    provider_type: Union[ProviderType, str] = ProviderType.SDK,
    merchant_id: str = ""
) -> Union[StripePaymentProvider, StripeHTTPProvider]:
    """
    Factory function to create the appropriate Stripe provider based on parameters.
    
    Args:
        api_key: Stripe secret API key
        provider_type: Type of provider to create (ProviderType.SDK or ProviderType.HTTP)
        merchant_id: Merchant ID (used by SDK provider, ignored by HTTP provider)
        
    Returns:
        Either StripePaymentProvider (SDK) or StripeHTTPProvider (HTTP) based on provider_type
        
    Examples:
        # Create SDK provider (default)
        sdk_provider = create_stripe_provider(api_key, ProviderType.SDK, merchant_id)
        
        # Create HTTP provider
        http_provider = create_stripe_provider(api_key, ProviderType.HTTP)
        
        # Using string values
        sdk_provider = create_stripe_provider(api_key, "sdk", merchant_id)
        http_provider = create_stripe_provider(api_key, "http")
    """
    # Convert string to enum if needed
    if isinstance(provider_type, str):
        try:
            provider_type = ProviderType(provider_type.lower())
        except ValueError:
            logger.warning(f"Invalid provider type '{provider_type}', defaulting to SDK")
            provider_type = ProviderType.SDK
    
    if provider_type == ProviderType.HTTP:
        return create_stripe_http_provider(api_key)
    else:
        return create_stripe_sdk_provider(api_key, merchant_id)