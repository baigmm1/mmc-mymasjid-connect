# External Providers

This directory contains integrations with external service providers.

## Available Providers

### 1. Stripe Payment Provider

**File**: `stripe_payment_provider.py`

Handles payment processing through Stripe, including:

- Customer management
- Payment intents (terminal and online)
- Refunds
- Payment method handling

**Configuration**:

- Configured per company via database provider configuration
- API keys and merchant IDs stored in provider configuration

**Usage**:

```python
from src.providers.stripe_payment_provider import StripePaymentProvider

provider = StripePaymentProvider(api_key="sk_test_...", merchant_id="acct_...")
customer = await provider.get_customer(email="donor@example.com")
```

### 2. SendGrid Email Provider

**File**: `sendgrid_email_provider.py`

Handles email sending through SendGrid API, including:

- Simple transactional emails (HTML and plain text)
- Template-based emails (using SendGrid dynamic templates)
- Bulk email sending
- Attachments and CC/BCC support
- Custom tracking arguments

**Configuration**:
Environment variables required:

- `SENDGRID_API_KEY`: Your SendGrid API key
- `SENDGRID_FROM_EMAIL`: Default sender email address (must be verified in SendGrid)
- `SENDGRID_FROM_NAME`: Default sender name (optional, defaults to "Masjid Connect")

### 3. Auth0 Provider

**File**: `auth0_provider.py`

Handles user profile retrieval from Auth0, including:

- User information from Auth0 userinfo endpoint
- Email extraction
- Profile data retrieval
- Support for OIDC standard and custom claims

**Configuration**:
Environment variable required:

- `AUTH0_DOMAIN`: Your Auth0 tenant domain (e.g., "masjidconnect.auth0.com")

**Usage**:

```python
from src.providers.auth0_provider import get_auth0_provider

# Create provider instance
auth0_provider = get_auth0_provider()

# Fetch full user info
user_info = await auth0_provider.get_user_info(access_token)

# Or get specific profile data
profile = await auth0_provider.get_user_profile(access_token)
# Returns: {"user_id": "...", "email": "...", "name": "...", ...}

# Or just get email
email = await auth0_provider.get_user_email(access_token)
```

**Reference**: [Auth0 User Profile API Documentation](https://auth0.com/docs/api/authentication/user-profile/get-user-info)

**Usage**:

```python
from src.providers.sendgrid_email_provider import get_sendgrid_provider

# Get provider instance
provider = await get_sendgrid_provider()

# Send simple email
result = await provider.send_email(
    to_email="recipient@example.com",
    to_name="John Doe",
    subject="Welcome!",
    html_content="<h1>Welcome to Masjid Connect</h1>",
    plain_text_content="Welcome to Masjid Connect"
)

# Send template email
result = await provider.send_template_email(
    to_email="recipient@example.com",
    template_id="d-1234567890abcdef",
    dynamic_template_data={
        "first_name": "John",
        "amount": "$100.00"
    }
)

# Send bulk emails
result = await provider.send_bulk_emails(
    recipients=[
        {"email": "user1@example.com", "name": "User 1"},
        {"email": "user2@example.com", "name": "User 2"},
    ],
    subject="Announcement",
    html_content="<p>Important announcement</p>"
)
```

**Example Use Cases**:
See `sendgrid_email_example.py` for complete examples:

- Donation receipt emails
- Bulk announcement emails
- Custom email endpoints

## Adding New Providers

When adding a new external provider integration:

1. **Create Provider File**: Create a new file following the naming pattern `{service}_provider.py`

2. **Provider Class Structure**:

   ```python
   class ServiceProvider:
       def __init__(self, api_key: str, **kwargs):
           """Initialize with credentials"""
           self.api_key = api_key
           # Setup client/SDK

       async def method_name(self, params):
           """Implement provider methods"""
           try:
               # Call external API
               # Log operations
               # Return results
           except Exception as e:
               logger.error("Error message", exc_info=True)
               raise
   ```

3. **Add Configuration**: Update `src/config.py` to add required environment variables

4. **Document in ENV_REFERENCE.md**: Add documentation for all new environment variables

5. **Create Factory Function**: Provide a `get_{service}_provider()` function for easy instantiation

6. **Add Tests**: Create tests in `tests/unit/providers/` or `tests/integration/providers/`

7. **Update This README**: Document the new provider

## Best Practices

### Error Handling

- Always catch provider-specific exceptions
- Log errors with appropriate context
- Re-raise exceptions for caller to handle
- Use structured logging with extra fields

### Logging

- Log successful operations at INFO level
- Log errors at ERROR level with `exc_info=True`
- Include relevant context (email addresses, transaction IDs, etc.)
- Use logger from `src.core.logging`

### Security

- Never hardcode API keys or credentials
- Use environment variables or secure configuration storage
- Validate inputs before passing to external APIs
- Sanitize sensitive data in logs

### Async Operations

- Use async/await for all I/O operations
- Handle network timeouts appropriately
- Consider retry logic for transient failures

### Configuration

- Support both default and override values
- Validate configuration on initialization
- Provide clear error messages for missing config

## Testing

### Unit Tests

Test provider logic with mocked external APIs:

```python
from unittest.mock import AsyncMock, patch

@patch('sendgrid.SendGridAPIClient')
async def test_send_email(mock_client):
    mock_client.return_value.send = AsyncMock(return_value=mock_response)
    provider = SendGridEmailProvider(api_key="test", from_email="test@example.com")
    result = await provider.send_email(...)
    assert result["success"] == True
```

### Integration Tests

Test actual provider integration in controlled environment:

- Use test API keys
- Test against sandbox/test environments
- Verify actual API responses

## Dependencies

Providers may require additional Python packages. Add to `requirements.in`:

```
# Provider dependencies
stripe
sendgrid
```

Then regenerate `requirements.txt`:

```bash
pip-compile requirements.in
```

## Monitoring and Observability

- All providers use structured logging
- Track success/failure rates
- Monitor API response times
- Alert on error rate thresholds
- Use custom_args for email tracking in SendGrid

## Support and Documentation

- **Stripe**: https://stripe.com/docs/api
- **SendGrid**: https://docs.sendgrid.com/
- **Internal Docs**: See `/docs` directory for detailed guides
