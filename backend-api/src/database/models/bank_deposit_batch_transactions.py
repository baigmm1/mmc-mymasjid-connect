"""
Bank Deposit Batch Transactions model for SQLAlchemy ORM.

Represents the BankDepositBatchTransactions table with complete schema definition.
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Integer, String, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class BankDepositBatchTransactions(Base):
    """
    Bank Deposit Batch Transactions entity.

    Represents individual transaction line items within a BankDepositBatch.
    Each transaction is linked to a donation receipt.

    Attributes:
        CompanyId: Reference to Company
        BatchNumber: Foreign key to BankDepositBatch
        LineNumber: Sequential line number within the batch
        DonationReceiptId: Reference to the donation receipt
        ProviderId: Payment provider identifier
        TransactionType: Type of transaction
        Amount: Amount for this transaction
        CreatedBy: User ID who created the transaction
        CreatedDate: Timestamp when transaction was created
        ModifiedBy: User ID who last modified the transaction
        ModifiedDate: Timestamp when transaction was last modified
    """

    __tablename__ = "BankDepositBatchTransactions"

    # Composite Primary Key
    CompanyId: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Reference to Company",
        primary_key=True
    )

    BatchNumber: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("BankDepositBatch.BatchNumber"),
        nullable=False,
        comment="Foreign key to BankDepositBatch",
        primary_key=True
    )

    LineNumber: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Sequential line number within the batch",
        primary_key=True
    )

    DonationReceiptId: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Reference to the donation receipt"
    )

    ProviderId: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Payment provider identifier"
    )

    TransactionType: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Type of transaction"
    )

    Amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2),
        nullable=True,
        comment="Amount for this transaction"
    )

    FeeAmount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2),
        nullable=True,
        comment="Transaction fee amount"
    )

    CreatedBy: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="User ID who created the transaction"
    )

    CreatedDate: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp when transaction was created"
    )

    ModifiedBy: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="User ID who last modified the transaction"
    )

    ModifiedDate: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp when transaction was last modified"
    )

    def __repr__(self) -> str:
        return f"<BankDepositBatchTransactions(BatchNumber={self.BatchNumber}, LineNumber={self.LineNumber}, Amount={self.Amount})>"
