"""
Bank Deposit Batch model for SQLAlchemy ORM.

Represents the BankDepositBatch table with complete schema definition.
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Integer, String, DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class BankDepositBatch(Base):
    """
    Bank Deposit Batch entity.

    Represents a batch of bank deposits with header information.
    Each batch contains multiple transactions (BankDepositBatchTransactions).

    Attributes:
        BatchNumber: Primary key - unique batch identifier
        BatchDate: Date the batch was created
        BankDepositDate: Date the batch was deposited to the bank
        BatchStatus: Status code of the batch
        CreatedBy: User who created the batch
        CreatedDate: Timestamp when batch was created
        ModifiedBy: User who last modified the batch
        ModifiedDate: Timestamp when batch was last modified
        BatchMethodType: Type of batch method (e.g., 'ACH', 'Check', 'Wire')
        CompanyId: Reference to Company
        ProviderId: Payment provider identifier
        Amount: Total amount in the batch
    """

    __tablename__ = "BankDepositBatch"

    BatchNumber: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Unique batch identifier"
    )

    BatchDate: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Date the batch was created"
    )

    BankDepositDate: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Date the batch was deposited to the bank"
    )

    BatchStatus: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Status code of the batch"
    )

    CreatedBy: Mapped[str] = mapped_column(
        String(25),
        nullable=False,
        comment="User who created the batch"
    )

    CreatedDate: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Timestamp when batch was created"
    )

    ModifiedBy: Mapped[Optional[str]] = mapped_column(
        String(25),
        nullable=True,
        comment="User who last modified the batch"
    )

    ModifiedDate: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment="Timestamp when batch was last modified"
    )

    BatchMethodType: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Type of batch method (e.g., 'ACH', 'Check', 'Wire')"
    )

    CompanyId: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Reference to Company"
    )

    ProviderId: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Payment provider identifier"
    )

    Amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        comment="Total amount in the batch"
    )

    def __repr__(self) -> str:
        return f"<BankDepositBatch(BatchNumber={self.BatchNumber}, CompanyId={self.CompanyId}, Amount={self.Amount})>"
