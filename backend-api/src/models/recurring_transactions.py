"""
Pydantic schemas for Recurring Transactions API requests and responses.

These schemas define the structure of JSON requests and responses for recurring transaction endpoints.
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

class RecurringTransactionStatusEnum:
    """Status codes for recurring transactions."""    
    INCOMPLETE = 1
    ACTIVE = 2
    CANCELED = 3
    INCOMPLETE_EXPIRED = 4
    TRIALING = 5
    PAST_DUE = 6
    UNPAID = 7
    PAUSED = 8


class RecurringFrequencyEnum:
    """Frequency types for recurring transactions."""
    
    MONTHLY = 1
    YEARLY = 2
    DAILY = 3
    WEEKLY = 4
    QUARTERLY = 5
    HALFYEAR = 6


class RecurringTransactionDetailsModel(BaseModel):
    """Response schema for Recurring Transaction Detail."""

    transactionId: int = Field(..., alias="TransactionId", description="Transaction identifier")
    lineNumber: int = Field(..., alias="LineNumber", description="Line number within transaction")
    companyId: int = Field(..., alias="CompanyId", description="Company identifier")
    donationType: int = Field(..., alias="DonationType", description="Type of donation")
    description: Optional[str] = Field(None, alias="Description", description="Optional description for this line item")
    amount: Optional[Decimal] = Field(None, alias="Amount", description="Line item amount")
    currency: Optional[str] = Field(None, alias="Currency", description="Currency code (e.g., USD)", max_length=3)

    model_config = {"from_attributes": True, "populate_by_name": True}


class RecurringTransactionDetailsCreateModel(BaseModel):
    """Request schema for creating a Recurring Transaction Detail."""

    donationType: int = Field(..., description="Type of donation")
    priceId: Optional[str] = Field(None, description="Stripe Price ID for this line item", max_length=100)
    productId: Optional[str] = Field(None, description="Reference to Product for this line item")
    causeId: Optional[str] = Field(None, description="Reference to Cause for this line item")
    amount: Decimal = Field(..., description="Line item amount")
    currency: Optional[str] = Field("USD", description="Currency code", max_length=3)


class RecurringTransactionPaymentsModel(BaseModel):
    """Response schema for Recurring Transaction Payment."""

    transactionId: int = Field(..., alias="TransactionId", description="Transaction identifier")
    lineNumber: int = Field(..., alias="LineNumber", description="Line number within transaction")
    donationReceiptId: int = Field(..., alias="DonationReceiptId", description="Donation receipt identifier")
    providerId: Optional[str] = Field(None, alias="ProviderId", description="Payment provider identifier", max_length=50)
    donationDate: datetime = Field(..., alias="DonationDate", description="Date of the donation/payment")

    model_config = {"from_attributes": True, "populate_by_name": True}


class RecurringTransactionModel(BaseModel):
    """Response schema for Recurring Transaction."""

    transactionId: int = Field(..., alias="TransactionId", description="Unique transaction identifier")
    companyId: int = Field(..., alias="CompanyId", description="Company identifier")
    donorId: Optional[int] = Field(None, alias="DonorId", description="Donor identifier")
    reviewDonorId: Optional[int] = Field(None, alias="ReviewDonorId", description="Review donor identifier")
    startDate: datetime = Field(..., alias="StartDate", description="Subscription start date")
    frequency: int = Field(..., alias="Frequency", description="Recurring frequency type")
    frequencyDescription: Optional[str] = Field(None, alias="FrequencyDescription", description="Human-readable frequency description") 
    frequencyCount: int = Field(..., alias="FrequencyCount", description="Number of frequency units")
    endDate: datetime = Field(..., alias="EndDate", description="Subscription end date")
    providerName: Optional[str] = Field(None, alias="ProviderName", description="Payment provider name", max_length=50)
    subscriptionId: Optional[str] = Field(None, alias="SubscriptionId", description="Provider's subscription ID", max_length=100)
    paymentMethod: Optional[str] = Field(None, alias="PaymentMethod", description="Payment method description", max_length=100)
    totalAmount: Optional[Decimal] = Field(None, alias="TotalAmount", description="Total subscription amount")
    status: int = Field(..., alias="Status", description="Current status")    
    details: Optional[list[RecurringTransactionDetailsModel]] = Field(
        default=[], 
        description="List of transaction detail line items"
    )
    payments: Optional[list[RecurringTransactionPaymentsModel]] = Field(
        default=[],
        description="List of payment history records for this transaction"
    )
    model_config = {"from_attributes": True, "populate_by_name": True}


class RecurringTransactionDetailModel(BaseModel):
    """Response schema for Recurring Transaction with detail and payment information."""

    transaction: RecurringTransactionModel = Field(..., description="Transaction header information")
    details: list[RecurringTransactionDetailsModel] = Field(default=[], description="Transaction detail line items")
    payments: list[RecurringTransactionPaymentsModel] = Field(default=[], description="Payment history")

    model_config = {"from_attributes": True, "populate_by_name": True}


class RecurringTransactionCreateModel(BaseModel):
    """Request schema for creating a Recurring Transaction."""

    companyId: int = Field(..., description="Company identifier")
    donorId: Optional[int] = Field(None, description="Donor identifier")
    reviewDonorId: Optional[int] = Field(None, description="Review donor identifier")
    startDate: datetime = Field(..., description="Subscription start date")
    frequency: int = Field(..., description="Recurring frequency type (1=Monthly, 2=Yearly)")
    frequencyCount: int = Field(default=1, description="Number of frequency units")
    endDate: Optional[datetime] = Field(None, description="Subscription end date")
    providerName: str = Field(..., description="Payment provider name", max_length=50)
    subscriptionId: str = Field(..., description="Provider's subscription ID", max_length=100)
    customerId: Optional[str] = Field(None, description="Provider's customer ID", max_length=100)
    paymentMethodId: Optional[str] = Field(None, description="Provider's payment method ID", max_length=100)
    paymentMethod: Optional[str] = Field(None, description="Payment method description", max_length=100)
    totalAmount: Decimal = Field(..., description="Total subscription amount")
    status: int = Field(default=RecurringTransactionStatusEnum.ACTIVE, description="Current status (2=Active)") # type: ignore
    details: Optional[list[RecurringTransactionDetailsCreateModel]] = Field(
        default=[], 
        description="List of transaction detail line items"
    )


class RecurringTransactionUpdateModel(BaseModel):
    """Request schema for updating a Recurring Transaction."""

    donorId: Optional[int] = Field(None, description="Donor identifier")
    reviewDonorId: Optional[int] = Field(None, description="Review donor identifier")
    endDate: Optional[datetime] = Field(None, description="Subscription end date")
    paymentMethod: Optional[str] = Field(None, description="Payment method description", max_length=100)
    customerId: Optional[str] = Field(None, description="Provider's customer ID", max_length=100)
    paymentMethodId: Optional[str] = Field(None, description="Provider's payment method ID", max_length=100)
    totalAmount: Optional[Decimal] = Field(None, description="Total subscription amount")
    status: Optional[int] = Field(None, description="Current status")


class RecurringTransactionListResponse(BaseModel):
    """Response schema for list of recurring transactions."""

    count: int = Field(..., description="Total number of transactions returned")
    items: list[RecurringTransactionModel] = Field(..., description="List of transactions")
    status: Optional[str] = Field(None, description="Status message")


class RecurringTransactionResponse(BaseModel):
    """Response schema for a single recurring transaction."""

    item: RecurringTransactionModel | None = Field(None, description="Transaction data")
    status: Optional[str] = Field(None, description="Status message")


class RecurringTransactionDetailResponse(BaseModel):
    """Response schema for transaction with details and payments."""

    item: RecurringTransactionDetailModel = Field(..., description="Transaction data with details and payments")
    status: Optional[str] = Field(None, description="Status message")


class RecurringTransactionOperationResponse(BaseModel):
    """Generic response for create/update/delete operations."""

    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Operation result message")
    transactionId: Optional[int] = Field(None, description="Transaction ID for create operations")


