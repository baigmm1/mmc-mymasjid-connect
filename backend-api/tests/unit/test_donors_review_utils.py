"""
Unit tests for DonorsReview utility functions.

Tests cover:
- Creating donor review records
- Retrieving donor review records
- Deleting donor review records
- Finding donors by email
- Validation functions
- Bulk operations
"""

import pytest
from sqlalchemy import select

from src.core.donors_review_utils import (
    bulk_create_donor_reviews,
    count_pending_reviews_for_company,
    create_donor_review_record,
    delete_donor_review_record,
    find_donor_review_by_email,
    get_donor_review_by_id,
    get_donors_review_for_company,
    validate_donor_data,
)
from src.database.models.donors_review import DonorsReview


@pytest.mark.unit
class TestDonorReviewValidation:
    """Test suite for donor review validation functions."""

    def test_validate_donor_data_with_name(self):
        """Test validation with complete name."""
        is_valid, error = validate_donor_data(complete_name="John Doe")
        assert is_valid is True
        assert error is None

    def test_validate_donor_data_with_email(self):
        """Test validation with email."""
        is_valid, error = validate_donor_data(email="john@example.com")
        assert is_valid is True
        assert error is None

    def test_validate_donor_data_with_phone(self):
        """Test validation with phone number."""
        is_valid, error = validate_donor_data(phone_number="555-1234")
        assert is_valid is True
        assert error is None

    def test_validate_donor_data_empty(self):
        """Test validation with no data."""
        is_valid, error = validate_donor_data()
        assert is_valid is False
        assert "at least one" in error.lower()

    def test_validate_donor_data_invalid_email(self):
        """Test validation with invalid email."""
        is_valid, error = validate_donor_data(email="invalid-email")
        assert is_valid is False
        assert "email" in error.lower()

    def test_validate_donor_data_name_too_long(self):
        """Test validation with name exceeding max length."""
        long_name = "A" * 241
        is_valid, error = validate_donor_data(complete_name=long_name)
        assert is_valid is False
        assert "240" in error

    def test_validate_donor_data_email_too_long(self):
        """Test validation with email exceeding max length."""
        long_email = "test@" + ("a" * 510) + ".com"
        is_valid, error = validate_donor_data(email=long_email)
        assert is_valid is False
        assert "512" in error

    def test_validate_donor_data_all_fields(self):
        """Test validation with all fields."""
        is_valid, error = validate_donor_data(
            complete_name="John Doe",
            email="john@example.com",
            phone_number="555-1234"
        )
        assert is_valid is True
        assert error is None


@pytest.mark.unit
class TestDonorReviewUtilityHelpers:
    """Test suite for utility helper functions."""

    def test_validate_with_valid_data(self):
        """Test validation helper with valid data."""
        is_valid, error = validate_donor_data(
            complete_name="John Doe",
            email="john@example.com",
            phone_number="555-1234"
        )
        assert is_valid is True

    def test_validate_with_minimal_data(self):
        """Test validation with minimal required data."""
        is_valid, error = validate_donor_data(email="test@example.com")
        assert is_valid is True


# Integration tests would require a database session
@pytest.mark.integration
class TestDonorReviewUtilityIntegration:
    """Test suite for donor review utility integration tests."""

    async def test_create_and_retrieve_donor_review(self, db_session):
        """Test creating and retrieving a donor review record."""
        # Create donor review
        donor = await create_donor_review_record(
            session=db_session,
            company_id=1,
            complete_name="Test Donor",
            email="test@example.com",
            phone_number="555-9999"
        )

        assert donor is not None
        assert donor.DonorId is not None
        assert donor.CompleteName == "Test Donor"
        assert donor.EMail == "test@example.com"

        # Retrieve the same donor
        retrieved = await get_donor_review_by_id(db_session, donor.DonorId)
        assert retrieved is not None
        assert retrieved.DonorId == donor.DonorId
        assert retrieved.CompleteName == "Test Donor"

    async def test_find_donor_by_email(self, db_session):
        """Test finding a donor by email."""
        # Create donor review
        await create_donor_review_record(
            session=db_session,
            company_id=1,
            complete_name="Email Test",
            email="findme@example.com"
        )

        # Find by email
        found = await find_donor_review_by_email(db_session, 1, "findme@example.com")
        assert found is not None
        assert found.EMail == "findme@example.com"

    async def test_count_pending_reviews(self, db_session):
        """Test counting pending reviews for a company."""
        # Create a few donor reviews
        await create_donor_review_record(
            session=db_session,
            company_id=1,
            complete_name="Donor 1"
        )
        await create_donor_review_record(
            session=db_session,
            company_id=1,
            complete_name="Donor 2"
        )

        count = await count_pending_reviews_for_company(db_session, 1)
        assert count >= 2

    async def test_delete_donor_review(self, db_session):
        """Test deleting a donor review record."""
        # Create donor review
        donor = await create_donor_review_record(
            session=db_session,
            company_id=1,
            complete_name="To Delete"
        )

        donor_id = donor.DonorId

        # Delete it
        success = await delete_donor_review_record(db_session, donor_id)
        assert success is True

        # Verify it's gone
        retrieved = await get_donor_review_by_id(db_session, donor_id)
        assert retrieved is None

    async def test_bulk_create_donors(self, db_session):
        """Test bulk creating donor review records."""
        donors_data = [
            {"complete_name": "Bulk Donor 1", "email": "bulk1@example.com"},
            {"complete_name": "Bulk Donor 2", "email": "bulk2@example.com"},
            {"complete_name": "Bulk Donor 3", "email": "bulk3@example.com"},
        ]

        success, failed = await bulk_create_donor_reviews(db_session, 1, donors_data)
        assert success == 3
        assert failed == 0

        # Verify they exist
        donors = await get_donors_review_for_company(db_session, 1)
        assert len(donors) >= 3
