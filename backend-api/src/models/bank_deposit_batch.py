"""
Pydantic schemas for Bank Deposit Batch API requests and responses.

These schemas define the structure of JSON requests and responses for bank deposit batch endpoints.
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class BankDepositBatchTransactionModel(BaseModel):
    """Response schema for Bank Deposit Batch Transaction."""

    companyId: int = Field(..., alias="CompanyId", description="Company identifier")
    batchNumber: int = Field(..., alias="BatchNumber", description="Batch number reference")
    lineNumber: int = Field(..., alias="LineNumber", description="Line number within batch")
    donationReceiptId: int = Field(..., alias="DonationReceiptId", description="Donation receipt identifier")
    providerId: str = Field(..., alias="ProviderId", description="Payment provider identifier", max_length=50)
    transactionType: str = Field(..., alias="TransactionType", description="Type of transaction", max_length=100)
    amount: Decimal = Field(..., alias="Amount", description="Transaction amount")
    feeAmount: Optional[Decimal] = Field(..., alias="FeeAmount", description="Transaction fee amount")
    createdBy: int = Field(..., alias="CreatedBy", description="User ID who created record")
    createdDate: datetime = Field(..., alias="CreatedDate", description="Creation timestamp")
    modifiedBy: Optional[int] = Field(None, alias="ModifiedBy", description="User ID who last modified record")
    modifiedDate: Optional[datetime] = Field(None, alias="ModifiedDate", description="Last modification timestamp")

    model_config = {"from_attributes": True, "populate_by_name": True}


class BankDepositBatchTransactionCreateModel(BaseModel):
    """Request schema for creating a Bank Deposit Batch Transaction."""

    donationReceiptId: int = Field(..., description="Donation receipt identifier")
    providerId: str = Field(..., description="Payment provider identifier", max_length=50)
    transactionType: str = Field(..., description="Type of transaction", max_length=100)
    amount: Decimal = Field(..., description="Transaction amount")
    feeAmount: Optional[Decimal] = Field(..., description="Transaction fee amount")

class BankDepositBatchModel(BaseModel):
    """Response schema for Bank Deposit Batch."""

    batchNumber: int = Field(..., alias="BatchNumber", description="Unique batch identifier")
    batchDate: datetime = Field(..., alias="BatchDate", description="Date batch was created")
    bankDepositDate: Optional[datetime] = Field(None, alias="BankDepositDate", description="Date deposited to bank")
    batchStatus: int = Field(..., alias="BatchStatus", description="Batch status code")
    createdBy: str = Field(..., alias="CreatedBy", description="User who created batch", max_length=25)
    createdDate: datetime = Field(..., alias="CreatedDate", description="Creation timestamp")
    modifiedBy: Optional[str] = Field(None, alias="ModifiedBy", description="User who last modified batch", max_length=25)
    modifiedDate: Optional[datetime] = Field(None, alias="ModifiedDate", description="Last modification timestamp")
    batchMethodType: str = Field(..., alias="BatchMethodType", description="Batch method type (e.g., ACH, Check, Wire)", max_length=20)
    companyId: int = Field(..., alias="CompanyId", description="Company identifier")
    providerId: str = Field(..., alias="ProviderId", description="Payment provider identifier", max_length=50)
    amount: Decimal = Field(..., alias="Amount", description="Total batch amount")

    model_config = {"from_attributes": True, "populate_by_name": True}


class BankDepositBatchDetailModel(BaseModel):
    """Response schema for Bank Deposit Batch with transaction details."""

    batch: BankDepositBatchModel = Field(..., description="Batch header information")
    transactions: list[BankDepositBatchTransactionModel] = Field(..., description="Transaction line items")

    model_config = {"from_attributes": True, "populate_by_name": True}


class BankDepositBatchCreateModel(BaseModel):
    """Request schema for creating a Bank Deposit Batch with transactions."""
    companyId: int = Field(..., description="Company identifier")
    batchDate: str = Field(..., description="Date batch was created")
    bankDepositDate: Optional[str] = Field(None, description="Date deposited to bank")
    batchStatus: int = Field(default=1, description="Batch status code")
    batchMethodType: str = Field(..., description="Batch method type (e.g., ACH, Check, Wire)", max_length=20)    
    batchMethodTypeId: Optional[int] = Field(None, description="Batch method type identifier")
    providerId: str = Field(..., description="Payment provider identifier", max_length=50)
    amount: Decimal = Field(..., description="Total batch amount")
    transactions: list[BankDepositBatchTransactionCreateModel] = Field(
        ..., 
        description="List of transaction details"
    )


class BankDepositBatchUpdateModel(BaseModel):
    """Request schema for updating a Bank Deposit Batch."""

    batchDate: Optional[datetime] = Field(None, description="Date batch was created")
    bankDepositDate: Optional[datetime] = Field(None, description="Date deposited to bank")
    batchStatus: Optional[int] = Field(None, description="Batch status code")
    batchMethodType: Optional[str] = Field(None, description="Batch method type", max_length=20)
    amount: Optional[Decimal] = Field(None, description="Total batch amount")


class BankDepositBatchListResponse(BaseModel):
    """Response schema for list of batches."""

    count: int = Field(..., description="Total number of batches returned")
    items: list[BankDepositBatchModel] = Field(..., description="List of batches")
    status: Optional[str] = Field(None, description="Status message")


class BankDepositBatchResponse(BaseModel):
    """Response schema for a single batch."""

    item: BankDepositBatchModel = Field(..., description="Batch data")
    status: Optional[str] = Field(None, description="Status message")


class BankDepositBatchDetailResponse(BaseModel):
    """Response schema for batch with transaction details."""

    item: BankDepositBatchDetailModel = Field(..., description="Batch data with transactions")
    status: Optional[str] = Field(None, description="Status message")


class OperationResponse(BaseModel):
    """Generic response for create/update/delete operations."""

    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Operation result message")
    batchNumber: Optional[int] = Field(None, description="Batch number for create operations")
