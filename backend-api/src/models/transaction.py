"""
Pydantic schemas for Transaction API responses.

These schemas define the structure of JSON responses for transaction endpoints.
"""

from typing import Optional
from pydantic import BaseModel, Field
from src.models.donors import DonorsModel

class TransactionDetailsModel(BaseModel):
    """Detailed response schema for Transaction."""
    LineNumber: int = Field(..., alias="lineNumber", description="Line number of the transaction detail")
    Description: Optional[str] = Field(None, alias="description", description="Description of the transaction detail", max_length=240)
    DonationTypeId: int = Field(..., alias="donationTypeId", description="Identifier for the donation type")
    Amount: float = Field(..., alias="amount", description="Amount for this transaction detail")
    FeePercent: Optional[float] = Field(None, alias="feePercent", description="Fee percentage applied to this detail")
    FeeAmount: Optional[float] = Field(None, alias="feeAmount", description="Fee amount applied to this detail")
    PriceId: Optional[str] = Field(None, alias="priceId", description="Identifier for the price associated with this detail", max_length=100)
    ProductId: Optional[str] = Field(None, alias="productId", description="Identifier for the product associated with this detail", max_length=100)

class TransactionModel(BaseModel):
    """Response schema for Transaction."""    
    TransactionId: int = Field(..., alias="transactionId", description="Unique transaction identifier")
    Description: Optional[str] = Field(None, alias="description", description="Description of the transaction", max_length=240)
    CompanyId: int = Field(..., alias="companyId", description="Unique company identifier")
    TerminalId: Optional[str] = Field(None, alias="terminalId", description="Terminal identifier", max_length=50)
    DonorId: Optional[int] = Field(None, alias="donorId", description="Unique donor identifier")
    DonorName: Optional[str] = Field(None, alias="donorName", description="Name of the donor", max_length=240)
    DonorPhone: Optional[str] = Field(None, alias="donorPhone", description="Phone number of the donor", max_length=50)
    DonorEmail: Optional[str] = Field(None, alias="donorEmail", description="Email address of the donor", max_length=512)
    DonorBillingZip: Optional[str] = Field(None, alias="donorBillingZip", description="Billing ZIP code of the donor", max_length=20)   
    TransactionDate: str = Field(..., alias="transactionDate", description="Date and time of the transaction in ISO 8601 format")
    PurposeId: Optional[int] = Field(None, alias="purposeId", description="Identifier for the purpose of the transaction")
    TotalAmount: float = Field(..., alias="totalAmount", description="Transaction amount")
    Currency: Optional[str] = Field(None, alias="currency", description="Currency code (e.g., USD)", max_length=6)  
    Recurring: Optional[bool] = Field(None, alias="recurring", description="Indicates if the transaction is recurring")
    NumberofMonths: Optional[int] = Field(None, alias="numberofMonths", description="Number of periods for recurring transactions (months/years/days depending on frequency)")
    RecurringFrequency: Optional[int] = Field(None, alias="recurringFrequency", description="Recurring frequency: 1=Monthly (default), 2=Yearly, 3=Daily")
    PaymentMethod: Optional[str] = Field(None, alias="paymentMethod", description="Payment method used", max_length=50)
    PaymentMethodId: Optional[int] = Field(None, alias="paymentMethodId", description="Identifier for the payment method")
    Provider: Optional[str] = Field(None, alias="provider", description="Payment provider name", max_length=25)
    ProviderName: Optional[str] = Field(None, alias="providerName", description="Payment provider display name", max_length=50)
    ProviderId: Optional[str] = Field(None, alias="providerId", description="Payment provider identifier")
    ProviderToken: Optional[str] = Field(None, alias="providerToken", description="Token provided by the payment provider", max_length=510)    
    ProviderPlanId: Optional[str] = Field(None, alias="providerPlanId", description="Identifier for the plan associated with this transaction", max_length=128)
    ProviderAgreementId: Optional[str] = Field(None, alias="providerAgreementId", description="Identifier for the agreement associated with this transaction", max_length=128)
    ProviderDescription: Optional[str] = Field(None, alias="providerDescription", description="Description from the payment provider", max_length=240)
    SuccessURL: Optional[str] = Field(None, alias="successUrl", description="URL to redirect on success", max_length=510)
    CancelURL: Optional[str] = Field(None, alias="cancelUrl", description="URL to redirect on cancellation", max_length=510)    
    CheckoutURL: Optional[str] = Field(None, alias="checkoutUrl", description="URL for online checkout", max_length=510)
    Status: Optional[str] = Field(None, alias="status", description="Transaction status", max_length=50)
    StatusCode: Optional[int] = Field(None, alias="statusCode", description="Status code of the transaction")
    DonorDetails: Optional[DonorsModel] = Field(None, alias="donorDetails", description="Details of the donor")
    Details: Optional[list[TransactionDetailsModel]] = Field(None, alias="details", description="List of transaction details")
    

class TransactionResponse(BaseModel):
    """Response schema for a single transaction."""
    item: TransactionModel = Field(..., description="Transaction data")
    status: Optional[str] = Field(None, description="Status message")
    message: Optional[str] = Field(None, description="Error message if applicable")


class TestPaymentMethodRequest(BaseModel):
    """Request schema for testing payment method presentation."""
    CompanyId: int = Field(..., alias="companyId", description="Unique company identifier")
    TerminalId: str = Field(..., alias="terminalId", description="Stripe Terminal reader ID")
    CardNumber: Optional[str] = Field(None, alias="cardNumber", description="Test card number to use (optional, defaults to 4242424242424242)")


class TestPaymentMethodResponse(BaseModel):
    """Response schema for test payment method presentation."""
    success: bool = Field(..., description="Whether the operation succeeded")
    message: Optional[str] = Field(None, description="Response message")
    reader_id: Optional[str] = Field(None, alias="readerId", description="Terminal reader ID")
    