"""
Pydantic schemas for ProviderConfiguration API responses.

These schemas define the structure of JSON responses for provider configuration endpoints.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ProviderConfigurationModel(BaseModel):
    """Response schema for ProviderConfiguration."""

    CompanyId: int = Field(..., alias="companyId", description="Company identifier")
    Provider: str = Field(..., alias="provider", description="Provider name (e.g., Stripe, PayPal)", max_length=25)
    Environment: Optional[str] = Field(None, alias="environment", description="Environment name (dev, staging, production)", max_length=25)
    MerchantId: Optional[str] = Field(None, alias="merchantId", description="Merchant identifier for the provider", max_length=255)
    PublicKey: Optional[str] = Field(None, alias="publicKey", description="Provider public key for authentication", max_length=255)
    PrivateKey: Optional[str] = Field(None, alias="privateKey", description="Provider private key (sensitive data)", max_length=255)
    Retries: Optional[int] = Field(None, alias="retries", description="Number of retries for failed requests")
    Timeout: Optional[int] = Field(None, alias="timeout", description="Request timeout in seconds")
    ApproveURL: Optional[str] = Field(None, alias="approveURL", description="URL for approved transactions", max_length=255)
    CancelURL: Optional[str] = Field(None, alias="cancelURL", description="URL for cancelled transactions", max_length=255)
    APIKey: Optional[str] = Field(None, alias="apiKey", description="API key for provider authentication (sensitive data)", max_length=255)

    model_config = {"from_attributes": True, "populate_by_name": True}


class ProviderConfigurationPublicModel(BaseModel):
    """Public response schema for ProviderConfiguration (excludes sensitive fields)."""

    CompanyId: int = Field(..., alias="companyId", description="Company identifier")
    Provider: str = Field(..., alias="provider", description="Provider name", max_length=25)
    Environment: Optional[str] = Field(None, alias="environment", description="Environment name", max_length=25)
    MerchantId: Optional[str] = Field(None, alias="merchantId", description="Merchant identifier", max_length=255)
    PublicKey: Optional[str] = Field(None, alias="publicKey", description="Provider public key", max_length=255)
    Retries: Optional[int] = Field(None, alias="retries", description="Number of retries for failed requests")
    Timeout: Optional[int] = Field(None, alias="timeout", description="Request timeout in seconds")
    ApproveURL: Optional[str] = Field(None, alias="approveURL", description="URL for approved transactions", max_length=255)
    CancelURL: Optional[str] = Field(None, alias="cancelURL", description="URL for cancelled transactions", max_length=255)

    model_config = {"from_attributes": True, "populate_by_name": True}


class ProviderConfigurationListResponse(BaseModel):
    """Response schema for list of provider configurations."""

    count: int = Field(..., description="Total number of provider configurations returned")
    items: list[ProviderConfigurationModel] = Field(..., description="List of provider configurations")
    status: Optional[str] = Field(None, description="Status message")


class ProviderConfigurationResponse(BaseModel):
    """Response schema for a single provider configuration."""

    item: ProviderConfigurationModel = Field(..., description="Provider configuration data")
    status: Optional[str] = Field(None, description="Status message")
