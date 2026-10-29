"""
Pydantic schemas for Donors API responses.

These schemas define the structure of JSON responses for donors endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, EmailStr
from src.models.user import User

class DonorsModel(BaseModel):
    """Response schema for Donors."""

    DonorId: int = Field(..., alias="donorId", description="Unique donor identifier")
    NamePrefix: Optional[str] = Field(None, alias="namePrefix", description="Name prefix", max_length=10)
    CompleteName: Optional[str] = Field(None, alias="completeName", description="Complete name", max_length=240)
    FirstName: Optional[str] = Field(None, alias="firstName", description="First name", max_length=60)
    MiddleName: Optional[str] = Field(None, alias="middleName", description="Middle name", max_length=60)
    LastName: Optional[str] = Field(None, alias="lastName", description="Last name", max_length=60)
    Suffix: Optional[str] = Field(None, alias="suffix", description="Name suffix", max_length=10)
    CompanyName: Optional[str] = Field(None, alias="companyName", description="Company name", max_length=240)
    TaxReceiptName: Optional[str] = Field(None, alias="taxReceiptName", description="Tax receipt name", max_length=240)
    AddressLine1: Optional[str] = Field(None, alias="addressLine1", description="Address line 1", max_length=100)
    AddressLine2: Optional[str] = Field(None, alias="addressLine2", description="Address line 2", max_length=100)
    City: Optional[str] = Field(None, alias="city", description="City", max_length=100)
    State: Optional[str] = Field(None, alias="state", description="State code", max_length=10)
    PostalCode: Optional[str] = Field(None, alias="postalCode", description="Postal code", max_length=20)
    CountryCode: Optional[str] = Field(None, alias="countryCode", description="Country code", max_length=6)
    PhoneNumber: Optional[str] = Field(None, alias="phoneNumber", description="Phone number", max_length=50)
    EMail: Optional[str] = Field(None, alias="eMail", description="Email", max_length=512)
    Occupation: Optional[str] = Field(None, alias="occupation", description="Occupation", max_length=100)
    Physician: Optional[bool] = Field(None, alias="physician", description="Is physician")
    IncorrectAddress: Optional[bool] = Field(None, alias="incorrectAddress", description="Incorrect address flag")
    PublishinDonorList: Optional[bool] = Field(None, alias="publishinDonorList", description="Publish in donor list")
    TaxReceiptRequired: Optional[bool] = Field(None, alias="taxReceiptRequired", description="Tax receipt required")
    StatusCode: Optional[int] = Field(None, alias="statusCode", description="Status code")
    CreatedBy: Optional[int] = Field(None, alias="createdBy", description="Created by user ID")
    CreatedDate: Optional[datetime] = Field(None, alias="createdDate", description="Creation date")
    ModifiedBy: Optional[int] = Field(None, alias="modifiedBy", description="Modified by user ID")
    ModifiedDate: Optional[datetime] = Field(None, alias="modifiedDate", description="Modification date")

    model_config = {"from_attributes": True, "populate_by_name": True}


class DonorsCreateModel(BaseModel):
    """Request schema for creating a new donor."""

    NamePrefix: Optional[str] = Field(None, alias="namePrefix", max_length=10)
    CompleteName: str = Field(..., alias="completeName", description="Complete name (required)", max_length=240)
    Suffix: Optional[str] = Field(None, alias="suffix", max_length=10)
    CompanyName: Optional[str] = Field(None, alias="companyName", max_length=240)
    TaxReceiptName: Optional[str] = Field(None, alias="taxReceiptName", max_length=240)
    AddressLine1: Optional[str] = Field(None, alias="addressLine1", max_length=100)
    AddressLine2: Optional[str] = Field(None, alias="addressLine2", max_length=100)
    City: Optional[str] = Field(None, alias="city", max_length=100)
    State: Optional[str] = Field(None, alias="state", max_length=10)
    PostalCode: Optional[str] = Field(None, alias="postalCode", max_length=20)
    CountryCode: Optional[str] = Field(None, alias="countryCode", max_length=6)
    PhoneNumber: Optional[str] = Field(None, alias="phoneNumber", max_length=50)
    EMail: Optional[str] = Field(None, alias="eMail", max_length=512)
    Occupation: Optional[str] = Field(None, alias="occupation", max_length=100)
    Physician: Optional[bool] = Field(False, alias="physician")
    IncorrectAddress: Optional[bool] = Field(False, alias="incorrectAddress")
    PublishinDonorList: Optional[bool] = Field(True, alias="publishinDonorList")
    TaxReceiptRequired: Optional[bool] = Field(True, alias="taxReceiptRequired")
    StatusCode: Optional[int] = Field(None, alias="statusCode")
    CreatedBy: Optional[int] = Field(None, alias="createdBy")

    model_config = {"populate_by_name": True}


class DonorsUpdateModel(BaseModel):
    """Request schema for updating an existing donor."""

    NamePrefix: Optional[str] = Field(None, alias="namePrefix", max_length=10)
    CompleteName: Optional[str] = Field(None, alias="completeName", max_length=240)
    Suffix: Optional[str] = Field(None, alias="suffix", max_length=10)
    CompanyName: Optional[str] = Field(None, alias="companyName", max_length=240)
    TaxReceiptName: Optional[str] = Field(None, alias="taxReceiptName", max_length=240)
    AddressLine1: Optional[str] = Field(None, alias="addressLine1", max_length=100)
    AddressLine2: Optional[str] = Field(None, alias="addressLine2", max_length=100)
    City: Optional[str] = Field(None, alias="city", max_length=100)
    State: Optional[str] = Field(None, alias="state", max_length=10)
    PostalCode: Optional[str] = Field(None, alias="postalCode", max_length=20)
    CountryCode: Optional[str] = Field(None, alias="countryCode", max_length=6)
    PhoneNumber: Optional[str] = Field(None, alias="phoneNumber", max_length=50)
    EMail: Optional[str] = Field(None, alias="eMail", max_length=512)
    Occupation: Optional[str] = Field(None, alias="occupation", max_length=100)
    Physician: Optional[bool] = Field(None, alias="physician")
    IncorrectAddress: Optional[bool] = Field(None, alias="incorrectAddress")
    PublishinDonorList: Optional[bool] = Field(None, alias="publishinDonorList")
    TaxReceiptRequired: Optional[bool] = Field(None, alias="taxReceiptRequired")
    StatusCode: Optional[int] = Field(None, alias="statusCode")
    ModifiedBy: Optional[int] = Field(None, alias="modifiedBy")

    model_config = {"populate_by_name": True}


class DonorsListResponse(BaseModel):
    """Response schema for list of donors."""

    count: int = Field(..., description="Total number of donors returned")
    items: list[DonorsModel] = Field(..., description="List of donors")
    status: Optional[str] = Field(None, description="Status message")


class DonorsResponse(BaseModel):
    """Response schema for a single donor."""

    item: Optional[DonorsModel] = Field(None, description="Donor data (null if not yet linked)")
    user: Optional[User] = Field(None, description="User data (null if not yet linked)")
    status: Optional[str] = Field(None, description="Status message")
    message: Optional[str] = Field(default=None, description="Additional message")
