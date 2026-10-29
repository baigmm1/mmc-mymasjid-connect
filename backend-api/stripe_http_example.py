"""
Example usage of the new Stripe HTTP Provider.

This script demonstrates how to use the HTTP provider to make direct API calls
to Stripe endpoints, giving you full control over the data returned.

Usage:
    Set environment variables:
    - STRIPE_SECRET_KEY: Your Stripe secret key
    - STRIPE_PROVIDER_TYPE: "http" (to use HTTP provider)
    
    Then run:
    python stripe_http_example.py
"""

import asyncio
import os
from datetime import datetime

from src.providers.stripe_provider_factory import create_stripe_provider, is_http_provider
from src.providers.stripe_http_provider import StripeHTTPProvider
from src.config import settings


async def demo_http_provider():
    """Demonstrate the HTTP provider functionality."""
    
    # Check configuration
    print(f"Stripe Provider Type: {settings.STRIPE_PROVIDER_TYPE}")
    print(f"Using HTTP Provider: {is_http_provider()}")
    print(f"Base URL: {settings.STRIPE_API_BASE_URL}")
    print(f"API Version: {settings.STRIPE_API_VERSION}")
    print("-" * 60)
    
    # You would normally get this from environment variables
    test_api_key = "sk_test_your_key_here"  # Replace with your test key
    
    # Create provider using factory
    provider = create_stripe_provider(test_api_key)
    
    if isinstance(provider, StripeHTTPProvider):
        print("✓ Successfully created HTTP provider")
        
        # Example: Get subscription data
        try:
            print("\n1. Testing direct subscription retrieval...")
            
            # This would be a real subscription ID from your Stripe account
            test_subscription_id = "sub_test_123"
            
            # Get raw subscription data (full Stripe response)
            raw_data = await provider.get_subscription(
                test_subscription_id, 
                expand=["default_payment_method", "latest_invoice.payment_intent"]
            )
            
            print(f"✓ Raw subscription data keys: {list(raw_data.keys())}")
            print(f"  Subscription ID: {raw_data.get('id')}")
            print(f"  Customer: {raw_data.get('customer')}")
            print(f"  Status: {raw_data.get('status')}")
            print(f"  Created: {datetime.fromtimestamp(raw_data.get('created', 0))}")
            
            # Get as SubscriptionModel
            print("\n2. Testing model conversion...")
            subscription_model = await provider.get_subscription_as_model(
                test_subscription_id,
                expand=["default_payment_method", "latest_invoice.payment_intent"]
            )
            
            print(f"✓ SubscriptionModel created:")
            print(f"  ID: {subscription_model.id}")
            print(f"  Customer: {subscription_model.customer}")
            print(f"  Created: {subscription_model.created_datetime}")
            print(f"  Payment Method: {subscription_model.payment_method_desc}")
            print(f"  Latest Invoice: {subscription_model.latest_invoice_id}")
            print(f"  Payment Intent: {subscription_model.payment_intent_id}")
            
        except Exception as e:
            print(f"✗ Error (expected with test data): {e}")
            print("  This is normal when using test subscription IDs")
        
        # Example: Compare with SDK provider
        print("\n3. Comparing data completeness...")
        print("   HTTP Provider advantages:")
        print("   - Access to complete Stripe response")
        print("   - No SDK filtering or transformation")
        print("   - Full control over expand parameters")
        print("   - Can access any field returned by Stripe API")
        
        # Clean up
        await provider.close()
        print("\n✓ HTTP client closed")
    
    else:
        print("✗ Provider is not HTTP type - check STRIPE_PROVIDER_TYPE setting")


async def compare_providers():
    """Compare HTTP vs SDK providers."""
    
    print("\n" + "=" * 60)
    print("PROVIDER COMPARISON")
    print("=" * 60)
    
    test_api_key = "sk_test_your_key_here"
    
    print("\nSDK Provider (stripe Python package):")
    print("  ✓ Easy to use")
    print("  ✓ Built-in error handling")
    print("  ✗ May filter response data")
    print("  ✗ Limited to SDK's data structure")
    print("  ✗ Updates require SDK updates")
    
    print("\nHTTP Provider (direct API calls):")
    print("  ✓ Complete access to API response")
    print("  ✓ Full control over requests")
    print("  ✓ Always up-to-date with Stripe API")
    print("  ✓ Custom error handling")
    print("  ✗ More code for basic operations")
    print("  ✗ Manual request/response handling")
    
    print(f"\nCurrent configuration: {settings.STRIPE_PROVIDER_TYPE}")


if __name__ == "__main__":
    print("Stripe HTTP Provider Demo")
    print("=" * 60)
    
    # Check if we have configuration
    if not settings.STRIPE_SECRET_KEY:
        print("⚠️  No STRIPE_SECRET_KEY found in configuration")
        print("   Set STRIPE_SECRET_KEY environment variable to test with real data")
    
    try:
        # Run demo
        asyncio.run(demo_http_provider())
        asyncio.run(compare_providers())
        
        print("\n" + "=" * 60)
        print("CONFIGURATION GUIDE")
        print("=" * 60)
        print("To use HTTP provider, set these environment variables:")
        print("  STRIPE_PROVIDER_TYPE=http")
        print("  STRIPE_SECRET_KEY=sk_test_your_key_here")
        print("  STRIPE_API_BASE_URL=https://api.stripe.com/v1  # (optional)")
        print("  STRIPE_API_VERSION=2023-10-16  # (optional)")
        
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"\nDemo failed: {e}")
        import traceback
        traceback.print_exc()