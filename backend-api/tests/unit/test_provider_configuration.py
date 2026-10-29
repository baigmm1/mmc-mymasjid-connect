"""
Unit tests for ProviderConfiguration models and utilities.

Tests cover:
- Database model creation
- Pydantic model validation
- Cache operations
- Utility functions
"""

import pytest
from sqlalchemy import select

from src.core.cache_manager import (
    clear_provider_configuration_cache,
    get_provider_configuration_from_cache,
    get_provider_configurations_for_company_from_cache,
    initialize_caches,
    warm_provider_configuration_cache,
)
from src.core.provider_config_utils import (
    get_all_provider_configs_for_company,
    get_provider_api_key,
    get_provider_config,
    get_provider_merchant_id,
    get_provider_private_key,
    get_provider_public_key,
    get_provider_retries,
    get_provider_timeout,
)
from src.database.models.provider_configuration import ProviderConfiguration
from src.models.provider_configuration import ProviderConfigurationModel


@pytest.mark.unit
class TestProviderConfigurationModel:
    """Test suite for ProviderConfiguration database model."""

    def test_create_provider_configuration(self):
        """Test creating a ProviderConfiguration instance."""
        config = ProviderConfiguration(
            CompanyId=1,
            Provider="Stripe",
            Environment="production",
            MerchantId="merchant_123",
            PublicKey="pk_test_123",
            PrivateKey="sk_test_123",
            APIKey="api_key_123",
            Retries=3,
            Timeout=30,
            ApproveURL="https://example.com/approve",
            CancelURL="https://example.com/cancel",
        )

        assert config.CompanyId == 1
        assert config.Provider == "Stripe"
        assert config.Environment == "production"
        assert config.MerchantId == "merchant_123"
        assert config.PublicKey == "pk_test_123"
        assert config.PrivateKey == "sk_test_123"
        assert config.APIKey == "api_key_123"
        assert config.Retries == 3
        assert config.Timeout == 30

    def test_provider_configuration_repr(self):
        """Test string representation of ProviderConfiguration."""
        config = ProviderConfiguration(
            CompanyId=1,
            Provider="Stripe",
            Environment="production",
        )
        repr_str = repr(config)
        assert "ProviderConfiguration" in repr_str
        assert "CompanyId=1" in repr_str
        assert "Provider=Stripe" in repr_str


@pytest.mark.unit
class TestProviderConfigurationPydanticModel:
    """Test suite for ProviderConfiguration Pydantic models."""

    def test_provider_configuration_model_validation(self):
        """Test Pydantic model validation with all fields."""
        data = {
            "CompanyId": 1,
            "Provider": "Stripe",
            "Environment": "production",
            "MerchantId": "merchant_123",
            "PublicKey": "pk_test_123",
            "PrivateKey": "sk_test_123",
            "APIKey": "api_key_123",
            "Retries": 3,
            "Timeout": 30,
            "ApproveURL": "https://example.com/approve",
            "CancelURL": "https://example.com/cancel",
        }

        model = ProviderConfigurationModel(**data)
        assert model.CompanyId == 1
        assert model.Provider == "Stripe"
        assert model.Environment == "production"

    def test_provider_configuration_model_with_aliases(self):
        """Test Pydantic model with camelCase aliases."""
        data = {
            "companyId": 1,
            "provider": "PayPal",
            "environment": "staging",
            "merchantId": "merchant_456",
        }

        model = ProviderConfigurationModel(**data)
        assert model.CompanyId == 1
        assert model.Provider == "PayPal"

    def test_provider_configuration_minimal_fields(self):
        """Test Pydantic model with minimal required fields."""
        data = {
            "CompanyId": 1,
            "Provider": "Stripe",
        }

        model = ProviderConfigurationModel(**data)
        assert model.CompanyId == 1
        assert model.Provider == "Stripe"
        assert model.Environment is None
        assert model.APIKey is None


@pytest.mark.unit
class TestProviderConfigUtilities:
    """Test suite for provider configuration utility functions."""

    def test_get_provider_api_key(self):
        """Test extracting API key from config."""
        config = ProviderConfiguration(
            CompanyId=1,
            Provider="Stripe",
            APIKey="api_key_123",
        )
        assert get_provider_api_key(config) == "api_key_123"
        assert get_provider_api_key(None) is None

    def test_get_provider_public_key(self):
        """Test extracting public key from config."""
        config = ProviderConfiguration(
            CompanyId=1,
            Provider="Stripe",
            PublicKey="pk_test_123",
        )
        assert get_provider_public_key(config) == "pk_test_123"

    def test_get_provider_timeout_with_default(self):
        """Test extracting timeout with default value."""
        config = ProviderConfiguration(
            CompanyId=1,
            Provider="Stripe",
            Timeout=60,
        )
        assert get_provider_timeout(config) == 60
        assert get_provider_timeout(None) == 30
        assert get_provider_timeout(None, default=45) == 45

    def test_get_provider_retries_with_default(self):
        """Test extracting retries with default value."""
        config = ProviderConfiguration(
            CompanyId=1,
            Provider="Stripe",
            Retries=5,
        )
        assert get_provider_retries(config) == 5
        assert get_provider_retries(None) == 3
        assert get_provider_retries(None, default=10) == 10
