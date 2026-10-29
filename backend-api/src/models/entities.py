"""
Pydantic schemas for Organization, User, and AuditLog API responses (stubs).

Minimal implementation - to be expanded based on actual project requirements.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, EmailStr


class OrganizationResponse(BaseModel):
    """Response schema for Organization (stub)."""

    id: int = Field(..., alias="id", description="Unique identifier")
    name: str = Field(..., alias="name", description="Organization name")
    created_at: datetime = Field(..., alias="createdAt", description="Timestamp when created (UTC)")
    updated_at: datetime = Field(..., alias="updatedAt", description="Timestamp when last modified (UTC)")

    model_config = {"from_attributes": True, "populate_by_name": True}


class UserResponse(BaseModel):
    """Response schema for User (stub)."""

    id: int = Field(..., alias="id", description="Unique identifier")
    email: str = Field(..., alias="email", description="Email address")
    full_name: str = Field(..., alias="fullName", description="User's full name")
    created_at: datetime = Field(..., alias="createdAt", description="Timestamp when created (UTC)")
    updated_at: datetime = Field(..., alias="updatedAt", description="Timestamp when last modified (UTC)")

    model_config = {"from_attributes": True, "populate_by_name": True}


class AuditLogResponse(BaseModel):
    """Response schema for AuditLog (stub)."""

    id: int = Field(..., alias="id", description="Unique identifier")
    action: str = Field(..., alias="action", description="Action performed")
    entity_type: str = Field(..., alias="entityType", description="Type of entity affected")
    timestamp: datetime = Field(..., alias="timestamp", description="When action occurred (UTC)")

    model_config = {"from_attributes": True, "populate_by_name": True}
