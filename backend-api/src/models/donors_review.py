"""
Pydantic schemas for DonorsReview API responses.

These schemas define the structure of JSON responses for donors review endpoints.
"""

from typing import Optional

from pydantic import BaseModel, Field, EmailStr


class DonorsReviewModel(BaseModel):
    """Response schema for DonorsReview."""

    DonorId: int = Field(..., alias="donorId", description="Unique donor identifier")
    CompanyId: int = Field(..., alias="companyId", description="Company identifier")
    NamePrefix: Optional[str] = Field(None, alias="namePrefix", description="Name prefix (Mr., Mrs., Dr., etc.)", max_length=10)
    CompleteName: Optional[str] = Field(None, alias="completeName", description="Complete name of the donor", max_length=240)
    AddressLine1: Optional[str] = Field(None, alias="addressLine1", description="Primary address line", max_length=100)
    AddressLine2: Optional[str] = Field(None, alias="addressLine2", description="Secondary address line", max_length=100)
    City: Optional[str] = Field(None, alias="city", description="City name", max_length=100)
    State: Optional[str] = Field(None, alias="state", description="State or province code", max_length=10)
    PostalCode: Optional[str] = Field(None, alias="postalCode", description="Postal or ZIP code", max_length=20)
    CountryCode: Optional[str] = Field(None, alias="countryCode", description="Country code", max_length=6)
    PhoneNumber: Optional[str] = Field(None, alias="phoneNumber", description="Contact phone number", max_length=50)
    EMail: Optional[str] = Field(None, alias="eMail", description="Email address", max_length=512)

    model_config = {"from_attributes": True, "populate_by_name": True}


class DonorsReviewCreateModel(BaseModel):
    """Request schema for creating a new donor review record."""

    CompanyId: int = Field(..., alias="companyId", description="Company identifier")
    NamePrefix: Optional[str] = Field(None, alias="namePrefix", description="Name prefix", max_length=10)
    CompleteName: Optional[str] = Field(None, alias="completeName", description="Complete name", max_length=240)
    AddressLine1: Optional[str] = Field(None, alias="addressLine1", description="Address line 1", max_length=100)
    AddressLine2: Optional[str] = Field(None, alias="addressLine2", description="Address line 2", max_length=100)
    City: Optional[str] = Field(None, alias="city", description="City", max_length=100)
    State: Optional[str] = Field(None, alias="state", description="State code", max_length=10)
    PostalCode: Optional[str] = Field(None, alias="postalCode", description="Postal code", max_length=20)
    CountryCode: Optional[str] = Field(None, alias="countryCode", description="Country code", max_length=6)
    PhoneNumber: Optional[str] = Field(None, alias="phoneNumber", description="Phone number", max_length=50)
    EMail: Optional[str] = Field(None, alias="eMail", description="Email", max_length=512)

    model_config = {"populate_by_name": True}


class DonorsReviewListResponse(BaseModel):
    """Response schema for list of donors review records."""

    count: int = Field(..., description="Total number of donor review records returned")
    items: list[DonorsReviewModel] = Field(..., description="List of donor review records")
    status: Optional[str] = Field(None, description="Status message")


class DonorsReviewResponse(BaseModel):
    """Response schema for a single donor review record."""

    item: DonorsReviewModel = Field(..., description="Donor review data")
    status: Optional[str] = Field(None, description="Status message")
