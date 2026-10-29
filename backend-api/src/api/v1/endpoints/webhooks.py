"""
Stripe webhook endpoints for processing payment events.

Provides POST endpoints for receiving and processing Stripe webhook events
including invoice.paid, payout.paid, and checkout.session.completed events.

Endpoints:
    POST /api/v1/webhooks/stripe/{company_id} - Process Stripe webhook for specific company
"""

import datetime
from typing import Optional

import stripe
from stripe import error as stripe_error
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from src.config import settings
from src.core.provider_config_utils import get_provider_config
from src.core.logging import CorrelationIdFilter, get_logger
from src.models.webhook import (
    StripeWebhookRequest,
    WebhookProcessingResponse,
)
from src.services.webhook_service import webhook_service
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.core.cache_manager import get_company_from_cache
from src.core.transaction_utils import (
    process_stripe_payout_paid,
    process_stripe_invoice_paid
)
from src.core.provider_manager import get_stripe_provider

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = get_logger(__name__, level=settings.LOG_LEVEL)


@router.post(
    "/stripe/{company_id}",
    response_model=WebhookProcessingResponse,
    status_code=200,
    summary="Process Stripe webhook",
    description="Process Stripe webhook events for a specific company. Supports invoice.paid, payout.paid, and checkout.session.completed events.",
)
async def process_stripe_webhook(
    company_id: int,
    webhook_data: StripeWebhookRequest,
    ignore: bool = Query(False, description="If true, receive event but don't process it"),
    request: Request = None, # type: ignore
    session: AsyncSession = Depends(get_session),
) -> WebhookProcessingResponse:
    """
    Process Stripe webhook event for a specific company.
    
    This endpoint receives Stripe webhook events and processes them based on the event type.
    Currently supports:
    - invoice.paid: Triggered when an invoice is successfully paid
    - payout.paid: Triggered when a payout has been paid out  
    - checkout.session.completed: Triggered when a checkout session is completed
    
    The endpoint includes an 'ignore' parameter that allows receiving events
    without processing them, useful for testing or temporary event suspension.
    
    Args:
        company_id: The ID of the company this webhook is for
        webhook_data: The Stripe webhook payload
        ignore: If true, event is received but not processed
        request: FastAPI request object (injected)
        
    Returns:
        WebhookProcessingResponse: Processing result with status and details
        
    Raises:
        HTTPException: If company_id is invalid or processing fails critically
    """
    correlation_id = CorrelationIdFilter.get_correlation_id() or "webhook-unknown"
    
    # Validate company_id format (basic validation)
        
    if not company_id:
        logger.error(
            "Invalid company_id provided in webhook URL",
            extra={
                "company_id": company_id,
                "event_id": webhook_data.id,
                "event_type": webhook_data.type,
                "correlation_id": correlation_id
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid company_id in URL path"
        )
    
    company = await get_company_from_cache(company_id, session)
    if not company:
        logger.error(
            "Invalid company_id provided in webhook URL",
            extra={
                "company_id": company_id,
                "event_id": webhook_data.id,
                "event_type": webhook_data.type,
                "correlation_id": correlation_id
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid company_id in URL path"
        )

    # Verify Stripe webhook signature
    try:
        # Get the raw request body
        payload = await request.body()
        
        # Get the Stripe signature from headers
        sig_header = request.headers.get("Stripe-Signature")
        if not sig_header:
            logger.error(
                "Missing Stripe-Signature header",
                extra={
                    "company_id": company_id,
                    "correlation_id": correlation_id
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe-Signature header"
            )
        
        # Get webhook secret from provider configuration
        webhook_config = await get_provider_config(
            company_id=company_id,
            provider="StripeEndPoint",
            session=session
        )
        
        if not webhook_config or not webhook_config.APIKey:
            logger.error(
                "Webhook endpoint secret not configured",
                extra={
                    "company_id": company_id,
                    "correlation_id": correlation_id
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook endpoint not configured for this company"
            )
        
        # Verify the signature using Stripe's library
        try:
            stripe.Webhook.construct_event(
                payload=payload,
                sig_header=sig_header,
                secret=webhook_config.APIKey
            )
            logger.info(
                "Webhook signature verified successfully",
                extra={
                    "company_id": company_id,
                    "event_id": webhook_data.id,
                    "event_type": webhook_data.type,
                    "correlation_id": correlation_id
                }
            )
        except stripe_error.SignatureVerificationError as e:
            logger.error(
                f"Webhook signature verification failed: {str(e)}",
                extra={
                    "company_id": company_id,
                    "correlation_id": correlation_id,
                    "error": str(e)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error during signature verification: {str(e)}",
            extra={
                "company_id": company_id,
                "correlation_id": correlation_id,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying webhook signature"
        )

    # Log webhook receipt
    logger.info(
        f"Received Stripe webhook for company {company_id}",
        extra={
            "company_id": company_id,
            "event_id": webhook_data.id,
            "event_type": webhook_data.type,
            "ignore": ignore,
            "correlation_id": correlation_id,
            "livemode": webhook_data.livemode,
        }
    )
    
    try:
        # Process the webhook event
        event_summary = await webhook_service.process_webhook_event(
            webhook_data=webhook_data,
            company_id=company_id,
            ignore=ignore,
            session=session
        )
        
        # Create response
        response = WebhookProcessingResponse(
            success=True,
            message=f"Webhook event {webhook_data.type} processed successfully",
            event_id=webhook_data.id,
            event_type=webhook_data.type,
            company_id=company_id,
            processed=event_summary.processed,
            processing_timestamp=event_summary.received_at,
            correlation_id=correlation_id
        )
        
        # Log successful processing
        logger.info(
            f"Webhook processing completed for event {webhook_data.id}",
            extra={
                "company_id": company_id,
                "event_id": webhook_data.id,
                "event_type": webhook_data.type,
                "processed": event_summary.processed,
                "correlation_id": correlation_id
            }
        )
        
        return response
        
    except Exception as e:
        # Log error details
        logger.error(
            f"Critical error processing webhook {webhook_data.id}: {str(e)}",
            extra={
                "company_id": company_id,
                "event_id": webhook_data.id,
                "event_type": webhook_data.type,
                "error": str(e),
                "correlation_id": correlation_id
            },
            exc_info=True
        )
        
        # Return error response but don't raise HTTP exception
        # Stripe expects 200 status even on processing errors to avoid retries
        error_response = WebhookProcessingResponse(
            success=False,
            message=f"Error processing webhook event: {str(e)}",
            event_id=webhook_data.id,
            event_type=webhook_data.type,
            company_id=company_id,
            processed=False,
            processing_timestamp=event_summary.received_at if 'event_summary' in locals() else None, # type: ignore
            correlation_id=correlation_id
        )
        
        return JSONResponse(
            status_code=200,  # Stripe expects 200 even on processing errors
            content=error_response.model_dump()
        ) # type: ignore


@router.get(
    "/stripe/{company_id}/status",
    status_code=200,
    summary="Check webhook endpoint status",
    description="Simple health check endpoint for webhook processing status",
)
async def webhook_status(company_id: str):
    """
    Check webhook endpoint status for a company.
    
    This is a simple health check endpoint that can be used to verify
    that the webhook endpoint is accessible and responding.
    
    Args:
        company_id: The company ID to check status for
        
    Returns:
        dict: Status information
    """
    return {
        "status": "active",
        "company_id": company_id,
        "supported_events": list(webhook_service.SUPPORTED_EVENT_TYPES.keys()),
        "endpoint": f"/api/v1/webhooks/stripe/{company_id}",
        "timestamp": CorrelationIdFilter.get_correlation_id() or "status-check"
    }

@router.post(
    "/stripe/{company_id}/payout/{payout_id}",
    status_code=200,
    summary="Process payout for a given payout_id",
    description="Retrieve detailed information about a specific payout and process bank deposit."
)
async def process_stripe_payout(
    company_id: int,
    payout_id: str,
    session: AsyncSession = Depends(get_session)
) -> WebhookProcessingResponse:
    """
    Process a Stripe payout by retrieving its details and creating a bank deposit batch.
    
    Args:
        company_id: The ID of the company this payout is for
        payout_id: The ID of the Stripe payout to process   
        session: Database session (injected)    
    Returns:
        WebhookProcessingResponse: Processing result with status and details    
    Raises:
        HTTPException: If company_id is invalid or processing fails critically  
    """

    correlation_id = CorrelationIdFilter.get_correlation_id() or "webhook-unknown"
    
    # Validate company_id format (basic validation)
    try:
        if not company_id:
            logger.error(
                "Invalid company_id provided in webhook URL",
                extra={
                    "company_id": company_id,
                    "correlation_id": correlation_id
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid company_id in URL path"
            )
        
        company = await get_company_from_cache(company_id, session)
        if not company:
            logger.error(
                "Invalid company_id provided in webhook URL",
                extra={
                    "company_id": company_id,
                    "correlation_id": correlation_id
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid company_id in URL path"
            )
        
        # Process the payout using the webhook service
        stripe_provider = await get_stripe_provider(
            session=session,
            company_id=company_id
        )

        # Call utility function for processing
        result = await process_stripe_payout_paid(
            session=session,
            payout_id=payout_id,
            company_id=company_id,
            stripe_provider=stripe_provider,
            event_id=""
        )
        return WebhookProcessingResponse(
            success=True,
            message=f"Payout {payout_id} processed successfully",
            event_id="payout_paid_processing",  
            event_type="payout_paid",
            company_id=company_id,
            processed=True,
            processing_timestamp=datetime.datetime.now(),  # Could be set to current time or event time if available
            correlation_id=correlation_id
        )
    except Exception as e:
        # Log error details
        logger.error(
            f"Critical error processing for payout {payout_id}: {str(e)}",
            extra={
                "company_id": company_id,
                "payout_id": payout_id,
                "error": str(e),
                "correlation_id": correlation_id
            },
            exc_info=True
        )
        
        # Return error response but don't raise HTTP exception
        # Stripe expects 200 status even on processing errors to avoid retries
        error_response = WebhookProcessingResponse(
            success=False,
            message=f"Error processing payout {payout_id}: {str(e)}",
            event_id="payout_processing_error",
            event_type="payout_processing",
            company_id=company_id,
            processed=False,
            processing_timestamp=datetime.datetime.now(), # type: ignore
            correlation_id=correlation_id
        )
        
        return JSONResponse(
            status_code=200,  # Stripe expects 200 even on processing errors
            content=error_response.model_dump()
        ) # type: ignore
    

@router.post(
    "/stripe/{company_id}/invoice/{invoice_id}",
    status_code=200,
    summary="Process invoice for a given invoice_id",
    description="Retrieve detailed information about a specific invoice and process bank deposit."
)
async def process_stripe_invoice(
    company_id: int,
    invoice_id: str,
    session: AsyncSession = Depends(get_session)
) -> WebhookProcessingResponse:
    """
    Process a Stripe invoice by retrieving its details and creating a bank deposit batch.
    
    Args:
        company_id: The ID of the company this invoice is for
        invoice_id: The ID of the Stripe invoice to process   
        session: Database session (injected)    
    Returns:
        WebhookProcessingResponse: Processing result with status and details    
    Raises:
        HTTPException: If company_id is invalid or processing fails critically  
    """

    correlation_id = CorrelationIdFilter.get_correlation_id() or "webhook-unknown"
    
    # Validate company_id format (basic validation)
    try:
        if not company_id:
            logger.error(
                "Invalid company_id provided in webhook URL",
                extra={
                    "company_id": company_id,
                    "correlation_id": correlation_id
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid company_id in URL path"
            )
        
        company = await get_company_from_cache(company_id, session)
        if not company:
            logger.error(
                "Invalid company_id provided in webhook URL",
                extra={
                    "company_id": company_id,
                    "correlation_id": correlation_id
                }
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid company_id in URL path"
            )
        
        # Process the payout using the webhook service
        stripe_provider = await get_stripe_provider(
            session=session,
            company_id=company_id
        )

        invoice = await stripe_provider.get_invoice(invoice_id=invoice_id, expand=["customer", "payments", "parent.subscription_details.subscription"])

        # Call utility function for processing
        result = await process_stripe_invoice_paid(
            session=session,
            invoice_data=invoice,
            company_id=company_id,
            stripe_provider=stripe_provider,
            event_id=""
        )
        return WebhookProcessingResponse(
            success=True,
            message=f"Invoice {invoice_id} processed successfully",
            event_id="invoice_paid_processing",  
            event_type="invoice_paid",
            company_id=company_id,
            processed=True,
            processing_timestamp=datetime.datetime.now(),  # Could be set to current time or event time if available
            correlation_id=correlation_id
        )
    except Exception as e:
        # Log error details
        logger.error(
            f"Critical error processing for invoice {invoice_id}: {str(e)}",
            extra={
                "company_id": company_id,
                "invoice_id": invoice_id,
                "error": str(e),
                "correlation_id": correlation_id
            },
            exc_info=True
        )
        
        # Return error response but don't raise HTTP exception
        # Stripe expects 200 status even on processing errors to avoid retries
        error_response = WebhookProcessingResponse(
            success=False,
            message=f"Error processing invoice {invoice_id}: {str(e)}",
            event_id="invoice_processing_error",
            event_type="invoice_processing",
            company_id=company_id,
            processed=False,
            processing_timestamp=datetime.datetime.now(), # type: ignore
            correlation_id=correlation_id
        )
        
        return JSONResponse(
            status_code=200,  # Stripe expects 200 even on processing errors
            content=error_response.model_dump()
        ) # type: ignore