"""
Pledges model for SQLAlchemy ORM.

Represents the Pledges table for recording and tracking donor pledges.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Pledges(Base):
    """
    Pledges entity.

    Stores pledge commitments made by donors, including the amount pledged,
    donation type, contact information, and confirmation status.

    Attributes:
        PledgeRecordID: Primary key (identity starting at 1001)
        CompanyId: Reference to Company (required)
        DonorId: Reference to the Donors table (nullable)
        ReviewDonorId: Reference to ReviewDonors table (nullable)
        PledgeBy: Name of the person making the pledge (required)
        PledgeEmail: Email address of the pledger
        PledgePhoneNumber: Phone number of the pledger
        PledgeDonationType: Reference to donation type
        AmountPledged: Amount committed in the pledge
        DatePledged: Date the pledge was made (required)
        DateConfirmed: Date the pledge was confirmed/fulfilled
        StatusCode: Status code (e.g. 1=Pending, 2=Confirmed, 3=Cancelled)
        CreatedBy: User ID who created the record
        CreatedDate: Record creation timestamp
        ModifiedBy: User ID who last modified the record
        ModifiedDate: Last modification timestamp
    """

    __tablename__ = "Pledges"

    PledgeRecordID: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique pledge identifier (identity column, starts at 1001)"
    )
    CompanyId: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Reference to Company"
    )
    DonorId: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Reference to Donors table"
    )

    ReviewDonorId: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Reference to ReviewDonors table"
    )

    PledgeBy: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Name of the person making the pledge"
    )

    PledgeEmail: Mapped[Optional[str]] = mapped_column(
        String(120),
        nullable=True,
        comment="Email address of the pledger"
    )

    PledgePhoneNumber: Mapped[Optional[str]] = mapped_column(
        String(25),
        nullable=True,
        comment="Phone number of the pledger"
    )

    PledgeDonationType: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Reference to donation type"
    )

    AmountPledged: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(19, 4),
        nullable=True,
        comment="Amount committed in the pledge"
    )

    DatePledged: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Date the pledge was made"
    )

    DateConfirmed: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Date the pledge was confirmed/fulfilled"
    )

    StatusCode: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Status code (1=Pending, 2=Confirmed, 3=Cancelled)"
    )

    CreatedBy: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="User ID who created the record"
    )

    CreatedDate: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
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
        comment="Last modification timestamp"
    )
