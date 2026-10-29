"""
Pydantic schemas for Company API responses.

These schemas define the structure of JSON responses for company endpoints.
"""

from typing import Optional

from pydantic import BaseModel, Field


class CompanyModel(BaseModel):
    """Response schema for Company."""

    CompanyId: int = Field(..., alias="companyId", description="Unique company identifier")
    CompanyName: str = Field(..., alias="companyName", description="Full company name", max_length=240)
    ShortName: Optional[str] = Field(None, alias="shortName", description="Abbreviated company name", max_length=20)
    AddressLine1: Optional[str] = Field(None, alias="addressLine1", description="Primary address line", max_length=100)
    AddressLine2: Optional[str] = Field(None, alias="addressLine2", description="Secondary address line", max_length=100)
    City: Optional[str] = Field(None, alias="city", description="City name", max_length=60)
    StateCode: Optional[str] = Field(None, alias="stateCode", description="State or province code", max_length=10)
    PostalCode: Optional[str] = Field(None, alias="postalCode", description="Postal or ZIP code", max_length=24)
    CountryCode: Optional[str] = Field(None, alias="countryCode", description="Country code", max_length=6)
    PhoneNumber: Optional[str] = Field(None, alias="phoneNumber", description="Contact phone number", max_length=100)
    EMail: Optional[str] = Field(None, alias="eMail", description="Contact email address", max_length=100)
    TaxId: Optional[str] = Field(None, alias="taxId", description="Tax identification number", max_length=50)
    Website: Optional[str] = Field(None, alias="website", description="Company website URL", max_length=100)
    CompanyLogo: Optional[str] = Field(None, alias="companyLogo", description="Path or URL to company logo", max_length=510)

    model_config = {"from_attributes": True, "populate_by_name": True}


class CompanyListResponse(BaseModel):
    """Response schema for list of companies."""

    count: int = Field(..., description="Total number of companies returned")
    items: list[CompanyModel] = Field(..., description="List of companies")
    status: Optional[str] = Field(None, description="Status message")


class CompanyResponse(BaseModel):
    """Response schema for a single company."""

    item: CompanyModel = Field(..., description="Company data")
    status: Optional[str] = Field(None, description="Status message")
