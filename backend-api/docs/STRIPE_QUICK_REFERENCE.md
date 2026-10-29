# Stripe Provider Quick Reference

## Import Statements

```python
# Import factory and provider types
from src.providers.stripe_provider_factory import (
    create_stripe_provider,
    create_stripe_sdk_provider,
    create_stripe_http_provider,
    ProviderType
)

# Import providers directly
from src.providers.stripe_payment_provider import StripePaymentProvider
from src.providers.stripe_http_provider import StripeHTTPProvider
```

## Quick Usage Examples

### 1. Direct Provider Creation (Recommended)

```python
# Create HTTP provider for complete data access
http_provider = create_stripe_http_provider("sk_test_key")

# Create SDK provider for convenience
sdk_provider = create_stripe_sdk_provider("sk_test_key", "merchant_id")
```

### 2. Factory with Enum (Type-Safe)

```python
# Using enum (recommended for type safety)
http_provider = create_stripe_provider("sk_test_key", ProviderType.HTTP)
sdk_provider = create_stripe_provider("sk_test_key", ProviderType.SDK, "merchant_id")
```

### 3. Factory with String

```python
# Using strings (flexible)
http_provider = create_stripe_provider("sk_test_key", "http")
sdk_provider = create_stripe_provider("sk_test_key", "sdk", "merchant_id")
```

### 4. Default Provider (SDK)

```python
# Defaults to SDK provider
provider = create_stripe_provider("sk_test_key")  # No type specified
```

## Use Case Examples

### HTTP Provider - Complete Data

```python
# Webhook processing - need all fields
async def process_webhook(event_data):
    async with create_stripe_http_provider(api_key) as provider:
        subscription = await provider.get_subscription(
            event_data["data"]["object"]["subscription"],
            expand=["default_payment_method", "latest_invoice"]
        )

        # Access any field from Stripe API
        metadata = subscription.get("metadata", {})
        custom_fields = subscription.get("custom_fields", [])

        return process_custom_data(metadata, custom_fields)

# Data export - need complete information
async def export_subscriptions():
    async with create_stripe_http_provider(api_key) as provider:
        data = await provider.get_subscription("sub_123")
        return {field: data.get(field) for field in data.keys()}
```

### SDK Provider - Convenience

```python
# Simple payment operations
def create_refund(charge_id: str):
    provider = create_stripe_sdk_provider(api_key, merchant_id)
    # Use SDK convenience methods
    return provider.create_refund(charge_id)

# Basic subscription management
def get_subscription_status(sub_id: str):
    provider = create_stripe_sdk_provider(api_key, merchant_id)
    subscription = provider.get_subscription(sub_id)
    return subscription.status
```

## Provider Selection Logic

```python
def get_stripe_provider(use_case: str, api_key: str):
    """Select provider based on use case."""

    # Cases that need complete data
    complete_data_cases = [
        "webhook_processing",
        "data_export",
        "integration_testing",
        "custom_field_access",
        "audit_logging"
    ]

    if use_case in complete_data_cases:
        return create_stripe_http_provider(api_key)
    else:
        return create_stripe_sdk_provider(api_key, merchant_id)

# Usage
webhook_provider = get_stripe_provider("webhook_processing", api_key)
payment_provider = get_stripe_provider("simple_payment", api_key)
```

## Error Handling

### HTTP Provider

```python
async def safe_http_operation():
    async with create_stripe_http_provider(api_key) as provider:
        try:
            data = await provider.get_subscription("sub_123")
        except Exception as e:
            if "No such subscription" in str(e):
                return {"error": "subscription_not_found"}
            elif "invalid_request_error" in str(e):
                return {"error": "invalid_request"}
            else:
                return {"error": "unexpected", "details": str(e)}
```

### SDK Provider

```python
def safe_sdk_operation():
    provider = create_stripe_sdk_provider(api_key, merchant_id)
    try:
        # SDK operations
        result = provider.some_operation()
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

## Key Differences

| Feature            | HTTP Provider                      | SDK Provider                                |
| ------------------ | ---------------------------------- | ------------------------------------------- |
| **Creation**       | `create_stripe_http_provider(key)` | `create_stripe_sdk_provider(key, merchant)` |
| **Usage**          | `async with` recommended           | Direct instantiation                        |
| **Data Access**    | Complete API response              | SDK-filtered response                       |
| **Error Handling** | Manual parsing                     | SDK abstractions                            |
| **Memory Usage**   | Higher (complete data)             | Lower (filtered data)                       |
| **Use Cases**      | Data analysis, webhooks            | Simple operations                           |

## Best Practices

### 1. Use Async Context Manager for HTTP

```python
# ✅ Recommended
async with create_stripe_http_provider(api_key) as provider:
    data = await provider.get_subscription("sub_123")

# ❌ Avoid (manual cleanup)
provider = create_stripe_http_provider(api_key)
data = await provider.get_subscription("sub_123")
await provider.close()  # Manual cleanup required
```

### 2. Choose Provider Based on Data Needs

```python
# ✅ Need complete data → HTTP
async with create_stripe_http_provider(api_key) as provider:
    complete_data = await provider.get_subscription("sub_123")

# ✅ Simple operations → SDK
provider = create_stripe_sdk_provider(api_key, merchant_id)
simple_result = provider.basic_operation()
```

### 3. Use Type-Safe Enums

```python
# ✅ Type-safe with enum
provider = create_stripe_provider(api_key, ProviderType.HTTP)

# ⚠️ String works but less type-safe
provider = create_stripe_provider(api_key, "http")
```

### 4. Handle Provider Types Gracefully

```python
def universal_operation(provider_type: str, api_key: str):
    """Handle any provider type gracefully."""

    try:
        if provider_type.lower() == "http":
            provider = create_stripe_http_provider(api_key)
        else:
            provider = create_stripe_sdk_provider(api_key, merchant_id)

        return {"success": True, "provider": type(provider).__name__}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

## Environment Variables (Optional)

```bash
# Only these are needed (no STRIPE_PROVIDER_TYPE!)
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret

# Optional HTTP provider settings
STRIPE_API_BASE_URL=https://api.stripe.com/v1
STRIPE_API_VERSION=2023-10-16
```

## Testing

```python
def test_provider_creation():
    """Test different ways to create providers."""

    # Test direct creation
    http = create_stripe_http_provider("sk_test")
    sdk = create_stripe_sdk_provider("sk_test", "merchant")

    assert isinstance(http, StripeHTTPProvider)
    assert isinstance(sdk, StripePaymentProvider)

    # Test factory with enum
    http2 = create_stripe_provider("sk_test", ProviderType.HTTP)
    sdk2 = create_stripe_provider("sk_test", ProviderType.SDK)

    assert isinstance(http2, StripeHTTPProvider)
    assert isinstance(sdk2, StripePaymentProvider)
```

## Summary

- ✅ **No environment variables** needed for provider selection
- ✅ **Parameter-based** provider choice
- ✅ **Use both providers** in same application
- ✅ **Direct creation** methods available
- ✅ **Factory methods** for flexibility
- ✅ **Type-safe enums** for provider selection
