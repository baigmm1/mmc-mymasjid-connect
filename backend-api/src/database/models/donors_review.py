"""
DonorsReview model for SQLAlchemy ORM.

Represents the Donors_Review table for managing donor records pending review.
"""

from typing import Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DonorsReview(Base):
    """
    Donors Review entity.

    Stores donor information pending review/approval before being added
    to the main Donors table.

    Attributes:
        DonorId: Primary key (identity/auto-increment)
        CompanyId: Company identifier
        NamePrefix: Name prefix (Mr., Mrs., Dr., etc.)
        CompleteName: Full name of the donor
        AddressLine1: Primary address line
        AddressLine2: Secondary address line
        City: City name
        State: State/province code
        PostalCode: Postal/ZIP code
        CountryCode: Country code
        PhoneNumber: Contact phone number
        EMail: Email address
    """

    __tablename__ = "Donors_Review"

    DonorId: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique donor identifier (identity column)"
    )

    CompanyId: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="Company identifier"
    )

    NamePrefix: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Name prefix (Mr., Mrs., Dr., etc.)"
    )

    CompleteName: Mapped[Optional[str]] = mapped_column(
        String(240),
        nullable=True,
        comment="Complete name of the donor"
    )

    AddressLine1: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Primary address line"
    )

    AddressLine2: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Secondary address line"
    )

    City: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="City name"
    )

    State: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="State or province code"
    )

    PostalCode: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Postal or ZIP code"
    )

    CountryCode: Mapped[Optional[str]] = mapped_column(
        String(6),
        nullable=True,
        comment="Country code"
    )

    PhoneNumber: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Contact phone number"
    )

    EMail: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Email address"
    )

    def __repr__(self) -> str:
        """String representation of DonorsReview."""
        return f"<DonorsReview(DonorId={self.DonorId}, CompanyId={self.CompanyId}, CompleteName={self.CompleteName})>"
