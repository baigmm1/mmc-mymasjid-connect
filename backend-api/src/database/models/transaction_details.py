"""
SQLAlchemy model for TransactionDetails table.

Represents line items/details for donation transactions.
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Integer, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base


class TransactionDetails(Base):
    """TransactionDetails database model."""
    
    __tablename__ = "TransactionDetails"
    
    # Composite Primary Key
    TransactionId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("TransactionHeader.TransactionId"),
        primary_key=True,
        nullable=False
    )
    LineNumber: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    
    # Line Item Details
    Description: Mapped[Optional[str]] = mapped_column(String(240), nullable=True)
    DonationTypeId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("DonationType.DonationTypeId"),
        nullable=False
    )
    Amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    
    # Fee Information
    FeePercent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    FeeAmount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    
    # Relationships
    # transaction: Mapped["TransactionHeader"] = relationship(back_populates="details")
    # donation_type: Mapped["DonationType"] = relationship()
    
    def __repr__(self) -> str:
        return f"<TransactionDetails(txn_id={self.TransactionId}, line={self.LineNumber}, amount={self.Amount})>"
