"""
Pydantic schemas for DonationType API responses.

These schemas define the structure of JSON responses for donation type endpoints.
"""

from typing import Optional

from pydantic import BaseModel, Field


class DonationTypeModel(BaseModel):
    """Response schema for DonationType."""

    CompanyId: int = Field(..., alias="companyId", description="Company identifier")
    DonationType: int = Field(..., alias="donationType", description="Donation type identifier")
    FundId: Optional[int] = Field(None, alias="fundId", description="Associated fund identifier")
    ShortName: Optional[str] = Field(None, alias="shortName", description="Abbreviated donation type name", max_length=20)
    ShortDescription: Optional[str] = Field(None, alias="shortDescription", description="Brief description", max_length=50)
    Description: Optional[str] = Field(None, alias="description", description="Full description", max_length=100)
    DetailedTextHeader: Optional[str] = Field(None, alias="detailedTextHeader", description="Header for detailed text", max_length=500)
    DetailedText: Optional[str] = Field(None, alias="detailedText", description="Detailed text content (unlimited length)")
    TaxReceipt: Optional[int] = Field(None, alias="taxReceipt", description="Tax receipt flag")
    AccountNumber: Optional[str] = Field(None, alias="accountNumber", description="Associated account number", max_length=40)
    ShowWeb: Optional[int] = Field(None, alias="showWeb", description="Display on web flag")
    ShowTablet: Optional[int] = Field(None, alias="showTablet", description="Display on tablet flag")
    ShowPhone: Optional[int] = Field(None, alias="showPhone", description="Display on phone flag")
    ShowKiosk: Optional[int] = Field(None, alias="showKiosk", description="Display on kiosk flag")
    ShowPledge: Optional[int] = Field(None, alias="showPledge", description="Display on pledge page flag")
    SuggestedAmounts: Optional[str] = Field(None, alias="suggestedAmounts", description="Suggested donation amounts", max_length=100)
    ImageURL: Optional[str] = Field(None, alias="imageURL", description="Primary image URL", max_length=510)
    ImageHeaderURL: Optional[str] = Field(None, alias="imageHeaderURL", description="Header image URL", max_length=510)
    ImageURLList: Optional[str] = Field(None, alias="imageURLList", description="List image URL", max_length=510)
    SortOrder: Optional[int] = Field(None, alias="sortOrder", description="Display sort order")
    StatusCode: Optional[int] = Field(None, alias="statusCode", description="Status code")

    model_config = {"from_attributes": True, "populate_by_name": True}


class DonationTypeListResponse(BaseModel):
    """Response schema for list of donation types."""

    count: int = Field(..., description="Total number of donation types returned")
    items: list[DonationTypeModel] = Field(..., description="List of donation types")
    status: Optional[str] = Field(None, description="Status message")


class DonationTypeResponse(BaseModel):
    """Response schema for a single donation type."""

    item: DonationTypeModel = Field(..., description="Donation type data")
    status: Optional[str] = Field(None, description="Status message")
