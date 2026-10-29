"""
Webhook service for processing Stripe webhook events.

Handles different types of Stripe webhook events including invoice.paid,
payout.paid, and checkout.session.completed. Provides separate processing
methods for each event type.
"""

from datetime import datetime
from typing import Any, Dict

from src.config import settings
from src.core.logging import get_logger
from src.models.webhook import StripeWebhookRequest, WebhookEventSummary
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.transaction_utils import (
    create_transaction_from_stripe_checkout_session,
    process_stripe_invoice_paid,
    process_stripe_payout_paid,
)
from src.core.provider_manager import get_stripe_provider, get_email_provider

logger = get_logger(__name__, level=settings.LOG_LEVEL)


class WebhookService:
    """Service for processing Stripe webhook events."""
    
    SUPPORTED_EVENT_TYPES = {
        "invoice.paid": "process_invoice_paid",
        "payout.paid": "process_payout_paid", 
        "checkout.session.completed": "process_checkout_session_completed"
    }
    
    def __init__(self):
        """Initialize webhook service."""
        self.logger = get_logger(__name__, level=settings.LOG_LEVEL)
        self.session: AsyncSession = None  # type: ignore
    
    async def process_webhook_event(            
        self, 
        session: AsyncSession,
        webhook_data: StripeWebhookRequest, 
        company_id: int,
        ignore: bool = False,
    ) -> WebhookEventSummary:
        """
        Process a Stripe webhook event.
        
        Args:
            webhook_data: The Stripe webhook payload
            company_id: The company ID from the URL
            ignore: Whether to ignore processing (receive but don't process)
            session: Database session for async operations
            
        Returns:
            WebhookEventSummary: Summary of the processing result
        """
        event_summary = WebhookEventSummary(
            event_id=webhook_data.id,
            event_type=webhook_data.type,
            company_id=company_id,
            received_at=datetime.utcnow(),
            processed=False,
            ignore_flag=ignore
        )
        
        # self.logger.info(
        #     f"Received webhook event: {webhook_data.type} for company {company_id}",
        #     extra={
        #         "event_id": webhook_data.id,
        #         "event_type": webhook_data.type,
        #         "company_id": company_id,
        #         "ignore": ignore
        #     }
        # )
        
        # If ignore flag is set, just log and return without processing
        if ignore:
            self.logger.info(
                f"Ignoring webhook event {webhook_data.id} due to ignore flag",
                extra={"event_id": webhook_data.id, "company_id": company_id}
            )
            return event_summary
        
        # Check if event type is supported
        if webhook_data.type not in self.SUPPORTED_EVENT_TYPES:
            self.logger.warning(
                f"Unsupported webhook event type: {webhook_data.type}",
                extra={
                    "event_id": webhook_data.id,
                    "event_type": webhook_data.type,
                    "company_id": company_id
                }
            )
            return event_summary
        
        # Process the event based on type
        try:
            self.session = session
            processor_method = getattr(self, self.SUPPORTED_EVENT_TYPES[webhook_data.type])
            await processor_method(webhook_data, company_id)
            event_summary.processed = True
            
            # self.logger.info(
            #     f"Successfully processed webhook event: {webhook_data.id}",
            #     extra={
            #         "event_id": webhook_data.id,
            #         "event_type": webhook_data.type,
            #         "company_id": company_id
            #     }
            # )
            
        except Exception as e:
            self.logger.error(
                f"Error processing webhook event {webhook_data.id}: {str(e)}",
                extra={
                    "event_id": webhook_data.id,
                    "event_type": webhook_data.type,
                    "company_id": company_id,
                    "error": str(e)
                },
                exc_info=True
            )
            # Don't mark as processed if there was an error
        
        return event_summary
    
    async def process_invoice_paid(self, webhook_data: StripeWebhookRequest, company_id: int) -> None:
        """
        Process invoice.paid webhook event.
        
        This event is triggered when an invoice is successfully paid.
        
        Args:
            webhook_data: The Stripe webhook payload
            company_id: The company ID
        """
        try:
            invoice_data = webhook_data.data.get("object", {})
            invoice_id = invoice_data.get("id")
            billing_reason = invoice_data.get("billing_reason", "unknown")
            if billing_reason != "subscription_cycle":
                self.logger.warning(
                    f"Invoice {invoice_id} has billing reason '{billing_reason}', skipping processing",
                    extra={
                        "event_id": webhook_data.id,
                        "invoice_id": invoice_id,
                        "company_id": company_id,
                        "billing_reason": billing_reason
                    }
                )
                return
            
            # Get Stripe payment provider (cached/singleton)
            stripe_provider = await get_stripe_provider(
                session=self.session,
                company_id=company_id
            )

            invoice = await stripe_provider.get_invoice(invoice_id=invoice_id, expand=["customer", "payments", "parent.subscription_details.subscription"])

            # Call utility function for processing
            result = await process_stripe_invoice_paid(
                session=self.session,
                invoice_data=invoice,
                company_id=company_id,
                event_id=webhook_data.id,
                stripe_provider=stripe_provider
            )
            
            # self.logger.info(
            #     f"Invoice paid event processed: {result.get('message')}",
            #     extra={
            #         "event_id": webhook_data.id,
            #         "invoice_id": invoice_id,
            #         "company_id": company_id
            #     }
            # )
        except Exception as e:
            self.logger.error(
                f"Error processing Invoice Paid event: {str(e)}",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "event_id": webhook_data.id,
                    "invoice_id": invoice_id,
                    "company_id": company_id
                },
                exc_info=True,
            )
            raise e
    
    
    async def process_payout_paid(self, webhook_data: StripeWebhookRequest, company_id: int) -> None:
        """
        Process payout.paid webhook event.
        
        This event is triggered when a payout has been paid out.
        
        Args:
            webhook_data: The Stripe webhook payload
            company_id: The company ID
        """
        try:
            payout_data = webhook_data.data.get("object", {})
            payout_id = payout_data.get("id")

            stripe_provider = await get_stripe_provider(
                session=self.session,
                company_id=company_id
            )

            # Call utility function for processing
            result = await process_stripe_payout_paid(
                session=self.session,
                payout_id=payout_id,
                company_id=company_id,
                stripe_provider=stripe_provider,
                event_id=webhook_data.id
            )
            
            self.logger.info(
                f"Payout paid event processed: {result.get('message')}",
                extra={
                    "event_id": webhook_data.id,
                    "payout_id": payout_id,
                    "company_id": company_id
                }
            )
        except Exception as e:
            self.logger.error(
                f"Error processing payout paid event: {str(e)}",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "event_id": webhook_data.id,
                    "payout_id": payout_id,
                    "company_id": company_id
                },
                exc_info=True,
            )
            raise e
    
    async def process_checkout_session_completed(self, webhook_data: StripeWebhookRequest, company_id: int) -> None:
        """
        Process checkout.session.completed webhook event.
        
        This event is triggered when a checkout session is successfully completed.
        
        Args:
            webhook_data: The Stripe webhook payload
            company_id: The company ID
        """
        try:
            session_data = webhook_data.data.get("object", {})
            checkout_session_id = session_data.get("id")
            
            self.logger.info(
                f"Processing checkout.session.completed event for session {checkout_session_id}",
                extra={
                    "event_id": webhook_data.id,
                    "session_id": checkout_session_id,
                    "company_id": company_id
                }
            )
            
            # Get Stripe payment provider (cached/singleton)
            stripe_provider = await get_stripe_provider(
                session=self.session,
                company_id=company_id
            )
            
            # Retrieve checkout session from Stripe with expanded details
            checkout_session = await stripe_provider.get_checkout_session(
                session_id=checkout_session_id,
                expand=["line_items", "customer"]
            )
            
            # Use utility function to create transaction
            transaction = await create_transaction_from_stripe_checkout_session(
                session=self.session,
                checkout_session=checkout_session,
                company_id=company_id,
                event_id=webhook_data.id
            )

            # Optional: Send receipt email if configured
            # if settings.SEND_EMAILS and transaction.DonorEmail:
            #     logger.info(
            #         f"Sending receipt email for transaction {transaction.TransactionId}",
            #         extra={"transaction_id": transaction.TransactionId, "email": transaction.DonorEmail}
            #     )            
            #     await send_transaction_receipt(transaction.TransactionId, session=self.session)

            self.logger.info(
                f"Checkout session completed processing finished for session {checkout_session_id}",
                extra={
                    "event_id": webhook_data.id,
                    "session_id": checkout_session_id,
                    "transaction_id": transaction.TransactionId,
                    "company_id": company_id
                }
            )
        except Exception as e:
            logger.error(
                f"Error processing checkout session: {str(e)}",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "event_id": webhook_data.id,
                    "company_id": company_id
                },
                exc_info=True,
            )
            raise e


# Global service instance
webhook_service = WebhookService()