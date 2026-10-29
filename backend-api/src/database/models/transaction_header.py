"""
SQLAlchemy model for TransactionHeader table.

Represents donation transactions in the system.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base


class TransactionHeader(Base):
    """TransactionHeader database model."""
    
    __tablename__ = "TransactionHeader"
    
    # Primary Key
    TransactionId: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Keys
    CompanyId: Mapped[int] = mapped_column(Integer, ForeignKey("Company.CompanyId"), nullable=False)
    DonorId: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("Donors.DonorId"), nullable=True)
    
    # Terminal/Device
    TerminalId: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Donor Information (cached for non-registered donors)
    DonorName: Mapped[Optional[str]] = mapped_column(String(240), nullable=True)
    DonorPhone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    DonorEmail: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    DonorBillingZip: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Transaction Details
    TransactionDate: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    PurposeId: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    TotalAmount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    Currency: Mapped[Optional[str]] = mapped_column(String(6), default="USD", nullable=True)
    
    # Recurring Donation Fields
    Recurring: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)
    NumberofMonths: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # 1 = Monthly (default), 2 = Yearly, 3 = Daily
    RecurringFrequency: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Payment Information
    PaymentMethod: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    PaymentMethodId: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    Provider: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    ProviderName: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ProviderId: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ProviderToken: Mapped[Optional[str]] = mapped_column(String(510), nullable=True)
    
    # Checkout URLs
    SuccessURL: Mapped[Optional[str]] = mapped_column(String(510), nullable=True)
    CancelURL: Mapped[Optional[str]] = mapped_column(String(510), nullable=True)
    CheckoutURL: Mapped[Optional[str]] = mapped_column(String(510), nullable=True)
    
    # Status
    Status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    StatusCode: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Audit Fields
    CreatedDate: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    CreatedBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ModifiedDate: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ModifiedBy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Relationships
    # details: Mapped[list["TransactionDetails"]] = relationship(back_populates="transaction")
    
    def __repr__(self) -> str:
        return f"<TransactionHeader(id={self.TransactionId}, amount={self.TotalAmount}, status={self.Status})>"
