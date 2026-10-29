"""
ProviderConfiguration model for SQLAlchemy ORM.

Represents the ProviderConfiguration table with complete schema definition.
Stores payment provider configurations for different companies and environments.
"""

from typing import Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ProviderConfiguration(Base):
    """
    Provider Configuration entity.

    Stores payment provider settings for different companies and providers.
    Composite primary key: (CompanyId, Provider)

    Attributes:
        CompanyId: Company identifier (part of composite PK)
        Provider: Provider name (part of composite PK)
        Environment: Environment name (dev, staging, production)
        MerchantId: Merchant identifier for the provider
        PublicKey: Provider public key for authentication
        PrivateKey: Provider private key for authentication
        Retries: Number of retries for failed requests
        Timeout: Request timeout in seconds
        ApproveURL: URL for approved transactions
        CancelURL: URL for cancelled transactions
        APIKey: API key for provider authentication
    """

    __tablename__ = "ProviderConfiguration"

    CompanyId: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
        comment="Company identifier"
    )

    Provider: Mapped[str] = mapped_column(
        String(25),
        primary_key=True,
        nullable=False,
        comment="Provider name (e.g., Stripe, PayPal)"
    )

    Environment: Mapped[Optional[str]] = mapped_column(
        String(25),
        nullable=True,
        comment="Environment name (dev, staging, production)"
    )

    MerchantId: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Merchant identifier for the provider"
    )

    PublicKey: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Provider public key for authentication"
    )

    PrivateKey: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Provider private key for authentication (sensitive data)"
    )

    Retries: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of retries for failed requests"
    )

    Timeout: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Request timeout in seconds"
    )

    ApproveURL: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="URL for approved transactions"
    )

    CancelURL: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="URL for cancelled transactions"
    )

    APIKey: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="API key for provider authentication (sensitive data)"
    )

    def __repr__(self) -> str:
        """String representation of ProviderConfiguration."""
        return f"<ProviderConfiguration(CompanyId={self.CompanyId}, Provider={self.Provider}, Environment={self.Environment})>"
