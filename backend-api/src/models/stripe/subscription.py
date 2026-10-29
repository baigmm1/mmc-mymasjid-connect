# define a subset of the subscription model to be used for data retreival

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SubscriptionModel(BaseModel):
    id: str = Field(..., description="Stripe subscription ID")
    customer_id: str = Field(..., description="Stripe customer ID")
    created: int = Field(..., description="Unix timestamp of subscription creation")
    created_datetime: Optional[datetime] = Field(None, description="Subscription creation time in ISO format")
    cancel_at: Optional[int] = Field(None, description="Unix timestamp of subscription cancellation")
    cancel_at_datetime: Optional[datetime] = Field(None, description="Subscription cancellation time in ISO format")
    payment_method_id: Optional[str] = Field(None, description="Default payment method ID for the subscription")
    payment_method_desc: Optional[str] = Field(None, description="Description of the default payment method for the subscription")
    latest_invoice_id: Optional[str] = Field(None, description="ID of the latest invoice for the subscription")
    payment_intent_id: Optional[str] = Field(None, description="ID of the payment intent associated with the latest invoice")

