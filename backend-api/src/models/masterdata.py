"""
Pydantic schemas for masterdata API responses.

These schemas define the structure of JSON responses for masterdata endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

class CountryCodeModel(BaseModel):
    """Response schema for CountryCodes."""

    CountryCode: str = Field(..., alias="countryCode", description="Three-letter country code (ISO 3166-1 alpha-3)", max_length=3)
    CountryName: str = Field(..., alias="countryName", description="Full name of the country", max_length=50)

    model_config = {"from_attributes": True, "populate_by_name": True}


class StateCodeModel(BaseModel):
    """Response schema for StateCodes."""

    StateId: int = Field(..., alias="stateId", description="Unique identifier for the state")
    CountryCode: str = Field(..., alias="countryCode", description="Associated country code", max_length=3)
    StateCode: str = Field(..., alias="stateCode", description="State code or abbreviation", max_length=5)
    StateName: str = Field(..., alias="stateName", description="Full name of the state", max_length=50)

    model_config = {"from_attributes": True, "populate_by_name": True}


class KeyValuePairModel(BaseModel):
    """Response schema for KeyValuePairs."""

    Id: int = Field(..., alias="id", description="Unique identifier for the key-value pair")
    Type: int = Field(..., alias="type", description="Type category of the key-value pair")
    Key: int = Field(..., alias="key", description="Key identifier")
    Value: str = Field(..., alias="value", description="Value associated with the key", max_length=255)

    model_config = {"from_attributes": True, "populate_by_name": True}


class NameValuePairModel(BaseModel):
    """Response schema for NameValuePairs."""

    Id: int = Field(..., alias="id", description="Unique identifier for the name-value pair")
    Type: int = Field(..., alias="type", description="Type category of the name-value pair")
    Name: str = Field(..., alias="name", description="Unique name/key for the setting", max_length=255)
    Value: Optional[str] = Field(None, alias="value", description="Value associated with the name", max_length=4000)

    model_config = {"from_attributes": True, "populate_by_name": True}


class CountryCodeListResponse(BaseModel):
    """Response schema for list of country codes."""

    count: int = Field(..., description="Total number of country codes returned")
    items: list[CountryCodeModel] = Field(..., description="List of country codes")
    status: Optional[str] = Field(None, description="Status message")

class CountryCodeResponse(BaseModel):
    """Response schema for a single country code."""

    item: CountryCodeModel = Field(..., description="Country code data")
    status: Optional[str] = Field(None, description="Status message")

class StateCodeListResponse(BaseModel):
    """Response schema for list of state codes."""

    count: int = Field(..., description="Total number of state codes returned")
    items: list[StateCodeModel] = Field(..., description="List of state codes")
    status: Optional[str] = Field(None, description="Status message")

class StateCodeResponse(BaseModel):
    """Response schema for a single state code."""

    item: StateCodeModel = Field(..., description="State code data")
    status: Optional[str] = Field(None, description="Status message")

class KeyValuePairListResponse(BaseModel):
    """Response schema for list of key-value pairs."""

    count: int = Field(..., description="Total number of key-value pairs returned")
    items: list[KeyValuePairModel] = Field(..., description="List of key-value pairs")
    status: Optional[str] = Field(None, description="Status message")

class KeyValuePairResponse(BaseModel):
    """Response schema for a single key-value pair."""

    item: KeyValuePairModel = Field(..., description="Key-value pair data")
    status: Optional[str] = Field(None, description="Status message")

class NameValuePairListResponse(BaseModel):
    """Response schema for list of name-value pairs."""

    count: int = Field(..., description="Total number of name-value pairs returned")
    items: list[NameValuePairModel] = Field(..., description="List of name-value pairs")
    status: Optional[str] = Field(None, description="Status message")
    
class NameValuePairResponse(BaseModel):
    """Response schema for a single name-value pair."""

    item: NameValuePairModel = Field(..., description="Name-value pair data")
    status: Optional[str] = Field(None, description="Status message")