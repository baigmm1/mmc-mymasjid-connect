"""
Recurring Transactions model for SQLAlchemy ORM.

Represents the RecurringTransactions table with complete schema definition.
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Integer, String, DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class RecurringTransactions(Base):
    """
    Recurring Transactions entity.

    Represents a recurring donation subscription from payment providers like Stripe.
    Each transaction can have multiple line items (RecurringTransactionDetails)
    and payment history (RecurringTransactionPayments).

    Attributes:
        TransactionId: Primary key - unique transaction identifier (starts at 10001)
        CompanyId: Reference to Company
        DonorId: Reference to Donors table (nullable)
        ReviewDonorId: Reference to ReviewDonors table (nullable)
        StartDate: Subscription start date
        Frequency: Recurring frequency type (1=Monthly, 2=Yearly, etc.)
        FrequencyCount: Number of frequency units
        EndDate: Subscription end/cancellation date
        ProviderName: Payment provider name (e.g., 'Stripe', 'PayPal')
        SubscriptionId: Provider's subscription identifier
        PaymentMethod: Provider's payment method ID or description
        TotalAmount: Total subscription amount
        Status: Current status (1=Active, 2=Canceled, etc.)
        CreatedBy: User who created the record
        CreatedDate: Timestamp when record was created
        ModifiedBy: User who last modified the record
        ModifiedDate: Timestamp when record was last modified
    """

    __tablename__ = "RecurringTransactions"

    TransactionId: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique transaction identifier (starts at 10001)"
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

    StartDate: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Subscription start date"
    )

    Frequency: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Recurring frequency type (1=Monthly, 2=Yearly, etc.)"
    )

    FrequencyCount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of frequency units"
    )

    EndDate: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Subscription end/cancellation date"
    )

    ProviderName: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Payment provider name (e.g., 'Stripe', 'PayPal')"
    )

    SubscriptionId: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Provider's subscription identifier"
    )

    PaymentMethod: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Provider's payment method ID or description"
    )

    TotalAmount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(19, 4),
        nullable=True,
        comment="Total subscription amount"
    )

    Status: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Current status (1=Active, 2=Canceled, etc.)"
    )

    CreatedBy: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="User who created the record"
    )

    CreatedDate: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp when record was created"
    )

    ModifiedBy: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="User who last modified the record"
    )

    ModifiedDate: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp when record was last modified"
    )

    def __repr__(self) -> str:
        """String representation of RecurringTransactions."""
        return (
            f"<RecurringTransactions("
            f"TransactionId={self.TransactionId}, "
            f"CompanyId={self.CompanyId}, "
            f"SubscriptionId='{self.SubscriptionId}', "
            f"Status={self.Status})>"
        )
