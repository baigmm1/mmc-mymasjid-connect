"""
Webhook models for Stripe webhook processing.

Defines request and response models for Stripe webhook endpoints including
event types, payload structures, and processing status.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class StripeWebhookRequest(BaseModel):
    """
    Stripe webhook request payload.
    
    This represents the raw webhook data received from Stripe.
    """
    id: str = Field(..., description="Stripe event ID")
    object: str = Field(..., description="Object type (should be 'event')")
    api_version: str = Field(..., description="Stripe API version")
    created: int = Field(..., description="Unix timestamp of event creation")
    data: Dict[str, Any] = Field(..., description="Event data object")
    livemode: bool = Field(..., description="Whether this event occurred in live mode")
    pending_webhooks: int = Field(..., description="Number of pending webhook deliveries")
    request: Optional[Dict[str, Any]] = Field(None, description="Request that caused the event")
    type: str = Field(..., description="Event type (e.g., invoice.paid)")


class WebhookProcessingRequest(BaseModel):
    """
    Request model for webhook processing endpoint.
    """
    ignore: bool = Field(default=False, description="If true, receive event but don't process it")
    webhook_data: StripeWebhookRequest = Field(..., description="Stripe webhook payload")


class WebhookProcessingResponse(BaseModel):
    """
    Response model for webhook processing.
    """
    success: bool = Field(..., description="Whether processing was successful")
    message: str = Field(..., description="Processing result message")
    event_id: str = Field(..., description="Stripe event ID")
    event_type: str = Field(..., description="Stripe event type")
    company_id: int = Field(..., description="Company ID from URL path")
    processed: bool = Field(..., description="Whether event was actually processed (false if ignore=true)")
    processing_timestamp: datetime = Field(..., description="When processing occurred")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracking")


class WebhookEventSummary(BaseModel):
    """
    Summary information for a webhook event.
    """
    event_id: str = Field(..., description="Stripe event ID")
    event_type: str = Field(..., description="Event type")
    company_id: int = Field(..., description="Company ID")
    received_at: datetime = Field(..., description="When event was received")
    processed: bool = Field(..., description="Whether event was processed")
    ignore_flag: bool = Field(..., description="Whether ignore flag was set")