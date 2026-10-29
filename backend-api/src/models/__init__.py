"""
Data models for the Masjid Connect application.

This package contains all Pydantic models used for request/response validation
and data serialization. Each model ensures type safety and automatic validation.
"""


from .error import ErrorResponse
from .health import HealthStatus, DatabaseStatus, DetailedHealthStatus
from .masterdata import (
    CountryCodeResponse,
    CountryCodeListResponse,
    StateCodeResponse,
    StateCodeListResponse,
    KeyValuePairResponse,
    KeyValuePairListResponse,
    NameValuePairResponse,
    NameValuePairListResponse,
)

# Phase 2: Entity response schemas (stubs)
from .entities import (
    OrganizationResponse,
    UserResponse,
    AuditLogResponse,
)
from .company import (
    CompanyModel,
    CompanyResponse,
    CompanyListResponse,
)
from .donation_type import (
    DonationTypeModel,
    DonationTypeResponse,
    DonationTypeListResponse,
)
from .service_type import (
    ServiceTypeModel,
    ServiceTypeResponse,
    ServiceTypeListResponse,
)   


__all__ = [
    # Error models
    "ErrorResponse",
    # Health models
    "HealthStatus",
    "DatabaseStatus",
    "DetailedHealthStatus",
    # Masterdata models
    "CountryCodeResponse",
    "CountryCodeListResponse",
    "StateCodeResponse",
    "StateCodeListResponse",
    "KeyValuePairResponse",
    "KeyValuePairListResponse",
    "NameValuePairResponse",
    "NameValuePairListResponse",
    # Phase 2 Entity Schemas (stubs)
    "OrganizationResponse",
    "UserResponse",
    "AuditLogResponse",
    # Company models
    "CompanyModel",
    "CompanyResponse",
    "CompanyListResponse",
    # DonationType models
    "DonationTypeModel",
    "DonationTypeResponse",
    "DonationTypeListResponse",
    # ServiceType models
    "ServiceTypeModel",
    "ServiceTypeResponse",
    "ServiceTypeListResponse",
]
