"""
Donors model for SQLAlchemy ORM.

Represents the Donors table for managing donor information.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Donors(Base):
    """
    Donors entity.

    Stores comprehensive donor information including contact details,
    preferences, and audit fields.

    Attributes:
        DonorId: Primary key (identity/auto-increment)
        NamePrefix: Name prefix (Mr., Mrs., Dr., etc.)
        CompleteName: Full name of the donor (always filled)
        FirstName: First name (derived from CompleteName)
        MiddleName: Middle name (derived from CompleteName)
        LastName: Last name (derived from CompleteName)
        Suffix: Name suffix (Jr., Sr., III, etc.)
        CompanyName: Company or organization name
        TaxReceiptName: Name for tax receipt
        AddressLine1: Primary address line
        AddressLine2: Secondary address line
        City: City name
        State: State/province code
        PostalCode: Postal/ZIP code
        CountryCode: Country code
        PhoneNumber: Contact phone number
        EMail: Email address
        Occupation: Donor's occupation
        Physician: Whether donor is a physician
        IncorrectAddress: Flag for incorrect address
        PublishinDonorList: Whether to publish in donor list
        TaxReceiptRequired: Whether tax receipt is required
        StatusCode: Status code
        CreatedBy: User ID who created the record
        CreatedDate: Record creation timestamp
        ModifiedBy: User ID who last modified the record
        ModifiedDate: Last modification timestamp
    """

    __tablename__ = "Donors"

    DonorId: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique donor identifier (identity column)"
    )

    NamePrefix: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Name prefix (Mr., Mrs., Dr., etc.)"
    )

    CompleteName: Mapped[Optional[str]] = mapped_column(
        String(240),
        nullable=True,
        index=True,
        comment="Complete name of the donor"
    )

    FirstName: Mapped[Optional[str]] = mapped_column(
        String(60),
        nullable=True,
        index=True,
        comment="First name (derived from CompleteName)"
    )

    MiddleName: Mapped[Optional[str]] = mapped_column(
        String(60),
        nullable=True,
        comment="Middle name (derived from CompleteName)"
    )

    LastName: Mapped[Optional[str]] = mapped_column(
        String(60),
        nullable=True,
        index=True,
        comment="Last name (derived from CompleteName)"
    )

    Suffix: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Name suffix (Jr., Sr., III, etc.)"
    )

    CompanyName: Mapped[Optional[str]] = mapped_column(
        String(240),
        nullable=True,
        comment="Company or organization name"
    )

    TaxReceiptName: Mapped[Optional[str]] = mapped_column(
        String(240),
        nullable=True,
        comment="Name for tax receipt purposes"
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
        index=True,
        comment="Email address"
    )

    Occupation: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Donor's occupation"
    )

    Physician: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        default=False,
        comment="Whether donor is a physician"
    )

    IncorrectAddress: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        default=False,
        comment="Flag for incorrect address"
    )

    PublishinDonorList: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        default=True,
        comment="Whether to publish in donor list"
    )

    TaxReceiptRequired: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        default=True,
        comment="Whether tax receipt is required"
    )

    StatusCode: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Status code"
    )

    CreatedBy: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="User ID who created the record"
    )

    CreatedDate: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        default=datetime.utcnow,
        comment="Record creation timestamp"
    )

    ModifiedBy: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="User ID who last modified the record"
    )

    ModifiedDate: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        onupdate=datetime.utcnow,
        comment="Last modification timestamp"
    )

    def __repr__(self) -> str:
        """String representation of Donors."""
        return f"<Donors(DonorId={self.DonorId}, CompleteName={self.CompleteName}, EMail={self.EMail})>"
