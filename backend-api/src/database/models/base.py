"""
Base model for SQLAlchemy ORM models.

Provides common fields and functionality for all database models including
automatic timestamps for created_at and updated_at fields.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


class BaseModel(Base):
    """
    Abstract base model with common audit fields.

    Provides id, created_at, and updated_at fields that are automatically
    managed by SQLAlchemy. All models that need timestamps should inherit
    from this base model.

    Attributes:
        id: Primary key identifier
        created_at: Timestamp when record was created (UTC)
        updated_at: Timestamp when record was last modified (UTC)
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        index=True,
        comment="Primary key identifier"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.getutcdate(),
        nullable=False,
        comment="Timestamp when record was created (UTC)"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.getutcdate(),
        onupdate=func.getutcdate(),
        nullable=False,
        comment="Timestamp when record was last modified (UTC)"
    )

    def __repr__(self) -> str:
        """Return string representation of model instance."""
        return f"<{self.__class__.__name__}(id={self.id})>"
