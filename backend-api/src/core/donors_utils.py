"""
Utility functions for managing donor records within backend code.

Provides convenient access to donor operations and name parsing functionality
for internal backend code.
"""

from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.models.donors import Donors
from src.database.models.donor_user_links import DonorUserLinks

logger = get_logger(__name__)


async def get_donor_id_by_user_id(
    session: AsyncSession,
    user_id: str,
    active_only: bool = True
) -> Optional[int]:
    """
    Get donor ID for a given user ID using the DonorUserLinks table.
    
    This utility function retrieves the donor ID associated with a user ID
    by querying the DonorUserLinks relationship table.
    
    Args:
        session: Database session
        user_id: The user ID to look up
        active_only: If True, only return links with StatusCode = 1 (active)
                    If False, return any link regardless of status
    
    Returns:
        The donor ID if a link exists, None otherwise
    
    Examples:
        >>> donor_id = await get_donor_id_by_user_id(session, "auth0|123456")
        >>> if donor_id:
        ...     # Use donor_id for queries
        ...     donor = await get_donor_by_id(session, donor_id)
    """
    query = select(DonorUserLinks.DonorId).where(
        DonorUserLinks.UserId == user_id
    )
    
    # Filter by active status if requested
    if active_only:
        query = query.where(DonorUserLinks.StatusCode == 2)
    
    result = await session.execute(query)
    donor_id = result.scalar_one_or_none()
    
    if donor_id:
        logger.debug(f"Found donor ID {donor_id} for user ID: {user_id}")
    else:
        logger.debug(f"No donor link found for user ID: {user_id}")
    
    return donor_id


async def get_donor_by_user_id(
    session: AsyncSession,
    user_id: str,
    active_only: bool = True
) -> Optional[Donors]:
    """
    Get full donor record for a given user ID.
    
    This is a convenience function that combines get_donor_id_by_user_id
    with fetching the full donor record.
    
    Args:
        session: Database session
        user_id: The user ID to look up
        active_only: If True, only return links with StatusCode = 1 (active)
    
    Returns:
        The Donors record if found, None otherwise
    
    Examples:
        >>> donor = await get_donor_by_user_id(session, "auth0|123456")
        >>> if donor:
        ...     print(f"Donor: {donor.CompleteName}")
    """
    donor_id = await get_donor_id_by_user_id(session, user_id, active_only)
    
    if not donor_id:
        return None
    
    result = await session.execute(
        select(Donors).where(Donors.DonorId == donor_id)
    )
    return result.scalar_one_or_none()


def parse_complete_name(complete_name: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse complete name into first, middle, and last name components.

    Args:
        complete_name: Full name to parse

    Returns:
        Tuple of (first_name, middle_name, last_name)

    Examples:
        >>> parse_complete_name("John Doe")
        ('John', None, 'Doe')
        
        >>> parse_complete_name("John Michael Doe")
        ('John', 'Michael', 'Doe')
        
        >>> parse_complete_name("John")
        ('John', None, None)
    """
    if not complete_name:
        return None, None, None

    # Remove extra whitespace and split
    parts = complete_name.strip().split()

    if len(parts) == 0:
        return None, None, None
    elif len(parts) == 1:
        # Only one name - treat as first name
        return parts[0], None, None
    elif len(parts) == 2:
        # Two names - first and last
        return parts[0], None, parts[1]
    else:
        # Three or more names - first, middle(s), last
        first_name = parts[0]
        last_name = parts[-1]
        middle_name = " ".join(parts[1:-1])
        return first_name, middle_name, last_name


async def create_donor(
    session: AsyncSession,
    complete_name: str,
    email: Optional[str] = None,
    phone_number: Optional[str] = None,
    address_line1: Optional[str] = None,
    address_line2: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    country_code: Optional[str] = None,
    name_prefix: Optional[str] = None,
    suffix: Optional[str] = None,
    company_name: Optional[str] = None,
    tax_receipt_name: Optional[str] = None,
    occupation: Optional[str] = None,
    physician: bool = False,
    incorrect_address: bool = False,
    publish_in_donor_list: bool = True,
    tax_receipt_required: bool = True,
    status_code: Optional[int] = None,
    created_by: Optional[int] = None,
) -> Optional[Donors]:
    """
    Create a new donor record with automatic name parsing.

    FirstName, MiddleName, and LastName are automatically derived from CompleteName.

    Args:
        session: Database session
        complete_name: Complete name (required)
        email: Email address
        phone_number: Phone number
        address_line1: Address line 1
        address_line2: Address line 2
        city: City
        state: State code
        postal_code: Postal code
        country_code: Country code
        name_prefix: Name prefix
        suffix: Name suffix
        company_name: Company name
        tax_receipt_name: Tax receipt name
        occupation: Occupation
        physician: Is physician flag
        incorrect_address: Incorrect address flag
        publish_in_donor_list: Publish in donor list flag
        tax_receipt_required: Tax receipt required flag
        status_code: Status code
        created_by: User ID creating the record

    Returns:
        Created Donors object if successful, None otherwise

    Example:
        ```python
        from src.core.donors_utils import create_donor
        from src.database import get_session

        async with get_session() as session:
            donor = await create_donor(
                session=session,
                complete_name="John Michael Doe",
                email="john@example.com",
                phone_number="555-1234",
                city="New York",
                state="NY"
            )
            if donor:
                print(f"Created donor: {donor.FirstName} {donor.LastName}")
        ```
    """
    try:
        # Parse the complete name
        first_name, middle_name, last_name = parse_complete_name(complete_name)

        # Create new donor
        new_donor = Donors(
            CompleteName=complete_name,
            FirstName=first_name,
            MiddleName=middle_name,
            LastName=last_name,
            NamePrefix=name_prefix,
            Suffix=suffix,
            CompanyName=company_name,
            TaxReceiptName=tax_receipt_name,
            AddressLine1=address_line1,
            AddressLine2=address_line2,
            City=city,
            State=state,
            PostalCode=postal_code,
            CountryCode=country_code,
            PhoneNumber=phone_number,
            EMail=email,
            Occupation=occupation,
            Physician=physician,
            IncorrectAddress=incorrect_address,
            PublishinDonorList=publish_in_donor_list,
            TaxReceiptRequired=tax_receipt_required,
            StatusCode=status_code,
            CreatedBy=created_by,
            CreatedDate=datetime.utcnow(),
        )

        session.add(new_donor)
        await session.commit()
        await session.refresh(new_donor)

        logger.info(
            f"Created donor with donor_id={new_donor.DonorId}",
            extra={
                "donor_id": new_donor.DonorId,
                "complete_name": complete_name,
                "email": email
            }
        )
        return new_donor

    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating donor: {e}", exc_info=True)
        return None


async def update_donor(
    session: AsyncSession,
    donor_id: int,
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
    suffix: Optional[str] = None,
    company_name: Optional[str] = None,
    tax_receipt_name: Optional[str] = None,
    occupation: Optional[str] = None,
    physician: Optional[bool] = None,
    incorrect_address: Optional[bool] = None,
    publish_in_donor_list: Optional[bool] = None,
    tax_receipt_required: Optional[bool] = None,
    status_code: Optional[int] = None,
    modified_by: Optional[int] = None,
) -> Optional[Donors]:
    """
    Update an existing donor record with automatic name parsing.

    If CompleteName is updated, FirstName, MiddleName, and LastName are automatically re-derived.

    Args:
        session: Database session
        donor_id: Donor identifier
        complete_name: Complete name (triggers name re-parsing)
        ... (other optional fields)

    Returns:
        Updated Donors object if successful, None otherwise

    Example:
        ```python
        donor = await update_donor(
            session=session,
            donor_id=123,
            complete_name="John Michael Smith",  # Name parsing happens automatically
            email="john.smith@example.com",
            modified_by=1
        )
        ```
    """
    try:
        # Get existing donor
        query = select(Donors).where(Donors.DonorId == donor_id)
        result = await session.execute(query)
        donor = result.scalar_one_or_none()

        if not donor:
            logger.warning(f"Donor not found: donor_id={donor_id}")
            return None

        # Update fields if provided
        if complete_name is not None:
            donor.CompleteName = complete_name
            # Re-parse the name
            first, middle, last = parse_complete_name(complete_name)
            donor.FirstName = first
            donor.MiddleName = middle
            donor.LastName = last

        if name_prefix is not None:
            donor.NamePrefix = name_prefix
        if suffix is not None:
            donor.Suffix = suffix
        if company_name is not None:
            donor.CompanyName = company_name
        if tax_receipt_name is not None:
            donor.TaxReceiptName = tax_receipt_name
        if address_line1 is not None:
            donor.AddressLine1 = address_line1
        if address_line2 is not None:
            donor.AddressLine2 = address_line2
        if city is not None:
            donor.City = city
        if state is not None:
            donor.State = state
        if postal_code is not None:
            donor.PostalCode = postal_code
        if country_code is not None:
            donor.CountryCode = country_code
        if phone_number is not None:
            donor.PhoneNumber = phone_number
        if email is not None:
            donor.EMail = email
        if occupation is not None:
            donor.Occupation = occupation
        if physician is not None:
            donor.Physician = physician
        if incorrect_address is not None:
            donor.IncorrectAddress = incorrect_address
        if publish_in_donor_list is not None:
            donor.PublishinDonorList = publish_in_donor_list
        if tax_receipt_required is not None:
            donor.TaxReceiptRequired = tax_receipt_required
        if status_code is not None:
            donor.StatusCode = status_code

        donor.ModifiedBy = modified_by
        donor.ModifiedDate = datetime.utcnow()

        await session.commit()
        await session.refresh(donor)

        logger.info(f"Updated donor with donor_id={donor_id}")
        return donor

    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating donor: {e}", exc_info=True)
        return None


async def get_donor_by_id(
    session: AsyncSession,
    donor_id: int,
) -> Optional[Donors]:
    """
    Get a donor by ID.

    Args:
        session: Database session
        donor_id: Donor identifier

    Returns:
        Donors object if found, None otherwise
    """
    try:
        query = select(Donors).where(Donors.DonorId == donor_id)
        result = await session.execute(query)
        donor = result.scalar_one_or_none()

        if donor:
            logger.debug(f"Retrieved donor with donor_id={donor_id}")
        else:
            logger.warning(f"Donor not found: donor_id={donor_id}")

        return donor

    except Exception as e:
        logger.error(f"Error retrieving donor: {e}", exc_info=True)
        return None


async def find_donor_by_email(
    session: AsyncSession,
    email: str,
) -> Optional[Donors]:
    """
    Find a donor by email address.

    Args:
        session: Database session
        email: Email address to search for

    Returns:
        First matching Donors object if found, None otherwise
    """
    try:
        query = select(Donors).where(Donors.EMail.ilike(email))
        result = await session.execute(query)
        donor = result.scalar_one_or_none()

        if donor:
            logger.debug(f"Found donor by email: {email}")
        else:
            logger.debug(f"No donor found for email: {email}")

        return donor

    except Exception as e:
        logger.error(f"Error finding donor by email: {e}", exc_info=True)
        return None


async def search_donors_by_name(
    session: AsyncSession,
    search_term: str,
    limit: int = 50,
) -> list[Donors]:
    """
    Search donors by name (searches CompleteName, FirstName, LastName).

    Args:
        session: Database session
        search_term: Search term
        limit: Maximum number of results

    Returns:
        List of matching Donors objects
    """
    try:
        search_pattern = f"%{search_term}%"
        query = select(Donors).where(
            or_(
                Donors.CompleteName.ilike(search_pattern),
                Donors.FirstName.ilike(search_pattern),
                Donors.LastName.ilike(search_pattern),
            )
        ).limit(limit)

        result = await session.execute(query)
        donors = result.scalars().all()

        logger.debug(f"Found {len(donors)} donors matching '{search_term}'")
        return list(donors)

    except Exception as e:
        logger.error(f"Error searching donors: {e}", exc_info=True)
        return []


async def get_all_donors(
    session: AsyncSession,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[Donors]:
    """
    Get all donors with optional pagination.

    Args:
        session: Database session
        limit: Maximum number of results
        offset: Number of records to skip

    Returns:
        List of Donors objects
    """
    try:
        query = select(Donors).order_by(Donors.DonorId)

        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        result = await session.execute(query)
        donors = result.scalars().all()

        logger.debug(f"Retrieved {len(donors)} donors")
        return list(donors)

    except Exception as e:
        logger.error(f"Error retrieving donors: {e}", exc_info=True)
        return []


async def delete_donor(
    session: AsyncSession,
    donor_id: int,
) -> bool:
    """
    Delete a donor by ID.

    Args:
        session: Database session
        donor_id: Donor identifier

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        donor = await get_donor_by_id(session, donor_id)
        if not donor:
            return False

        await session.delete(donor)
        await session.commit()

        logger.info(f"Deleted donor with donor_id={donor_id}")
        return True

    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting donor: {e}", exc_info=True)
        return False
