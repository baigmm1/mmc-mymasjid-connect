"""
Global provider manager for singleton provider instances.

This module provides centralized access to payment and email providers,
ensuring that only one instance of each provider is created per company/configuration
and shared across all requests.

Usage:
    from src.core.provider_manager import get_stripe_provider, get_stripe_http_provider, get_email_provider
    
    # Get Stripe SDK provider (creates on first access, reuses thereafter)
    stripe = await get_stripe_provider(session, company_id)
    
    # Get Stripe HTTP provider (creates on first access, reuses thereafter)
    stripe_http = await get_stripe_http_provider(session, company_id)
    
    # Get Email provider (creates on first access, reuses thereafter)
    email = await get_email_provider(session, company_id)
    
    # Clear cached providers (useful for testing or config changes)
    clear_provider_cache()
"""

from typing import Optional, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.config import settings
from src.core.provider_config_utils import get_provider_config
from src.providers.stripe_payment_provider import StripePaymentProvider
from src.providers.stripe_http_provider import StripeHTTPProvider
from src.providers.sendgrid_email_provider import SendGridEmailProvider


logger = get_logger(__name__, level=settings.LOG_LEVEL)


# Global cache for provider instances
# Key format: (provider_type, company_id, merchant_id)
_provider_cache: Dict[Tuple[str, int, str], object] = {}


async def get_stripe_provider(
    session: AsyncSession,
    company_id: int
) -> StripePaymentProvider:
    """
    Get or create a Stripe payment provider instance for the specified company.
    
    The provider instance is cached and reused for subsequent requests with the
    same company_id and merchant configuration.
    
    Args:
        session: Database session for fetching provider configuration
        company_id: Company ID to get provider configuration for
        
    Returns:
        StripePaymentProvider instance configured for the company
        
    Raises:
        ValueError: If provider configuration is not found or invalid
        Exception: If provider initialization fails
        
    Example:
        ```python
        stripe = await get_stripe_provider(session, company_id=10001)
        payment_intent = await stripe.create_payment_intent(...)
        ```
    """
    try:
        # Fetch provider configuration
        provider_config = await get_provider_config(
            session=session,
            company_id=company_id,
            provider="Stripe"
        )
        
        if not provider_config:
            logger.error(
                f"No provider configuration found for company_id={company_id}"
            )
            raise ValueError(
                f"No provider configuration found for company {company_id}"
            )
        
        # Extract configuration
        api_key = provider_config.PrivateKey or provider_config.APIKey or ""
        merchant_id = provider_config.MerchantId or ""
        
        if not api_key or not merchant_id:
            logger.error(
                "Invalid provider configuration: missing API key or merchant ID",
                extra={
                    "company_id": company_id,
                    "merchant_id": merchant_id,
                    "has_api_key": bool(api_key)
                }
            )
            raise ValueError(
                f"Invalid provider configuration for company {company_id}: "
                f"missing API key or merchant ID"
            )
        
        # Check cache for existing provider
        cache_key = ("stripe", company_id, merchant_id)
        
        if cache_key in _provider_cache:
            logger.debug(
                "Returning cached Stripe provider",
                extra={"company_id": company_id, "merchant_id": merchant_id}
            )
            return _provider_cache[cache_key]  # type: ignore
        
        # Create new provider instance
        logger.info(
            "Creating new Stripe provider instance",
            extra={"company_id": company_id, "merchant_id": merchant_id}
        )
        
        stripe_provider = StripePaymentProvider(
            api_key=api_key,
            merchant_id=merchant_id
        )
        
        # Cache the provider
        _provider_cache[cache_key] = stripe_provider
        
        logger.info(
            "Stripe provider created and cached",
            extra={"company_id": company_id, "merchant_id": merchant_id}
        )
        
        return stripe_provider
        
    except ValueError:
        # Re-raise ValueError as-is
        raise
    except Exception as e:
        logger.error(
            f"Failed to initialize Stripe provider: {str(e)}",
            exc_info=True,
            extra={"company_id": company_id}
        )
        raise


async def get_stripe_http_provider(
    session: AsyncSession,
    company_id: int
) -> StripeHTTPProvider:
    """
    Get or create a Stripe HTTP provider instance for the specified company.
    
    The provider instance is cached and reused for subsequent requests with the
    same company_id and merchant configuration. This provider makes direct HTTP
    requests to Stripe API without SDK limitations.
    
    Args:
        session: Database session for fetching provider configuration
        company_id: Company ID to get provider configuration for
        
    Returns:
        StripeHTTPProvider instance configured for the company
        
    Raises:
        ValueError: If provider configuration is not found or invalid
        Exception: If provider initialization fails
        
    Example:
        ```python
        stripe_http = await get_stripe_http_provider(session, company_id=10001)
        # Use stripe_http for direct HTTP API calls
        ```
    """
    try:
        # Fetch provider configuration
        provider_config = await get_provider_config(
            session=session,
            company_id=company_id,
            provider="Stripe"
        )
        
        if not provider_config:
            logger.error(
                f"No provider configuration found for company_id={company_id}"
            )
            raise ValueError(
                f"No provider configuration found for company {company_id}"
            )
        
        # Extract configuration
        api_key = provider_config.PrivateKey or provider_config.APIKey or ""
        merchant_id = provider_config.MerchantId or ""
        
        if not api_key:
            logger.error(
                "Invalid provider configuration: missing API key",
                extra={
                    "company_id": company_id,
                    "merchant_id": merchant_id
                }
            )
            raise ValueError(
                f"Invalid provider configuration for company {company_id}: "
                f"missing API key"
            )
        
        # Check cache for existing provider
        cache_key = ("stripe_http", company_id, merchant_id)
        
        if cache_key in _provider_cache:
            logger.debug(
                "Returning cached Stripe HTTP provider",
                extra={"company_id": company_id, "merchant_id": merchant_id}
            )
            return _provider_cache[cache_key]  # type: ignore
        
        # Create new provider instance
        logger.info(
            "Creating new Stripe HTTP provider instance",
            extra={"company_id": company_id, "merchant_id": merchant_id}
        )
        
        stripe_http_provider = StripeHTTPProvider(
            api_key=api_key
        )
        
        # Cache the provider
        _provider_cache[cache_key] = stripe_http_provider
        
        logger.info(
            "Stripe HTTP provider created and cached",
            extra={"company_id": company_id, "merchant_id": merchant_id}
        )
        
        return stripe_http_provider
        
    except ValueError:
        # Re-raise ValueError as-is
        raise
    except Exception as e:
        logger.error(
            f"Failed to initialize Stripe HTTP provider: {str(e)}",
            exc_info=True,
            extra={"company_id": company_id}
        )
        raise


async def get_email_provider(
    session: AsyncSession,
    company_id: int
) -> SendGridEmailProvider:
    """
    Get or create an email provider instance for the specified company.
    
    The provider instance is cached and reused for subsequent requests with the
    same company_id and configuration.
    
    Args:
        session: Database session for fetching provider configuration
        company_id: Company ID to get provider configuration for
        provider_name: Email provider name (default: "SendGridEMail")
        
    Returns:
        SendGridEmailProvider instance configured for the company
        
    Raises:
        ValueError: If provider configuration is not found or invalid
        Exception: If provider initialization fails
        
    Example:
        ```python
        email = await get_email_provider(session, company_id=10001)
        await email.send_email(to_email="donor@example.com", ...)
        ```
    """
    try:
        # Fetch provider configuration
        provider_config = await get_provider_config(
            session=session,
            company_id=company_id,
            provider="SendGridEMail"
        )
        
        if not provider_config:
            logger.error(
                f"No email provider configuration found for company_id={company_id}"
            )
            raise ValueError(
                f"No SendGridEMail email provider configuration found for company {company_id}"
            )
        
        # Extract configuration
        api_key = provider_config.APIKey or provider_config.PrivateKey or ""
        # Use settings for from_email and from_name as provider config doesn't have these fields
        from_email = settings.SENDGRID_FROM_EMAIL or ""
        from_name = settings.SENDGRID_FROM_NAME or "Masjid Connect"
        merchant_id = provider_config.MerchantId or f"{company_id}"
        
        if not api_key:
            logger.error(
                "Invalid email provider configuration: missing API key",
                extra={"company_id": company_id}
            )
            raise ValueError(
                f"Invalid email provider configuration for company {company_id}: missing API key"
            )
        
        if not from_email:
            logger.error(
                "Invalid email provider configuration: missing from_email",
                extra={"company_id": company_id}
            )
            raise ValueError(
                f"Invalid email provider configuration for company {company_id}: "
                f"missing from_email (check SENDGRID_FROM_EMAIL setting)"
            )
        
        # Check cache for existing provider
        cache_key = ("email", company_id, merchant_id)
        
        if cache_key in _provider_cache:
            logger.debug(
                "Returning cached email provider",
                extra={"company_id": company_id}
            )
            return _provider_cache[cache_key]  # type: ignore
        
        # Create new provider instance
        logger.info(
            "Creating new email provider instance",
            extra={"company_id": company_id, "from_email": from_email}
        )
        
        email_provider = SendGridEmailProvider(
            api_key=api_key,
            from_email=from_email,
            from_name=from_name
        )
        
        # Cache the provider
        _provider_cache[cache_key] = email_provider
        
        logger.info(
            "Email provider created and cached",
            extra={"company_id": company_id}
        )
        
        return email_provider
        
    except ValueError:
        # Re-raise ValueError as-is
        raise
    except Exception as e:
        logger.error(
            f"Failed to initialize email provider: {str(e)}",
            exc_info=True,
            extra={"company_id": company_id}
        )
        raise


def clear_provider_cache(
    provider_type: Optional[str] = None,
    company_id: Optional[int] = None
) -> int:
    """
    Clear cached provider instances.
    
    This is useful when provider configuration changes or for testing purposes.
    
    Args:
        provider_type: Optional provider type to clear ("stripe", "stripe_http", or "email")
                      If None, clears all providers
        company_id: Optional company ID to clear providers for
                   If None, clears all companies
                   
    Returns:
        Number of provider instances removed from cache
        
    Examples:
        ```python
        # Clear all cached providers
        clear_provider_cache()
        
        # Clear only Stripe SDK providers
        clear_provider_cache(provider_type="stripe")
        
        # Clear only Stripe HTTP providers
        clear_provider_cache(provider_type="stripe_http")
        
        # Clear all providers for a specific company
        clear_provider_cache(company_id=10001)
        
        # Clear Stripe provider for specific company
        clear_provider_cache(provider_type="stripe", company_id=10001)
        ```
    """
    global _provider_cache
    
    if provider_type is None and company_id is None:
        # Clear everything
        count = len(_provider_cache)
        _provider_cache.clear()
        logger.info(f"Cleared all provider cache ({count} providers)")
        return count
    
    # Filter and remove matching entries
    keys_to_remove = []
    for key in _provider_cache.keys():
        key_provider_type, key_company_id, _ = key
        
        if provider_type and key_provider_type != provider_type:
            continue
        if company_id and key_company_id != company_id:
            continue
            
        keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del _provider_cache[key]
    
    logger.info(
        f"Cleared {len(keys_to_remove)} provider(s) from cache",
        extra={
            "provider_type": provider_type,
            "company_id": company_id,
            "cleared_count": len(keys_to_remove)
        }
    )
    
    return len(keys_to_remove)


def get_cache_stats() -> Dict[str, int]:
    """
    Get statistics about cached providers.
    
    Returns:
        Dictionary with cache statistics:
        - total: Total number of cached providers
        - stripe: Number of Stripe SDK providers
        - stripe_http: Number of Stripe HTTP providers
        - email: Number of email providers
        
    Example:
        ```python
        stats = get_cache_stats()
        print(f"Total cached providers: {stats['total']}")
        ```
    """
    stats = {
        "total": len(_provider_cache),
        "stripe": 0,
        "stripe_http": 0,
        "email": 0
    }
    
    for key in _provider_cache.keys():
        provider_type, _, _ = key
        if provider_type == "stripe":
            stats["stripe"] += 1
        elif provider_type == "stripe_http":
            stats["stripe_http"] += 1
        elif provider_type == "email":
            stats["email"] += 1
    
    return stats
