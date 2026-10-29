"""
User model stub for SQLAlchemy ORM.

Minimal implementation - to be expanded based on actual project requirements.
"""

from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel


class User(BaseModel):
    """
    User entity (stub implementation).

    This is a minimal stub implementation. Expand based on actual project requirements.

    Attributes:
        id: Primary key (inherited from BaseModel)
        email: User email address
        full_name: User's full name
        created_at: Timestamp when created (inherited from BaseModel)
        updated_at: Timestamp when last modified (inherited from BaseModel)
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="User email address"
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User's full name"
    )

    def __repr__(self) -> str:
        """Return string representation of User instance."""
        return f"<User(id={self.id}, email='{self.email}')>"
