"""
Pydantic schemas for Pledges API.

These schemas define the structure of request/response bodies for pledge endpoints.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class PledgeModel(BaseModel):
    """Response schema for a single Pledge record."""

    PledgeRecordID: int = Field(..., alias="pledgeRecordId", description="Unique pledge identifier")
    CompanyId: int = Field(..., alias="companyId", description="Company identifier")
    DonorId: Optional[int] = Field(None, alias="donorId", description="Reference to Donors table")
    ReviewDonorId: Optional[int] = Field(None, alias="reviewDonorId", description="Reference to ReviewDonors table")
    PledgeBy: str = Field(..., alias="pledgeBy", description="Name of the person making the pledge", max_length=100)
    PledgeEmail: Optional[str] = Field(None, alias="pledgeEmail", description="Email address of the pledger", max_length=120)
    PledgePhoneNumber: Optional[str] = Field(None, alias="pledgePhoneNumber", description="Phone number of the pledger", max_length=25)
    PledgeDonationType: Optional[int] = Field(None, alias="pledgeDonationType", description="Donation type ID")
    PledgeDonationTypeDescription: Optional[str] = Field(None, alias="pledgeDonationTypeDescription", description="Description of the donation type")
    AmountPledged: Optional[Decimal] = Field(None, alias="amountPledged", description="Amount committed in the pledge")
    DatePledged: datetime = Field(..., alias="datePledged", description="Date the pledge was made")
    DateConfirmed: Optional[datetime] = Field(None, alias="dateConfirmed", description="Date the pledge was confirmed/fulfilled")
    StatusCode: Optional[int] = Field(None, alias="statusCode", description="Status code (1=Pending, 2=Confirmed, 3=Cancelled)")
    CreatedBy: Optional[int] = Field(None, alias="createdBy", description="Created by user ID")
    CreatedDate: Optional[datetime] = Field(None, alias="createdDate", description="Creation timestamp")
    ModifiedBy: Optional[int] = Field(None, alias="modifiedBy", description="Modified by user ID")
    ModifiedDate: Optional[datetime] = Field(None, alias="modifiedDate", description="Last modification timestamp")

    model_config = {"from_attributes": True, "populate_by_name": True}


class PledgeCreateModel(BaseModel):
    """Request schema for creating a new Pledge."""

    CompanyId: int = Field(..., alias="companyId", description="Company identifier")
    DonorId: Optional[int] = Field(None, alias="donorId", description="Reference to Donors table")
    ReviewDonorId: Optional[int] = Field(None, alias="reviewDonorId", description="Reference to ReviewDonors table")
    PledgeBy: str = Field(..., alias="pledgeBy", description="Name of the person making the pledge", max_length=100)
    PledgeEmail: Optional[str] = Field(None, alias="pledgeEmail", description="Email address of the pledger", max_length=120)
    PledgePhoneNumber: Optional[str] = Field(None, alias="pledgePhoneNumber", description="Phone number of the pledger", max_length=25)
    PledgeDonationType: Optional[int] = Field(None, alias="pledgeDonationType", description="Donation type ID")
    AmountPledged: Optional[Decimal] = Field(None, alias="amountPledged", description="Amount committed in the pledge")
    DatePledged: datetime = Field(..., alias="datePledged", description="Date the pledge was made")
    DateConfirmed: Optional[datetime] = Field(None, alias="dateConfirmed", description="Date the pledge was confirmed/fulfilled")
    StatusCode: Optional[int] = Field(1, alias="statusCode", description="Status code (1=Pending, 2=Confirmed, 3=Cancelled)")
    CreatedBy: Optional[int] = Field(None, alias="createdBy", description="User ID creating this record")

    model_config = {"populate_by_name": True}


class PledgeUpdateModel(BaseModel):
    """Request schema for updating an existing Pledge."""
    CompanyId: Optional[int] = Field(None, alias="companyId", description="Company identifier")
    DonorId: Optional[int] = Field(None, alias="donorId", description="Reference to Donors table")
    ReviewDonorId: Optional[int] = Field(None, alias="reviewDonorId", description="Reference to ReviewDonors table")
    PledgeBy: Optional[str] = Field(None, alias="pledgeBy", description="Name of the person making the pledge", max_length=100)
    PledgeEmail: Optional[str] = Field(None, alias="pledgeEmail", description="Email address of the pledger", max_length=120)
    PledgePhoneNumber: Optional[str] = Field(None, alias="pledgePhoneNumber", description="Phone number of the pledger", max_length=25)
    PledgeDonationType: Optional[int] = Field(None, alias="pledgeDonationType", description="Donation type ID")
    AmountPledged: Optional[Decimal] = Field(None, alias="amountPledged", description="Amount committed in the pledge")
    DatePledged: Optional[datetime] = Field(None, alias="datePledged", description="Date the pledge was made")
    DateConfirmed: Optional[datetime] = Field(None, alias="dateConfirmed", description="Date the pledge was confirmed/fulfilled")
    StatusCode: Optional[int] = Field(None, alias="statusCode", description="Status code (1=Pending, 2=Confirmed, 3=Cancelled)")
    ModifiedBy: Optional[int] = Field(None, alias="modifiedBy", description="User ID modifying this record")

    model_config = {"populate_by_name": True}


class PledgeListResponse(BaseModel):
    """Response schema for a list of Pledge records."""

    count: int = Field(..., description="Total number of pledges returned")
    items: list[PledgeModel] = Field(..., description="List of pledges")
    status: Optional[str] = Field(None, description="Status message")


class PledgeSingleResponse(BaseModel):
    """Response schema for a single Pledge record."""

    item: PledgeModel = Field(..., description="Pledge data")
    status: Optional[str] = Field(None, description="Status message")
