"""
Recurring Transaction Payments model for SQLAlchemy ORM.

Represents the RecurringTransactionPayments table with complete schema definition.
"""

from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class RecurringTransactionPayments(Base):
    """
    Recurring Transaction Payments entity.

    Represents payment history tracking for recurring transactions.
    Links recurring transactions to actual donation receipts when payments are processed.

    Attributes:
        TransactionId: Foreign key to RecurringTransactions (composite primary key)
        LineNumber: Line number within transaction (composite primary key)
        DonationReceiptId: Reference to DonationReceipts table
    """

    __tablename__ = "RecurringTransactionPayments"

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

    DonationReceiptId: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Reference to DonationReceipts table"
    )

    def __repr__(self) -> str:
        """String representation of RecurringTransactionPayments."""
        return (
            f"<RecurringTransactionPayments("
            f"TransactionId={self.TransactionId}, "
            f"LineNumber={self.LineNumber}, "
            f"DonationReceiptId={self.DonationReceiptId})>"
        )
