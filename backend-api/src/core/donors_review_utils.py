"""
Utility functions for managing donor review records within backend code.

Provides convenient access to donor review operations for internal backend code,
making it easy to create and manage donor records pending review programmatically.
"""

from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.models.donors_review import DonorsReview

logger = get_logger(__name__)


async def create_donor_review_record(
    session: AsyncSession,
    company_id: int,
    complete_name: Optional[str] = None,
    email: Optional[str] = None,
    phone_number: Optional[str] = None,
    address_line1: Optional[str] = None,
    address_line2: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    country_code: Optional[str] = None,
    name_prefix: Optional[str] = None,
) -> Optional[DonorsReview]:
    """
    Create a new donor review record.

    This is a convenience function for internal backend code to easily
    create donor records that need review/approval.

    Args:
        session: Database session
        company_id: Company identifier
        complete_name: Complete name of the donor
        email: Email address
        phone_number: Contact phone number
        address_line1: Primary address line
        address_line2: Secondary address line
        city: City name
        state: State code
        postal_code: Postal/ZIP code
        country_code: Country code
        name_prefix: Name prefix (Mr., Mrs., Dr., etc.)

    Returns:
        Created DonorsReview object if successful, None otherwise

    Example:
        ```python
        from src.core.donors_review_utils import create_donor_review_record
        from src.database import get_session

        async with get_session() as session:
            donor = await create_donor_review_record(
                session=session,
                company_id=1,
                complete_name="John Doe",
                email="john@example.com",
                phone_number="555-1234",
                city="New York",
                state="NY"
            )
            if donor:
                print(f"Created donor review record with ID: {donor.DonorId}")
        ```
    """
    try:
        new_donor = DonorsReview(
            CompanyId=company_id,
            CompleteName=complete_name,
            EMail=email,
            PhoneNumber=phone_number,
            AddressLine1=address_line1,
            AddressLine2=address_line2,
            City=city,
            State=state,
            PostalCode=postal_code,
            CountryCode=country_code,
            NamePrefix=name_prefix,
        )

        session.add(new_donor)
        await session.commit()
        await session.refresh(new_donor)

        logger.info(
            f"Created donor review record with donor_id={new_donor.DonorId} for company_id={company_id}",
            extra={"donor_id": new_donor.DonorId, "company_id": company_id, "complete_name": complete_name}
        )
        return new_donor

    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating donor review record: {e}", exc_info=True)
        return None


async def get_donor_review_by_id(
    session: AsyncSession,
    donor_id: int,
) -> Optional[DonorsReview]:
    """
    Get a donor review record by ID.

    Args:
        session: Database session
        donor_id: Donor identifier

    Returns:
        DonorsReview object if found, None otherwise

    Example:
        ```python
        donor = await get_donor_review_by_id(session, 123)
        if donor:
            print(f"Found donor: {donor.CompleteName}")
        ```
    """
    try:
        query = select(DonorsReview).where(DonorsReview.DonorId == donor_id)
        result = await session.execute(query)
        donor = result.scalar_one_or_none()

        if donor:
            logger.debug(f"Retrieved donor review record for donor_id={donor_id}")
        else:
            logger.warning(f"Donor review record not found for donor_id={donor_id}")

        return donor

    except Exception as e:
        logger.error(f"Error retrieving donor review record: {e}", exc_info=True)
        return None


async def get_donors_review_for_company(
    session: AsyncSession,
    company_id: int,
) -> list[DonorsReview]:
    """
    Get all donor review records for a specific company.

    Args:
        session: Database session
        company_id: Company identifier

    Returns:
        List of DonorsReview objects for the company

    Example:
        ```python
        donors = await get_donors_review_for_company(session, 1)
        print(f"Found {len(donors)} donors waiting for review")
        for donor in donors:
            print(f"- {donor.CompleteName} ({donor.EMail})")
        ```
    """
    try:
        query = select(DonorsReview).where(
            DonorsReview.CompanyId == company_id
        ).order_by(DonorsReview.DonorId)
        
        result = await session.execute(query)
        donors = result.scalars().all()

        logger.debug(f"Retrieved {len(donors)} donor review records for company_id={company_id}")
        return list(donors)

    except Exception as e:
        logger.error(f"Error retrieving donor review records for company: {e}", exc_info=True)
        return []


async def delete_donor_review_record(
    session: AsyncSession,
    donor_id: int,
) -> bool:
    """
    Delete a donor review record by ID.

    Args:
        session: Database session
        donor_id: Donor identifier

    Returns:
        True if deleted successfully, False otherwise

    Example:
        ```python
        success = await delete_donor_review_record(session, 123)
        if success:
            print("Donor review record deleted successfully")
        ```
    """
    try:
        # Check if record exists
        query = select(DonorsReview).where(DonorsReview.DonorId == donor_id)
        result = await session.execute(query)
        donor = result.scalar_one_or_none()

        if not donor:
            logger.warning(f"Cannot delete: donor review record not found for donor_id={donor_id}")
            return False

        # Delete the record
        delete_query = delete(DonorsReview).where(DonorsReview.DonorId == donor_id)
        await session.execute(delete_query)
        await session.commit()

        logger.info(f"Deleted donor review record for donor_id={donor_id}")
        return True

    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting donor review record: {e}", exc_info=True)
        return False


async def find_donor_review_by_email(
    session: AsyncSession,
    company_id: int,
    email: str,
) -> Optional[DonorsReview]:
    """
    Find a donor review record by email for a specific company.

    Args:
        session: Database session
        company_id: Company identifier
        email: Email address to search for

    Returns:
        First matching DonorsReview object if found, None otherwise

    Example:
        ```python
        donor = await find_donor_review_by_email(session, 1, "john@example.com")
        if donor:
            print(f"Found existing review for: {donor.CompleteName}")
        ```
    """
    try:
        query = select(DonorsReview).where(
            DonorsReview.CompanyId == company_id,
            DonorsReview.EMail.ilike(email)
        )
        result = await session.execute(query)
        donor = result.scalar_one_or_none()

        if donor:
            logger.debug(f"Found donor review record by email: {email}")
        else:
            logger.debug(f"No donor review record found for email: {email}")

        return donor

    except Exception as e:
        logger.error(f"Error finding donor review record by email: {e}", exc_info=True)
        return None


async def count_pending_reviews_for_company(
    session: AsyncSession,
    company_id: int,
) -> int:
    """
    Count the number of pending donor review records for a company.

    Args:
        session: Database session
        company_id: Company identifier

    Returns:
        Number of pending donor review records

    Example:
        ```python
        count = await count_pending_reviews_for_company(session, 1)
        print(f"There are {count} donors waiting for review")
        ```
    """
    try:
        query = select(DonorsReview).where(DonorsReview.CompanyId == company_id)
        result = await session.execute(query)
        donors = result.scalars().all()
        count = len(donors)

        logger.debug(f"Company {company_id} has {count} pending donor reviews")
        return count

    except Exception as e:
        logger.error(f"Error counting pending reviews: {e}", exc_info=True)
        return 0


def validate_donor_data(
    complete_name: Optional[str] = None,
    email: Optional[str] = None,
    phone_number: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """
    Validate donor data before creating a review record.

    Args:
        complete_name: Complete name of the donor
        email: Email address
        phone_number: Phone number

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        ```python
        is_valid, error = validate_donor_data(
            complete_name="John Doe",
            email="john@example.com"
        )
        if not is_valid:
            print(f"Validation error: {error}")
        ```
    """
    # At least one of name, email, or phone should be provided
    if not any([complete_name, email, phone_number]):
        return False, "At least one of complete_name, email, or phone_number must be provided"

    # Validate email format if provided
    if email and "@" not in email:
        return False, "Invalid email format"

    # Validate name length if provided
    if complete_name and len(complete_name) > 240:
        return False, "Complete name exceeds maximum length of 240 characters"

    # Validate email length if provided
    if email and len(email) > 512:
        return False, "Email exceeds maximum length of 512 characters"

    # Validate phone length if provided
    if phone_number and len(phone_number) > 50:
        return False, "Phone number exceeds maximum length of 50 characters"

    return True, None


async def bulk_create_donor_reviews(
    session: AsyncSession,
    company_id: int,
    donors_data: list[dict],
) -> tuple[int, int]:
    """
    Create multiple donor review records at once.

    Args:
        session: Database session
        company_id: Company identifier
        donors_data: List of dictionaries with donor data

    Returns:
        Tuple of (success_count, failure_count)

    Example:
        ```python
        donors = [
            {"complete_name": "John Doe", "email": "john@example.com"},
            {"complete_name": "Jane Smith", "email": "jane@example.com"},
        ]
        success, failed = await bulk_create_donor_reviews(session, 1, donors)
        print(f"Created {success} records, {failed} failed")
        ```
    """
    success_count = 0
    failure_count = 0

    for donor_data in donors_data:
        try:
            new_donor = DonorsReview(
                CompanyId=company_id,
                CompleteName=donor_data.get("complete_name"),
                EMail=donor_data.get("email"),
                PhoneNumber=donor_data.get("phone_number"),
                AddressLine1=donor_data.get("address_line1"),
                AddressLine2=donor_data.get("address_line2"),
                City=donor_data.get("city"),
                State=donor_data.get("state"),
                PostalCode=donor_data.get("postal_code"),
                CountryCode=donor_data.get("country_code"),
                NamePrefix=donor_data.get("name_prefix"),
            )

            session.add(new_donor)
            success_count += 1

        except Exception as e:
            logger.error(f"Error creating donor review record in bulk: {e}", exc_info=True)
            failure_count += 1

    try:
        await session.commit()
        logger.info(f"Bulk created {success_count} donor review records for company_id={company_id}")
    except Exception as e:
        await session.rollback()
        logger.error(f"Error committing bulk donor reviews: {e}", exc_info=True)
        return 0, len(donors_data)

    return success_count, failure_count
