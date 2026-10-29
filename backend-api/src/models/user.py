"""
Pydantic schemas for Users API responses.

These schemas define the structure of JSON responses for users endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, EmailStr

class User(BaseModel):
    """
    Authenticated user model populated from Auth0 JWT claims.
    Roles are extracted from the configured custom namespace claim.
    """

    id: str  # Auth0 user ID (sub claim)
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    nick_name: Optional[str] = None
    picture: Optional[str] = None
    email: Optional[str] = None
    email_verified: bool = False
    roles: list[str] = Field(default_factory=list, description="Auth0 roles assigned to this user")

    def has_role(self, role: str) -> bool:
        """Return True if the user has the specified role (case-insensitive)."""
        return role.lower() in [r.lower() for r in self.roles]

    def has_any_role(self, *roles: str) -> bool:
        """Return True if the user has at least one of the specified roles."""
        lower_user_roles = {r.lower() for r in self.roles}
        return any(r.lower() in lower_user_roles for r in roles)

    def has_all_roles(self, *roles: str) -> bool:
        """Return True if the user has all of the specified roles."""
        lower_user_roles = {r.lower() for r in self.roles}
        return all(r.lower() in lower_user_roles for r in roles)


class UserMeResponse(BaseModel):
    """
    Response model for the /auth/me endpoint.
    Returns authenticated user identity and assigned roles.
    """

    id: str = Field(description="Auth0 user ID (sub claim)")
    email: Optional[str] = Field(default=None, description="User email address")
    email_verified: bool = Field(description="Whether the email address has been verified")
    name: Optional[str] = Field(default=None, description="Full display name")
    first_name: Optional[str] = Field(default=None, description="Given name")
    last_name: Optional[str] = Field(default=None, description="Family name")
    nick_name: Optional[str] = Field(default=None, description="Nickname")
    picture: Optional[str] = Field(default=None, description="Profile picture URL")
    roles: list[str] = Field(description="Auth0 roles assigned to this user")
