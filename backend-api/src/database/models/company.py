"""
Company model for SQLAlchemy ORM.

Represents the Company table with complete schema definition.
"""

from typing import Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Company(Base):
    """
    Company entity.

    Attributes:
        CompanyId: Primary key
        CompanyName: Full company name
        ShortName: Abbreviated company name
        AddressLine1: Primary address line
        AddressLine2: Secondary address line
        City: City name
        StateCode: State/province code
        PostalCode: Postal/ZIP code
        CountryCode: Country code
        PhoneNumber: Contact phone number
        EMail: Contact email address
        TaxId: Tax identification number
        Website: Company website URL
        CompanyLogo: Path or URL to company logo
    """

    __tablename__ = "Company"

    CompanyId: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique company identifier"
    )

    CompanyName: Mapped[str] = mapped_column(
        String(240),
        nullable=False,
        comment="Full company name"
    )

    ShortName: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Abbreviated company name"
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
        String(60),
        nullable=True,
        comment="City name"
    )

    StateCode: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="State or province code"
    )

    PostalCode: Mapped[Optional[str]] = mapped_column(
        String(24),
        nullable=True,
        comment="Postal or ZIP code"
    )

    CountryCode: Mapped[Optional[str]] = mapped_column(
        String(6),
        nullable=True,
        comment="Country code"
    )

    PhoneNumber: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Contact phone number"
    )

    EMail: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Contact email address"
    )

    TaxId: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Tax identification number"
    )

    Website: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Company website URL"
    )

    CompanyLogo: Mapped[Optional[str]] = mapped_column(
        String(510),
        nullable=True,
        comment="Path or URL to company logo"
    )

    def __repr__(self) -> str:
        """Return string representation of Company instance."""
        return f"<Company(CompanyId={self.CompanyId}, CompanyName='{self.CompanyName}')>"
