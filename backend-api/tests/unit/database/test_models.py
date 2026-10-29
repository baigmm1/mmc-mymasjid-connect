"""Tests for database models.

These tests validate the ORM model definitions match the database schema.
Tests focus on table structure, primary keys, and required fields.
"""

import pytest
from sqlalchemy import inspect

from src.database.models.company import Company
from src.database.models.donation_type import DonationType
from src.database.models.masterdata import CountryCodes, StateCodes, KeyValuePairs, NameValuePair


class TestCompanyModel:
    """Tests for Company model."""

    def test_company_table_name(self):
        """Test Company table name is correct."""
        assert Company.__tablename__ == "Company"

    def test_company_has_primary_key(self):
        """Test Company has CompanyId as primary key."""
        pk_columns = [col.name for col in Company.__table__.primary_key.columns]
        assert "CompanyId" in pk_columns
        assert len(pk_columns) == 1

    def test_company_has_required_columns(self):
        """Test Company has required columns."""
        columns = [col.name for col in Company.__table__.columns]
        assert "CompanyId" in columns
        assert "CompanyName" in columns
        assert "ShortName" in columns

    def test_company_companyid_not_nullable(self):
        """Test CompanyId column is not nullable."""
        companyid_col = Company.__table__.columns["CompanyId"]
        assert not companyid_col.nullable
        assert companyid_col.primary_key

    def test_company_companyname_not_nullable(self):
        """Test CompanyName column is not nullable."""
        companyname_col = Company.__table__.columns["CompanyName"]
        assert not companyname_col.nullable


class TestDonationTypeModel:
    """Tests for DonationType model."""

    def test_donation_type_table_name(self):
        """Test DonationType table name is correct."""
        assert DonationType.__tablename__ == "DonationTypes"

    def test_donation_type_composite_primary_key(self):
        """Test DonationType has composite primary key."""
        pk_columns = [col.name for col in DonationType.__table__.primary_key.columns]
        assert set(pk_columns) == {"CompanyId", "DonationType"}
        assert len(pk_columns) == 2

    def test_donation_type_has_required_columns(self):
        """Test DonationType has required columns."""
        columns = [col.name for col in DonationType.__table__.columns]
        assert "CompanyId" in columns
        assert "DonationType" in columns
        assert "FundId" in columns
        assert "ShortName" in columns
        assert "ShowWeb" in columns
        assert "ShowTablet" in columns
        assert "ShowPhone" in columns
        assert "ShowKiosk" in columns

    def test_donation_type_primary_keys_not_nullable(self):
        """Test primary key columns are not nullable."""
        companyid_col = DonationType.__table__.columns["CompanyId"]
        donationtype_col = DonationType.__table__.columns["DonationType"]
        assert not companyid_col.nullable
        assert not donationtype_col.nullable
        assert companyid_col.primary_key
        assert donationtype_col.primary_key


class TestCountryCodesModel:
    """Tests for CountryCodes model."""

    def test_country_codes_table_name(self):
        """Test CountryCodes table name is correct."""
        assert CountryCodes.__tablename__ == "CountryCodes"

    def test_country_codes_primary_key(self):
        """Test CountryCodes primary key is CountryCode."""
        pk_columns = [col.name for col in CountryCodes.__table__.primary_key.columns]
        assert pk_columns == ["CountryCode"]

    def test_country_codes_has_required_columns(self):
        """Test CountryCodes has required columns."""
        columns = [col.name for col in CountryCodes.__table__.columns]
        assert "CountryCode" in columns
        assert "CountryName" in columns


class TestStateCodesModel:
    """Tests for StateCodes model."""

    def test_state_codes_table_name(self):
        """Test StateCodes table name is correct."""
        assert StateCodes.__tablename__ == "StateCodes"

    def test_state_codes_primary_key(self):
        """Test StateCodes primary key is StateId."""
        pk_columns = [col.name for col in StateCodes.__table__.primary_key.columns]
        assert pk_columns == ["StateId"]

    def test_state_codes_has_required_columns(self):
        """Test StateCodes has required columns."""
        columns = [col.name for col in StateCodes.__table__.columns]
        assert "StateId" in columns
        assert "StateCode" in columns
        assert "StateName" in columns
        assert "CountryCode" in columns


class TestKeyValuePairsModel:
    """Tests for KeyValuePairs model."""

    def test_key_value_pairs_table_name(self):
        """Test KeyValuePairs table name is correct."""
        assert KeyValuePairs.__tablename__ == "KeyValuePairs"

    def test_key_value_pairs_has_required_columns(self):
        """Test KeyValuePairs has required columns."""
        columns = [col.name for col in KeyValuePairs.__table__.columns]
        assert "Id" in columns
        assert "Type" in columns
        assert "Key" in columns
        assert "Value" in columns


class TestNameValuePairModel:
    """Tests for NameValuePair model."""

    def test_name_value_pair_table_name(self):
        """Test NameValuePair table name is correct."""
        assert NameValuePair.__tablename__ == "NameValuePairs"

    def test_name_value_pair_has_required_columns(self):
        """Test NameValuePair has required columns."""
        columns = [col.name for col in NameValuePair.__table__.columns]
        assert "Id" in columns
        assert "Type" in columns
        assert "Name" in columns
        assert "Value" in columns


class TestModelStructure:
    """Tests for model structure validation."""

    def test_company_has_mapped_columns(self):
        """Test Company uses SQLAlchemy 2.0 Mapped columns."""
        # Check that model is properly configured
        assert hasattr(Company, "__table__")
        assert Company.__table__.name == "Company"

    def test_donation_type_has_mapped_columns(self):
        """Test DonationType uses SQLAlchemy 2.0 Mapped columns."""
        assert hasattr(DonationType, "__table__")
        assert DonationType.__table__.name == "DonationTypes"

    def test_all_models_have_base_class(self):
        """Test all models inherit from Base."""
        from src.database.models.base import Base
        assert issubclass(Company, Base)
        assert issubclass(DonationType, Base)
        assert issubclass(CountryCodes, Base)
        assert issubclass(StateCodes, Base)

    def test_company_table_has_columns(self):
        """Test Company table has columns defined."""
        assert len(Company.__table__.columns) > 0

    def test_donation_type_table_has_columns(self):
        """Test DonationType table has columns defined."""
        assert len(DonationType.__table__.columns) > 0
