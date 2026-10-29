"""
Recurring Transaction Details model for SQLAlchemy ORM.

Represents the RecurringTransactionDetails table with complete schema definition.
"""

from typing import Optional
from decimal import Decimal

from sqlalchemy import Integer, String, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class RecurringTransactionDetails(Base):
    """
    Recurring Transaction Details entity.

    Represents line item details for a recurring transaction.
    Each recurring transaction can have multiple detail lines for different donation types.

    Attributes:
        TransactionId: Foreign key to RecurringTransactions (composite primary key)
        LineNumber: Line number within transaction (composite primary key)
        CompanyId: Reference to Company
        DonationType: Type of donation (reference to DonationType)
        Amount: Line item amount
        Currency: Currency code (e.g., 'USD', 'CAD')
    """

    __tablename__ = "RecurringTransactionDetails"

    TransactionId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("RecurringTransactions.TransactionId"),
        primary_key=True,
        comment="Foreign key to RecurringTransactions"
    )

    LineNumber: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        comment="Line number within transaction"
    )

    CompanyId: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Reference to Company"
    )

    DonationType: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Type of donation (reference to DonationType)"
    )

    Amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(19, 4),
        nullable=True,
        comment="Line item amount"
    )

    Currency: Mapped[Optional[str]] = mapped_column(
        String(3),
        nullable=True,
        comment="Currency code (e.g., 'USD', 'CAD')"
    )

    def __repr__(self) -> str:
        """String representation of RecurringTransactionDetails."""
        return (
            f"<RecurringTransactionDetails("
            f"TransactionId={self.TransactionId}, "
            f"LineNumber={self.LineNumber}, "
            f"DonationType={self.DonationType}, "
            f"Amount={self.Amount})>"
        )
