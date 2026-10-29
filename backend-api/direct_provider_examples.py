"""
Direct Provider Usage Examples

This demonstrates how to use both SDK and HTTP providers directly
based on your specific use case, without environment-based switching.
"""

import asyncio
from src.providers.stripe_provider_factory import (
    create_stripe_provider,
    create_stripe_sdk_provider, 
    create_stripe_http_provider,
    ProviderType
)


async def use_case_examples():
    """Examples of when to use each provider."""
    
    api_key = "sk_test_your_key_here"
    merchant_id = "merchant_123"
    
    print("=" * 60)
    print("DIRECT PROVIDER USAGE EXAMPLES")
    print("=" * 60)
    
    # Use Case 1: Need complete Stripe API data (use HTTP)
    print("\n1. USE CASE: Need complete subscription data with all fields")
    print("   SOLUTION: Use HTTP Provider")
    
    http_provider = create_stripe_http_provider(api_key)
    try:
        # Get complete subscription data with expansions
        subscription_data = await http_provider.get_subscription(
            "sub_test_123",
            expand=["default_payment_method", "latest_invoice", "customer"]
        )
        print(f"   ✓ HTTP Provider - All fields available: {list(subscription_data.keys())[:10]}...")
        
        # Access any field from Stripe API
        customer_data = subscription_data.get("customer", {})
        payment_method = subscription_data.get("default_payment_method", {})
        
        print(f"   ✓ Customer email: {customer_data.get('email', 'N/A')}")
        print(f"   ✓ Payment method type: {payment_method.get('type', 'N/A')}")
        
    except Exception as e:
        print(f"   ⚠️  Expected error with test data: {e}")
    finally:
        await http_provider.close()
    
    # Use Case 2: Simple operations with SDK convenience (use SDK)
    print("\n2. USE CASE: Simple payment processing with SDK helpers")
    print("   SOLUTION: Use SDK Provider")
    
    sdk_provider = create_stripe_sdk_provider(api_key, merchant_id)
    try:
        # SDK provides convenient methods and error handling
        print("   ✓ SDK Provider - Convenient built-in methods")
        print("   ✓ Automatic error handling and retries")
        print("   ✓ Simplified object access")
        
    except Exception as e:
        print(f"   ⚠️  Error: {e}")
    
    # Use Case 3: Factory method with explicit choice
    print("\n3. USE CASE: Dynamic provider selection based on requirements")
    print("   SOLUTION: Use Factory with Parameters")
    
    # Choose provider based on your specific needs
    need_complete_data = True
    
    if need_complete_data:
        provider = create_stripe_provider(api_key, ProviderType.HTTP)
        print("   ✓ Selected HTTP Provider for complete data access")
    else:
        provider = create_stripe_provider(api_key, ProviderType.SDK, merchant_id)
        print("   ✓ Selected SDK Provider for simple operations")
    
    # Clean up HTTP provider if needed
    if hasattr(provider, 'close'):
        await provider.close()


async def specific_scenarios():
    """Specific scenarios for when to use each provider."""
    
    api_key = "sk_test_your_key_here"
    
    print("\n" + "=" * 60)
    print("SPECIFIC USE CASE SCENARIOS")
    print("=" * 60)
    
    scenarios = [
        {
            "scenario": "Webhooks Processing - Need all event data",
            "provider": "HTTP",
            "reason": "Webhooks may contain fields not exposed by SDK"
        },
        {
            "scenario": "Basic payment creation",
            "provider": "SDK", 
            "reason": "SDK provides convenient helpers and validation"
        },
        {
            "scenario": "Data analysis - Export subscription details",
            "provider": "HTTP",
            "reason": "Need access to all metadata and custom fields"
        },
        {
            "scenario": "Customer portal - Display payment methods",
            "provider": "SDK",
            "reason": "SDK objects provide easy access to common fields"
        },
        {
            "scenario": "Integration testing - Verify API responses",
            "provider": "HTTP", 
            "reason": "Need to test exact API response structure"
        },
        {
            "scenario": "Simple refund processing",
            "provider": "SDK",
            "reason": "SDK provides built-in refund methods"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. SCENARIO: {scenario['scenario']}")
        print(f"   RECOMMENDED: {scenario['provider']} Provider")
        print(f"   REASON: {scenario['reason']}")
        
        if scenario['provider'] == 'HTTP':
            # Example HTTP usage
            print("   CODE EXAMPLE:")
            print("   async with create_stripe_http_provider(api_key) as provider:")
            print("       data = await provider.get_subscription('sub_123')")
            print("       # Access all fields: data.get('any_field')")
        else:
            # Example SDK usage  
            print("   CODE EXAMPLE:")
            print("   provider = create_stripe_sdk_provider(api_key)")
            print("   # Use SDK convenience methods")


def synchronous_examples():
    """Examples that don't require async operations."""
    
    print("\n" + "=" * 60)
    print("PROVIDER SELECTION EXAMPLES")
    print("=" * 60)
    
    api_key = "sk_test_key"
    merchant_id = "merchant_123"
    
    # Method 1: Direct provider creation
    print("\nMETHOD 1: Direct Provider Creation")
    sdk_provider = create_stripe_sdk_provider(api_key, merchant_id)
    http_provider = create_stripe_http_provider(api_key)
    print(f"✓ SDK Provider: {type(sdk_provider).__name__}")
    print(f"✓ HTTP Provider: {type(http_provider).__name__}")
    
    # Method 2: Factory with enum
    print("\nMETHOD 2: Factory with ProviderType Enum")
    sdk_via_factory = create_stripe_provider(api_key, ProviderType.SDK, merchant_id)
    http_via_factory = create_stripe_provider(api_key, ProviderType.HTTP)
    print(f"✓ SDK via Factory: {type(sdk_via_factory).__name__}")
    print(f"✓ HTTP via Factory: {type(http_via_factory).__name__}")
    
    # Method 3: Factory with string
    print("\nMETHOD 3: Factory with String")
    sdk_string = create_stripe_provider(api_key, "sdk", merchant_id)
    http_string = create_stripe_provider(api_key, "http")
    print(f"✓ SDK via String: {type(sdk_string).__name__}")
    print(f"✓ HTTP via String: {type(http_string).__name__}")
    
    # Method 4: Default behavior
    print("\nMETHOD 4: Default Provider (SDK)")
    default_provider = create_stripe_provider(api_key)
    print(f"✓ Default Provider: {type(default_provider).__name__}")


if __name__ == "__main__":
    print("Stripe Provider Direct Usage Examples")
    
    try:
        # Run synchronous examples first
        synchronous_examples()
        
        # Run async examples
        asyncio.run(use_case_examples())
        asyncio.run(specific_scenarios())
        
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print("✓ Use HTTP Provider when you need complete API data")
        print("✓ Use SDK Provider when you want convenience and simplicity") 
        print("✓ Choose provider based on specific use case requirements")
        print("✓ No environment variables needed - control via parameters")
        print("✓ Both providers can be used in the same application")
        
    except KeyboardInterrupt:
        print("\nExamples interrupted by user")
    except Exception as e:
        print(f"\nExample failed: {e}")
        import traceback
        traceback.print_exc()