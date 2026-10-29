# Stripe Providers Documentation

This document describes how to use both Stripe HTTP Provider and SDK Provider based on your specific use case requirements.

## Overview

This application provides two Stripe provider options:

1. **HTTP Provider** - Direct API calls for complete data access
2. **SDK Provider** - Official Stripe Python SDK for convenience

**Key Feature:** Choose providers via **parameters**, not environment variables. Use different providers for different operations in the same application.

## Provider Selection Guide

### Use HTTP Provider When:

- ✅ Need complete Stripe API response data
- ✅ SDK is not returning all required fields
- ✅ Processing webhooks with unknown fields
- ✅ Building data analysis/export features
- ✅ Testing exact API response structures
- ✅ Need access to custom fields or metadata

### Use SDK Provider When:

- ✅ Want convenient built-in methods
- ✅ Need simplified error handling
- ✅ Basic payment processing operations
- ✅ Prefer official Stripe abstractions
- ✅ Don't need all response fields

## Quick Start Examples

### Method 1: Direct Provider Creation

```python
from src.providers.stripe_provider_factory import (
    create_stripe_http_provider,
    create_stripe_sdk_provider
)

# Create HTTP provider for complete data access
http_provider = create_stripe_http_provider("sk_test_your_key")

# Create SDK provider for convenience
sdk_provider = create_stripe_sdk_provider("sk_test_your_key", "merchant_id")
```

### Method 2: Factory with Provider Type

```python
from src.providers.stripe_provider_factory import (
    create_stripe_provider,
    ProviderType
)

# Using enum (recommended)
http_provider = create_stripe_provider("sk_test_key", ProviderType.HTTP)
sdk_provider = create_stripe_provider("sk_test_key", ProviderType.SDK, "merchant_id")

# Using strings
http_provider = create_stripe_provider("sk_test_key", "http")
sdk_provider = create_stripe_provider("sk_test_key", "sdk", "merchant_id")
```

## Detailed Usage Examples

### HTTP Provider - Complete Data Access

```python
async def get_complete_subscription_data():
    """Example: Get subscription with all fields."""

    async with create_stripe_http_provider("sk_test_key") as provider:
        # Get raw subscription data with expansions
        subscription_data = await provider.get_subscription(
            "sub_123",
            expand=["default_payment_method", "latest_invoice", "customer"]
        )

        # Access any field from Stripe API
        print(f"All fields: {list(subscription_data.keys())}")

        # Access nested data
        customer = subscription_data.get("customer", {})
        payment_method = subscription_data.get("default_payment_method", {})

        print(f"Customer email: {customer.get('email')}")
        print(f"Card brand: {payment_method.get('card', {}).get('brand')}")

        # Convert to model if needed
        model = await provider.get_subscription_as_model("sub_123")
        return model
```

### SDK Provider - Convenience Methods

```python
def simple_payment_operations():
    """Example: Basic operations with SDK."""

    provider = create_stripe_sdk_provider("sk_test_key", "merchant_123")

    # SDK provides convenient methods (example structure)
    # Note: Actual methods depend on your StripePaymentProvider implementation

    # Simple subscription retrieval
    subscription = provider.get_subscription_sync("sub_123")
    print(f"Status: {subscription.status}")

    return subscription
```

## Use Case Scenarios

### Webhook Processing (HTTP Provider Recommended)

```python
async def process_webhook(event_data):
    """Webhooks may contain fields not in SDK."""

    # Use HTTP provider to access complete webhook data
    async with create_stripe_http_provider(api_key) as provider:
        if event_data["type"] == "invoice.paid":
            invoice_id = event_data["data"]["object"]["id"]

            # Get complete invoice data
            invoice = await provider.get_invoice(
                invoice_id,
                expand=["subscription", "payment_intent"]
            )

            # Access any field from webhook
            custom_fields = invoice.get("custom_fields", [])
            metadata = invoice.get("metadata", {})

            return {"status": "processed", "metadata": metadata}
```

### Simple Payment Creation (SDK Provider Recommended)

```python
def create_payment():
    """Simple operations benefit from SDK convenience."""

    provider = create_stripe_sdk_provider(api_key, merchant_id)

    # Use SDK convenience methods for standard operations
    # (Implementation depends on your StripePaymentProvider)

    return {"status": "created"}
```

### Data Export (HTTP Provider Recommended)

```python
async def export_subscription_data():
    """Data analysis needs complete field access."""

    async with create_stripe_http_provider(api_key) as provider:
        subscriptions = []

        # Get complete data for analysis
        for sub_id in subscription_ids:
            data = await provider.get_subscription(
                sub_id,
                expand=["customer", "default_payment_method", "items"]
            )

            # Extract any fields for export
            export_data = {
                "id": data["id"],
                "customer_email": data.get("customer", {}).get("email"),
                "plan_name": data.get("items", {}).get("data", [{}])[0].get("price", {}).get("nickname"),
                "metadata": data.get("metadata", {}),
                # Access any other fields as needed
            }

            subscriptions.append(export_data)

        return subscriptions
```

## Configuration

### Environment Variables

```bash
# Required: Stripe credentials (same for both providers)
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret

# Optional: HTTP Provider settings
STRIPE_API_BASE_URL=https://api.stripe.com/v1    # Default
STRIPE_API_VERSION=2023-10-16                    # Default
```

**No `STRIPE_PROVIDER_TYPE` needed** - choose via parameters!

## Advanced Examples

### Dynamic Provider Selection

```python
def get_provider_for_use_case(use_case: str, api_key: str):
    """Select provider based on specific requirements."""

    data_intensive_cases = [
        "webhook_processing",
        "data_export",
        "integration_testing",
        "custom_field_access"
    ]

    if use_case in data_intensive_cases:
        return create_stripe_http_provider(api_key)
    else:
        return create_stripe_sdk_provider(api_key)

# Usage
provider = get_provider_for_use_case("webhook_processing", api_key)
```

### Mixed Usage in Same Application

```python
class PaymentService:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def get_complete_subscription(self, sub_id: str):
        """Use HTTP for complete data access."""
        async with create_stripe_http_provider(self.api_key) as provider:
            return await provider.get_subscription(sub_id)

    def simple_refund(self, charge_id: str):
        """Use SDK for simple operations."""
        provider = create_stripe_sdk_provider(self.api_key)
        # Use SDK convenience methods
        return provider.create_refund(charge_id)
```

## Error Handling

### HTTP Provider Errors

```python
async def handle_http_errors():
    async with create_stripe_http_provider(api_key) as provider:
        try:
            subscription = await provider.get_subscription("sub_123")
        except Exception as e:
            if "No such subscription" in str(e):
                print("Subscription not found")
            elif "invalid_request_error" in str(e):
                print("Invalid request")
            else:
                print(f"Unexpected error: {e}")
```

### SDK Provider Errors

```python
def handle_sdk_errors():
    provider = create_stripe_sdk_provider(api_key)
    try:
        # SDK operations
        pass
    except Exception as e:
        # SDK provides different error handling
        print(f"SDK Error: {e}")
```

## Performance Considerations

| Aspect            | HTTP Provider          | SDK Provider          |
| ----------------- | ---------------------- | --------------------- |
| **Response Size** | Complete (all fields)  | Filtered (SDK fields) |
| **Network Calls** | Direct HTTP            | SDK processing        |
| **Memory Usage**  | Higher (complete data) | Lower (filtered data) |
| **Processing**    | Manual parsing         | SDK abstractions      |

## Best Practices

### 1. Choose Based on Requirements

```python
# Data analysis → HTTP Provider
async with create_stripe_http_provider(api_key) as provider:
    data = await provider.get_subscription("sub_123")

# Simple operations → SDK Provider
provider = create_stripe_sdk_provider(api_key)
```

### 2. Use Async Context Managers for HTTP

```python
# Recommended
async with create_stripe_http_provider(api_key) as provider:
    # Operations
    pass
# Automatically closes connection

# Alternative
provider = create_stripe_http_provider(api_key)
try:
    # Operations
    pass
finally:
    await provider.close()
```

### 3. Expand Only What You Need

```python
# Good - specific expansions
subscription = await provider.get_subscription(
    "sub_123",
    expand=["default_payment_method"]
)

# Avoid - unnecessary expansions
subscription = await provider.get_subscription(
    "sub_123",
    expand=["customer", "default_payment_method", "items", "latest_invoice"]
)
```

## Testing

### Unit Tests

```bash
# Test both providers
python -m pytest tests/unit/test_stripe_http_provider.py -v
```

### Example Test

```python
def test_provider_selection():
    """Test creating different providers."""

    # Test direct creation
    http_provider = create_stripe_http_provider("sk_test_key")
    sdk_provider = create_stripe_sdk_provider("sk_test_key")

    assert isinstance(http_provider, StripeHTTPProvider)
    assert isinstance(sdk_provider, StripePaymentProvider)

    # Test factory creation
    http_via_factory = create_stripe_provider("sk_test_key", ProviderType.HTTP)
    sdk_via_factory = create_stripe_provider("sk_test_key", ProviderType.SDK)

    assert isinstance(http_via_factory, StripeHTTPProvider)
    assert isinstance(sdk_via_factory, StripePaymentProvider)
```

## Migration Guide

### From Environment-Based to Parameter-Based

```python
# Before (environment-based)
# Set STRIPE_PROVIDER_TYPE=http
provider = create_stripe_provider(api_key)

# After (parameter-based)
provider = create_stripe_provider(api_key, ProviderType.HTTP)
# OR
provider = create_stripe_http_provider(api_key)
```

## Summary

- ✅ **No environment variables needed for provider selection**
- ✅ **Choose provider via parameters based on use case**
- ✅ **Use both providers in same application**
- ✅ **HTTP Provider for complete data access**
- ✅ **SDK Provider for convenience and simplicity**
- ✅ **Dynamic selection based on requirements**

Choose the right tool for each job - HTTP for complete data, SDK for convenience!
