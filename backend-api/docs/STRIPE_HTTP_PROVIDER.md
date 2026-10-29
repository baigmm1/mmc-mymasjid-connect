# Stripe HTTP Provider Documentation

This document describes the new Stripe HTTP Provider that makes direct API calls to Stripe endpoints without using the Python SDK.

## Overview

The Stripe HTTP Provider provides an alternative to the Stripe Python SDK by making direct HTTP requests to the Stripe API. This gives you complete control over the request/response data and ensures you have access to all fields returned by Stripe's API.

## When to Use HTTP Provider

**Use HTTP Provider when:**

- The Stripe Python SDK is not returning all the data you need
- You need access to the complete Stripe API response
- You want full control over request parameters and response parsing
- You need the latest Stripe API features before SDK support

**Use SDK Provider when:**

- You want simplified integration with built-in helpers
- You prefer Stripe's official Python abstractions
- You don't need access to all response fields

## Configuration

### Environment Variables

Add these settings to your environment:

```bash
# Required: Choose provider type
STRIPE_PROVIDER_TYPE=http          # "http" for HTTP provider, "sdk" for Python SDK

# Required: Your Stripe credentials
STRIPE_SECRET_KEY=sk_test_...       # Your Stripe secret key
STRIPE_PUBLISHABLE_KEY=pk_test_...  # Your Stripe publishable key

# Optional: HTTP Provider specific settings
STRIPE_API_BASE_URL=https://api.stripe.com/v1    # Default Stripe API base URL
STRIPE_API_VERSION=2023-10-16                    # Stripe API version
```

### Provider Selection

The system automatically selects the appropriate provider based on `STRIPE_PROVIDER_TYPE`:

```python
from src.providers.stripe_provider_factory import create_stripe_provider

# Factory automatically returns HTTP or SDK provider based on config
provider = create_stripe_provider(api_key="sk_test_...", merchant_id="optional")

# Or create HTTP provider directly
from src.providers.stripe_http_provider import StripeHTTPProvider
http_provider = StripeHTTPProvider(api_key="sk_test_...")
```

## HTTP Provider Features

### Direct API Access

```python
async with StripeHTTPProvider(api_key) as provider:
    # Get complete subscription data with expansions
    subscription_data = await provider.get_subscription(
        "sub_123",
        expand=["default_payment_method", "latest_invoice.payment_intent"]
    )

    # Access any field returned by Stripe API
    payment_method = subscription_data.get("default_payment_method", {})
    card_details = payment_method.get("card", {})
    print(f"Card last 4: {card_details.get('last4')}")
```

### Model Conversion

```python
# Convert to SubscriptionModel with proper field mapping
subscription_model = await provider.get_subscription_as_model("sub_123")

print(f"ID: {subscription_model.id}")
print(f"Customer: {subscription_model.customer}")
print(f"Created: {subscription_model.created_datetime}")
print(f"Payment Method: {subscription_model.payment_method_desc}")
```

### Comprehensive Error Handling

```python
try:
    subscription = await provider.get_subscription("invalid_sub")
except Exception as e:
    # Detailed error information from Stripe API
    print(f"Error: {e}")
    # Example: "Stripe subscription retrieval failed: No such subscription: invalid_sub (Type: invalid_request_error, Code: resource_missing)"
```

## Available Methods

### Subscription Operations

```python
# Get subscription with full API response
raw_data = await provider.get_subscription(
    subscription_id="sub_123",
    expand=["default_payment_method", "latest_invoice"]
)

# Get subscription as SubscriptionModel
model = await provider.get_subscription_as_model("sub_123")
```

### Customer Operations

```python
# Get customer data
customer_data = await provider.get_customer("cus_123")
print(f"Email: {customer_data.get('email')}")
print(f"Name: {customer_data.get('name')}")
```

### Invoice Operations

```python
# Get invoice with expansions
invoice_data = await provider.get_invoice(
    "in_123",
    expand=["payment_intent", "subscription"]
)
```

## Comparison: HTTP vs SDK Provider

| Feature             | HTTP Provider          | SDK Provider          |
| ------------------- | ---------------------- | --------------------- |
| **Data Access**     | Complete API response  | SDK-filtered response |
| **Field Coverage**  | All Stripe API fields  | Limited to SDK models |
| **API Updates**     | Immediate access       | Requires SDK update   |
| **Error Details**   | Full Stripe error info | SDK-processed errors  |
| **Request Control** | Complete control       | SDK abstractions      |
| **Code Complexity** | More verbose           | Simplified            |
| **Performance**     | Direct HTTP calls      | SDK overhead          |

## Usage Examples

### Basic Subscription Retrieval

```python
import asyncio
from src.providers.stripe_provider_factory import create_stripe_provider

async def get_subscription_info():
    provider = create_stripe_provider("sk_test_your_key")

    if hasattr(provider, 'get_subscription'):  # HTTP provider
        # Get complete data
        data = await provider.get_subscription("sub_123")
        print(f"Complete data keys: {list(data.keys())}")

        # Get as model
        model = await provider.get_subscription_as_model("sub_123")
        print(f"Model: {model}")

        await provider.close()

asyncio.run(get_subscription_info())
```

### Accessing Expanded Data

```python
async def get_detailed_subscription():
    async with StripeHTTPProvider("sk_test_key") as provider:
        subscription = await provider.get_subscription(
            "sub_123",
            expand=[
                "default_payment_method",
                "latest_invoice",
                "latest_invoice.payment_intent",
                "customer"
            ]
        )

        # Access nested data that might not be available in SDK
        customer = subscription.get("customer", {})
        payment_method = subscription.get("default_payment_method", {})
        invoice = subscription.get("latest_invoice", {})

        print(f"Customer email: {customer.get('email')}")
        print(f"Card brand: {payment_method.get('card', {}).get('brand')}")
        print(f"Invoice status: {invoice.get('status')}")
```

### Error Handling

```python
async def handle_errors():
    async with StripeHTTPProvider("sk_test_key") as provider:
        try:
            subscription = await provider.get_subscription("invalid_id")
        except Exception as e:
            if "No such subscription" in str(e):
                print("Subscription not found")
            elif "invalid_request_error" in str(e):
                print("Invalid request")
            else:
                print(f"Unexpected error: {e}")
```

## Migration Guide

### From SDK to HTTP Provider

1. **Update Configuration:**

   ```bash
   STRIPE_PROVIDER_TYPE=http
   ```

2. **Update Code:**

   ```python
   # Before (SDK)
   subscription = stripe.Subscription.retrieve("sub_123")
   customer_id = subscription.customer

   # After (HTTP)
   subscription = await provider.get_subscription("sub_123")
   customer_id = subscription.get("customer")
   ```

3. **Handle Async Operations:**

   ```python
   # HTTP provider uses async/await
   subscription = await provider.get_subscription("sub_123")
   ```

4. **Update Field Access:**
   ```python
   # SDK might filter fields, HTTP provides complete response
   all_fields = subscription.keys()  # See what's available
   ```

## Testing

### Unit Tests

```bash
# Test HTTP provider
python -m pytest tests/unit/test_stripe_http_provider.py -v

# Test provider factory
python -m pytest tests/unit/test_stripe_http_provider.py::TestStripeProviderFactory -v
```

### Manual Testing

```bash
# Run example script
python stripe_http_example.py
```

### Environment Setup for Testing

```bash
export STRIPE_PROVIDER_TYPE=http
export STRIPE_SECRET_KEY=sk_test_your_test_key
export STRIPE_API_VERSION=2023-10-16
```

## Best Practices

### 1. Use Async Context Manager

```python
async with StripeHTTPProvider(api_key) as provider:
    # Operations here
    pass
# Automatically closes HTTP client
```

### 2. Handle Network Errors

```python
try:
    data = await provider.get_subscription("sub_123")
except httpx.RequestError as e:
    print(f"Network error: {e}")
except Exception as e:
    print(f"API error: {e}")
```

### 3. Use Expansions Wisely

```python
# Expand only what you need to reduce response size
subscription = await provider.get_subscription(
    "sub_123",
    expand=["default_payment_method"]  # Only expand needed fields
)
```

### 4. Log for Debugging

The HTTP provider provides comprehensive logging:

```python
# Logs include:
# - Request URLs and parameters
# - Response status codes
# - Error details with context
# - Data size information
```

## Performance Considerations

- **HTTP Overhead:** Direct HTTP calls may have slight overhead vs SDK
- **Response Size:** Expanded responses can be large - expand only needed fields
- **Connection Reuse:** HTTP client reuses connections for efficiency
- **Timeouts:** 30-second timeout for API calls (configurable)

## Security Notes

- Always use HTTPS (enforced by default)
- API keys are sent in Authorization header
- Never log API keys or sensitive data
- Use environment variables for credentials

## Troubleshooting

### Common Issues

1. **Provider Type Not Recognized**

   ```
   Solution: Check STRIPE_PROVIDER_TYPE environment variable
   ```

2. **Network Timeout**

   ```
   Solution: Check network connectivity and Stripe API status
   ```

3. **Invalid API Key**

   ```
   Solution: Verify STRIPE_SECRET_KEY format and permissions
   ```

4. **Missing Fields in Response**
   ```
   Solution: Use expand parameter or check Stripe API documentation
   ```

### Debug Mode

Enable detailed logging:

```bash
export LOG_LEVEL=DEBUG
```

This will show:

- Full request URLs and headers
- Response data sizes
- Processing time information
- Detailed error context

## Support

- **Stripe API Documentation:** https://docs.stripe.com/api
- **HTTP Status Codes:** https://docs.stripe.com/api/errors
- **API Versioning:** https://docs.stripe.com/api/versioning
