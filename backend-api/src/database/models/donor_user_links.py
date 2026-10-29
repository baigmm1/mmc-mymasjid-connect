"""
SQLAlchemy model for DonorUserLinks table.

Represents the relationship between users and donor records.
"""

from typing import Optional

from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.database.models.base import Base


class DonorUserLinks(Base):
    """
    DonorUserLinks database model.
    
    Links user accounts to donor records, enabling authenticated users
    to access their donation history and profile.
    """
    
    __tablename__ = "DonorUserLinks"
    
    # Composite Primary Key
    UserId: Mapped[str] = mapped_column(String(100), primary_key=True, nullable=False)
    DonorId: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("Donors.DonorId"),
        primary_key=True,
        nullable=False
    )
    
    # Status
    StatusCode: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    def __repr__(self) -> str:
        return f"<DonorUserLinks(user_id={self.UserId}, donor_id={self.DonorId}, status={self.StatusCode})>"
