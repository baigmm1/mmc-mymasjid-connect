"""
DonationType model for SQLAlchemy ORM.

Represents the DonationType table with complete schema definition.
"""

from typing import Optional

from sqlalchemy import Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DonationType(Base):
    """
    DonationType entity.

    Attributes:
        CompanyId: Company identifier (part of composite key)
        DonationType: Donation type identifier (part of composite key)
        FundId: Associated fund identifier
        ShortName: Abbreviated donation type name
        ShortDescription: Brief description
        Description: Full description
        DetailedTextHeader: Header for detailed text
        DetailedText: Detailed text content (unlimited length)
        TaxReceipt: Tax receipt flag
        AccountNumber: Associated account number
        ShowWeb: Display on web flag
        ShowTablet: Display on tablet flag
        ShowPhone: Display on phone flag
        ShowKiosk: Display on kiosk flag
        ShowPledge: Display on pledge page flag
        SuggestedAmounts: Suggested donation amounts
        ImageURL: Primary image URL
        ImageHeaderURL: Header image URL
        ImageURLList: List image URL
        SortOrder: Display sort order
        StatusCode: Status code
    """

    __tablename__ = "DonationTypes"

    CompanyId: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        comment="Company identifier"
    )

    DonationType: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        comment="Donation type identifier"
    )

    FundId: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Associated fund identifier"
    )

    ShortName: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Abbreviated donation type name"
    )

    ShortDescription: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Brief description"
    )

    Description: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Full description"
    )

    DetailedTextHeader: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Header for detailed text"
    )

    DetailedText: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed text content (unlimited length)"
    )

    TaxReceipt: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
        comment="Tax receipt flag"
    )

    AccountNumber: Mapped[Optional[str]] = mapped_column(
        String(40),
        nullable=True,
        comment="Associated account number"
    )

    ShowWeb: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
        comment="Display on web flag"
    )

    ShowTablet: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
        comment="Display on tablet flag"
    )

    ShowPhone: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
        comment="Display on phone flag"
    )

    ShowKiosk: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
        comment="Display on kiosk flag"
    )
    ShowPledge: Mapped[Optional[int]] = mapped_column(
        SmallInteger,
        nullable=True,
        comment="Display on pledge page"
    )
    SuggestedAmounts: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Suggested donation amounts"
    )

    ImageURL: Mapped[Optional[str]] = mapped_column(
        String(510),
        nullable=True,
        comment="Primary image URL"
    )

    ImageHeaderURL: Mapped[Optional[str]] = mapped_column(
        String(510),
        nullable=True,
        comment="Header image URL"
    )

    ImageURLList: Mapped[Optional[str]] = mapped_column(
        String(510),
        nullable=True,
        comment="List image URL"
    )

    SortOrder: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Display sort order"
    )

    StatusCode: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Status code"
    )

    def __repr__(self) -> str:
        """Return string representation of DonationType instance."""
        return f"<DonationType(CompanyId={self.CompanyId}, DonationType={self.DonationType}, ShortName='{self.ShortName}')>"
