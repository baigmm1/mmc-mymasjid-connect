"""
Unit tests for webhook service and endpoints.

Tests verify webhook processing logic in isolation,
without external dependencies.

Test markers:
- @pytest.mark.unit: Unit test (isolated component testing)
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.models.webhook import StripeWebhookRequest, WebhookEventSummary
from src.services.webhook_service import WebhookService


@pytest.mark.unit
class TestWebhookService:
    """Unit tests for webhook service."""

    @pytest.fixture
    def webhook_service(self):
        """Create webhook service instance for testing."""
        return WebhookService()

    @pytest.fixture
    def sample_stripe_invoice_paid_event(self):
        """Sample Stripe invoice.paid webhook event."""
        return StripeWebhookRequest(
            id="evt_test_webhook_invoice_paid",
            object="event",
            api_version="2023-10-16",
            created=1640995200,  # Jan 1, 2022
            data={
                "object": {
                    "id": "in_test_invoice_123",
                    "customer": "cus_test_customer_456",
                    "amount_paid": 2000,  # $20.00 in cents
                    "status": "paid"
                }
            },
            livemode=False,
            pending_webhooks=1,
            request={"id": "req_test_123", "idempotency_key": "test_key"},
            type="invoice.paid"
        )

    @pytest.fixture
    def sample_stripe_payout_paid_event(self):
        """Sample Stripe payout.paid webhook event."""
        return StripeWebhookRequest(
            id="evt_test_webhook_payout_paid",
            object="event",
            api_version="2023-10-16",
            created=1640995200,
            data={
                "object": {
                    "id": "po_test_payout_123",
                    "amount": 50000,  # $500.00 in cents
                    "currency": "usd",
                    "arrival_date": 1641081600,  # Jan 2, 2022
                    "status": "paid"
                }
            },
            livemode=False,
            pending_webhooks=1,
            request=None,
            type="payout.paid"
        )

    @pytest.fixture
    def sample_stripe_checkout_completed_event(self):
        """Sample Stripe checkout.session.completed webhook event."""
        return StripeWebhookRequest(
            id="evt_test_webhook_checkout_completed",
            object="event",
            api_version="2023-10-16",
            created=1640995200,
            data={
                "object": {
                    "id": "cs_test_session_123",
                    "customer": "cus_test_customer_789",
                    "payment_intent": "pi_test_intent_123",
                    "amount_total": 3000,  # $30.00 in cents
                    "currency": "usd",
                    "status": "complete"
                }
            },
            livemode=False,
            pending_webhooks=1,
            request=None,
            type="checkout.session.completed"
        )

    @pytest.mark.asyncio
    async def test_process_webhook_event_with_ignore_flag(self, webhook_service, sample_stripe_invoice_paid_event):
        """Test that events with ignore=True are received but not processed."""
        result = await webhook_service.process_webhook_event(
            webhook_data=sample_stripe_invoice_paid_event,
            company_id="test_company_123",
            ignore=True
        )

        assert isinstance(result, WebhookEventSummary)
        assert result.event_id == "evt_test_webhook_invoice_paid"
        assert result.event_type == "invoice.paid"
        assert result.company_id == "test_company_123"
        assert result.processed is False
        assert result.ignore_flag is True

    @pytest.mark.asyncio
    async def test_process_webhook_event_unsupported_type(self, webhook_service):
        """Test handling of unsupported webhook event types."""
        unsupported_event = StripeWebhookRequest(
            id="evt_test_unsupported",
            object="event",
            api_version="2023-10-16",
            created=1640995200,
            data={"object": {"id": "test_123"}},
            livemode=False,
            pending_webhooks=1,
            request=None,
            type="customer.created"  # Unsupported type
        )

        result = await webhook_service.process_webhook_event(
            webhook_data=unsupported_event,
            company_id="test_company_123",
            ignore=False
        )

        assert result.processed is False
        assert result.event_type == "customer.created"

    @pytest.mark.asyncio
    async def test_process_invoice_paid_event(self, webhook_service, sample_stripe_invoice_paid_event):
        """Test processing of invoice.paid event."""
        with patch.object(webhook_service, 'process_invoice_paid', new_callable=AsyncMock) as mock_process:
            result = await webhook_service.process_webhook_event(
                webhook_data=sample_stripe_invoice_paid_event,
                company_id="test_company_123",
                ignore=False
            )

            mock_process.assert_called_once_with(sample_stripe_invoice_paid_event, "test_company_123")
            assert result.processed is True

    @pytest.mark.asyncio
    async def test_process_payout_paid_event(self, webhook_service, sample_stripe_payout_paid_event):
        """Test processing of payout.paid event."""
        with patch.object(webhook_service, 'process_payout_paid', new_callable=AsyncMock) as mock_process:
            result = await webhook_service.process_webhook_event(
                webhook_data=sample_stripe_payout_paid_event,
                company_id="test_company_123",
                ignore=False
            )

            mock_process.assert_called_once_with(sample_stripe_payout_paid_event, "test_company_123")
            assert result.processed is True

    @pytest.mark.asyncio
    async def test_process_checkout_session_completed_event(self, webhook_service, sample_stripe_checkout_completed_event):
        """Test processing of checkout.session.completed event."""
        with patch.object(webhook_service, 'process_checkout_session_completed', new_callable=AsyncMock) as mock_process:
            result = await webhook_service.process_webhook_event(
                webhook_data=sample_stripe_checkout_completed_event,
                company_id="test_company_123",
                ignore=False
            )

            mock_process.assert_called_once_with(sample_stripe_checkout_completed_event, "test_company_123")
            assert result.processed is True

    @pytest.mark.asyncio
    async def test_process_invoice_paid_stub(self, webhook_service, sample_stripe_invoice_paid_event):
        """Test the invoice paid processing stub executes without error."""
        # This test verifies the stub method runs successfully
        await webhook_service.process_invoice_paid(sample_stripe_invoice_paid_event, "test_company_123")
        # No assertion needed - if no exception is raised, test passes

    @pytest.mark.asyncio
    async def test_process_payout_paid_stub(self, webhook_service, sample_stripe_payout_paid_event):
        """Test the payout paid processing stub executes without error."""
        # This test verifies the stub method runs successfully
        await webhook_service.process_payout_paid(sample_stripe_payout_paid_event, "test_company_123")
        # No assertion needed - if no exception is raised, test passes

    @pytest.mark.asyncio
    async def test_process_checkout_session_completed_stub(self, webhook_service, sample_stripe_checkout_completed_event):
        """Test the checkout session completed processing stub executes without error."""
        # This test verifies the stub method runs successfully
        await webhook_service.process_checkout_session_completed(sample_stripe_checkout_completed_event, "test_company_123")
        # No assertion needed - if no exception is raised, test passes

    @pytest.mark.asyncio
    async def test_supported_event_types_mapping(self, webhook_service):
        """Test that supported event types map to correct processor methods."""
        expected_mapping = {
            "invoice.paid": "process_invoice_paid",
            "payout.paid": "process_payout_paid", 
            "checkout.session.completed": "process_checkout_session_completed"
        }
        
        assert webhook_service.SUPPORTED_EVENT_TYPES == expected_mapping
        
        # Verify all mapped methods exist
        for event_type, method_name in expected_mapping.items():
            assert hasattr(webhook_service, method_name)
            assert callable(getattr(webhook_service, method_name))