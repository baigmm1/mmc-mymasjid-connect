"""
Utility functions for accessing provider configurations within backend code.

Provides convenient access to provider configuration settings for payment providers
like Stripe, PayPal, etc., using cached data for optimal performance.
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cache_manager import (
    get_provider_configuration_from_cache,
    get_provider_configurations_for_company_from_cache,
)
from src.core.logging import get_logger
from src.database.models.provider_configuration import ProviderConfiguration

logger = get_logger(__name__)


async def get_provider_config(
    company_id: int,
    provider: str,
    session: Optional[AsyncSession] = None,
) -> Optional[ProviderConfiguration]:
    """
    Get provider configuration for a specific company and provider.

    This is a convenience function for internal backend code to easily
    retrieve provider configurations from cache or database.

    Args:
        company_id: Company identifier
        provider: Provider name (e.g., "Stripe", "PayPal")
        session: Optional database session for fallback query

    Returns:
        ProviderConfiguration object if found, None otherwise

    Example:
        ```python
        from src.core.provider_config_utils import get_provider_config
        from src.database import get_session

        async with get_session() as session:
            stripe_config = await get_provider_config(1, "Stripe", session)
            if stripe_config:
                api_key = stripe_config.APIKey
                merchant_id = stripe_config.MerchantId
        ```
    """
    try:
        config = await get_provider_configuration_from_cache(company_id, provider, session)
        if config:
            logger.debug(f"Retrieved provider config for company_id={company_id}, provider={provider}")
        else:
            logger.warning(f"No provider config found for company_id={company_id}, provider={provider}")
        return config
    except Exception as e:
        logger.error(f"Error retrieving provider config: {e}", exc_info=True)
        return None


async def get_all_provider_configs_for_company(
    company_id: int,
) -> list[ProviderConfiguration]:
    """
    Get all provider configurations for a specific company.

    This is a convenience function for internal backend code to easily
    retrieve all provider configurations for a company from cache.

    Args:
        company_id: Company identifier

    Returns:
        List of ProviderConfiguration objects for the company

    Example:
        ```python
        from src.core.provider_config_utils import get_all_provider_configs_for_company

        configs = await get_all_provider_configs_for_company(1)
        for config in configs:
            print(f"Provider: {config.Provider}, Environment: {config.Environment}")
        ```
    """
    try:
        configs = await get_provider_configurations_for_company_from_cache(company_id)
        logger.debug(f"Retrieved {len(configs)} provider configs for company_id={company_id}")
        return configs
    except Exception as e:
        logger.error(f"Error retrieving provider configs for company: {e}", exc_info=True)
        return []


def get_provider_api_key(config: Optional[ProviderConfiguration]) -> Optional[str]:
    """
    Extract API key from provider configuration.

    Args:
        config: Provider configuration object

    Returns:
        API key if available, None otherwise
    """
    return config.APIKey if config else None


def get_provider_public_key(config: Optional[ProviderConfiguration]) -> Optional[str]:
    """
    Extract public key from provider configuration.

    Args:
        config: Provider configuration object

    Returns:
        Public key if available, None otherwise
    """
    return config.PublicKey if config else None


def get_provider_private_key(config: Optional[ProviderConfiguration]) -> Optional[str]:
    """
    Extract private key from provider configuration.

    Args:
        config: Provider configuration object

    Returns:
        Private key if available, None otherwise
    """
    return config.PrivateKey if config else None


def get_provider_merchant_id(config: Optional[ProviderConfiguration]) -> Optional[str]:
    """
    Extract merchant ID from provider configuration.

    Args:
        config: Provider configuration object

    Returns:
        Merchant ID if available, None otherwise
    """
    return config.MerchantId if config else None


def get_provider_timeout(config: Optional[ProviderConfiguration], default: int = 30) -> int:
    """
    Extract timeout from provider configuration with a default value.

    Args:
        config: Provider configuration object
        default: Default timeout in seconds if not specified (default: 30)

    Returns:
        Timeout in seconds
    """
    if config and config.Timeout is not None:
        return config.Timeout
    return default


def get_provider_retries(config: Optional[ProviderConfiguration], default: int = 3) -> int:
    """
    Extract retry count from provider configuration with a default value.

    Args:
        config: Provider configuration object
        default: Default number of retries if not specified (default: 3)

    Returns:
        Number of retries
    """
    if config and config.Retries is not None:
        return config.Retries
    return default
