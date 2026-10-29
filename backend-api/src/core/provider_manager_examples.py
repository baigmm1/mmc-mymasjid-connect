"""
Provider Manager Usage Examples

This module demonstrates how to use the global provider manager to access
Stripe and SendGrid providers as singleton instances.

The provider manager ensures that:
1. Providers are initialized only once per company/configuration
2. Subsequent requests reuse the cached provider instance
3. Configuration is loaded from the database automatically
4. Error handling is consistent across the application
"""

from sqlalchemy.ext.asyncio import AsyncSession
from src.core.provider_manager import (
    get_stripe_provider,
    get_email_provider,
    clear_provider_cache,
    get_cache_stats
)


# Example 1: Using Stripe Provider
async def process_payment_example(session: AsyncSession, company_id: int, amount: float):
    """
    Example of using the Stripe provider to process a payment.
    
    The provider is automatically cached after first access.
    Subsequent calls with the same company_id will reuse the same instance.
    """
    # Get Stripe provider (creates or retrieves from cache)
    stripe = await get_stripe_provider(
        session=session,
        company_id=company_id,
        payment_method="stripe_terminal"
    )
    
    # Use the provider
    payment_intent = await stripe.create_payment_intent(
        amount=int(amount * 100),  # Convert to cents
        currency="usd",
        description="Donation payment"
    )
    
    return payment_intent


# Example 2: Using Email Provider
async def send_receipt_example(
    session: AsyncSession,
    company_id: int,
    email: str,
    transaction_id: int
):
    """
    Example of using the email provider to send a receipt.
    
    The provider configuration is loaded from database and cached.
    """
    # Get email provider (creates or retrieves from cache)
    email_provider = await get_email_provider(
        session=session,
        company_id=company_id,
        provider_name="sendgrid"
    )
    
    # Send email
    result = await email_provider.send_email(
        to_email=email,
        subject=f"Receipt for Transaction #{transaction_id}",
        html_content="<h1>Thank you for your donation!</h1>",
        custom_args={
            "transaction_id": str(transaction_id),
            "company_id": str(company_id)
        }
    )
    
    return result


# Example 3: Error Handling
async def handle_provider_errors_example(session: AsyncSession, company_id: int):
    """
    Example of handling provider initialization errors.
    
    The provider manager raises ValueError for configuration issues.
    """
    try:
        stripe = await get_stripe_provider(
            session=session,
            company_id=company_id
        )
        # Use provider...
        
    except ValueError as e:
        # Configuration not found or invalid
        print(f"Provider configuration error: {e}")
        # Handle error (e.g., return error response to user)
        
    except Exception as e:
        # Other errors (database, network, etc.)
        print(f"Unexpected error: {e}")
        # Handle error


# Example 4: Cache Management
def cache_management_example():
    """
    Example of managing the provider cache.
    
    Useful for testing, configuration updates, or memory management.
    """
    # Get current cache statistics
    stats = get_cache_stats()
    print(f"Total cached providers: {stats['total']}")
    print(f"Stripe providers: {stats['stripe']}")
    print(f"Email providers: {stats['email']}")
    
    # Clear all cached providers
    cleared_count = clear_provider_cache()
    print(f"Cleared {cleared_count} provider(s)")
    
    # Clear only Stripe providers
    cleared_count = clear_provider_cache(provider_type="stripe")
    print(f"Cleared {cleared_count} Stripe provider(s)")
    
    # Clear all providers for a specific company
    cleared_count = clear_provider_cache(company_id=10001)
    print(f"Cleared {cleared_count} provider(s) for company 10001")
    
    # Clear Stripe provider for specific company
    cleared_count = clear_provider_cache(
        provider_type="stripe",
        company_id=10001
    )
    print(f"Cleared Stripe provider for company 10001")


# Example 5: Using in FastAPI Endpoints
"""
Example of using providers in FastAPI endpoints:

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.core.provider_manager import get_stripe_provider, get_email_provider

router = APIRouter()

@router.post("/payment")
async def create_payment(
    company_id: int,
    amount: float,
    session: AsyncSession = Depends(get_session)
):
    # Get provider - automatically cached
    stripe = await get_stripe_provider(session, company_id)
    
    # Process payment
    intent = await stripe.create_payment_intent(
        amount=int(amount * 100),
        currency="usd"
    )
    
    return {"payment_intent_id": intent.id}


@router.post("/send-receipt/{transaction_id}")
async def send_receipt(
    transaction_id: int,
    company_id: int,
    email: str,
    session: AsyncSession = Depends(get_session)
):
    # Get email provider - automatically cached
    email_provider = await get_email_provider(session, company_id)
    
    # Send receipt
    await email_provider.send_email(
        to_email=email,
        subject=f"Receipt #{transaction_id}",
        html_content="<h1>Thank you!</h1>"
    )
    
    return {"success": True}
"""


# Example 6: Testing with Cache Clearing
"""
Example of clearing cache in tests:

import pytest
from src.core.provider_manager import clear_provider_cache

@pytest.fixture(autouse=True)
def clear_cache_after_test():
    # Clear cache after each test to ensure isolation
    yield
    clear_provider_cache()


async def test_payment_processing(session):
    # Test with clean provider cache
    stripe = await get_stripe_provider(session, company_id=1)
    # ... test logic
"""


# Benefits of Using Provider Manager:
"""
1. Performance: Providers are created once and reused
   - Reduces overhead of repeated initialization
   - Shares connection pools and resources

2. Consistency: All provider access goes through the same path
   - Standardized error handling
   - Consistent configuration loading
   - Easier to maintain and debug

3. Memory Efficiency: Shared instances reduce memory usage
   - One provider instance per company/config instead of per request
   - Automatic caching with configurable clearing

4. Testability: Easy to clear cache and reset state
   - Clean state between tests
   - Mock-friendly design

5. Maintainability: Centralized provider management
   - Single place to update provider logic
   - Easy to add new provider types
   - Configuration changes don't require code updates
"""
