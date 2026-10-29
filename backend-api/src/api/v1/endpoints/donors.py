"""
Donors endpoints for managing donor records.

Provides CRUD endpoints for donor management with automatic name parsing.

Endpoints:
    GET /api/v1/donors/me - Get current authenticated user's donor profile
    GET /api/v1/donors - Get all or filtered donors
    GET /api/v1/donors/{donor_id} - Get single donor by ID
    GET /api/v1/donors/search - Search donors by name
    GET /api/v1/donors/by-email/{email} - Find donor by email
    POST /api/v1/donors - Create a new donor
    PUT /api/v1/donors/{donor_id} - Update an existing donor
    DELETE /api/v1/donors/{donor_id} - Delete a donor
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.dependencies import User, get_current_user_required
from src.core.donors_utils import parse_complete_name
from src.core.logging import get_logger
from src.core.stored_procedure_utils import execute_stored_procedure_with_output
from src.database import get_session
from src.database.models.donors import Donors
from src.models.donors import (
    DonorsCreateModel,
    DonorsListResponse,
    DonorsModel,
    DonorsResponse,
    DonorsUpdateModel,
)

router = APIRouter(prefix="/donors", tags=["donors"])
logger = get_logger(__name__, level=settings.LOG_LEVEL)


@router.get(
    "/me",
    response_model=DonorsResponse,
    status_code=200,
    summary="Get current user's donor profile",
    description="Retrieve the donor profile for the authenticated user. Creates a link if it doesn't exist.",
)
async def get_current_user_donor(
    current_user: User = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_session),
) -> DonorsResponse:
    """
    Get the donor profile for the currently authenticated user.
    
    This endpoint:
    1. Extracts the user ID and email from the JWT token
    2. Calls the UIActionCreateDonorUserLink stored procedure to get/create the donor link
    3. Retrieves the full donor record
    4. Returns the donor information
    
    Requires authentication via Bearer token.
    
    Args:
        current_user: Authenticated user from JWT token (injected)
        session: Database session (injected)
        
    Returns:
        DonorsResponse with the donor profile
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 404 if donor not found
        HTTPException: 500 if stored procedure or database error
        
    Example:
        GET /api/v1/donors/me
        Authorization: Bearer <token>
    """
    logger.info(
        f"Retrieving donor profile for authenticated user",
        extra={
            "user_id": current_user.id,
            "email": current_user.email,
        },
    )
    
    try:
        # Call stored procedure to get/create donor-user link
        # UIActionCreateDonorUserLink with DataType = 1
        parameters = {
            "DataType": 1,
            "UserId": current_user.id,
            "FullName": current_user.name or "",
            "NickName": current_user.nick_name or "",
            "FirstName": current_user.first_name or "",
            "LastName": current_user.last_name or "",
            "EMail": current_user.email or "",
            "EMailVerified": 1 if current_user.email_verified else 0,
            "Picture": current_user.picture or "",
            "StatusCode": 2
        }
        
        output_params = {
            "DonorId": "INT",
        }
        
        logger.info("Calling UIActionCreateDonorUserLink stored procedure")
        
        _, outputs = await execute_stored_procedure_with_output(
            session=session,
            procedure_name="UIActionCreateDonorUserLink",
            parameters=parameters,
            output_params=output_params,
            fetch_multiple=False,
        )
        
        donor_id = outputs.get("DonorId")
        
        # If no DonorId returned, user is not yet linked to a donor record
        if not donor_id or donor_id == 0:
            logger.info(f"No donor linked yet for user: {current_user.id}")
            return DonorsResponse(
                item=None,
                user=current_user,
                status="pending",
                message="Your account is being validated by an administrator. Once approved, you will have access to your personalized donation portal."
            )
        
        logger.info(f"Retrieved DonorId: {donor_id} for user: {current_user.id}")
        
        # Get the full donor record
        query = select(Donors).where(Donors.DonorId == donor_id)
        result = await session.execute(query)
        donor = result.scalar_one_or_none()
        
        # If DonorId exists but donor record not found, still return pending
        if not donor:
            logger.warning(f"DonorId {donor_id} returned but donor record not found for user: {current_user.id}")
            return DonorsResponse(
                item=None,
                user=current_user,
                status="pending",
                message="Your account is being validated by an administrator. Once approved, you will have access to your personalized donation portal."
            )
        
        logger.info(f"Successfully retrieved donor profile for user: {current_user.id}")
        
        donor_model = DonorsModel.model_validate(donor)
        return DonorsResponse(item=donor_model, user=current_user, status="success")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving donor profile for user: {str(e)}",
            exc_info=True,
            extra={
                "user_id": current_user.id,
                "email": current_user.email,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving donor profile: {str(e)}",
        )


@router.get(
    "",
    response_model=DonorsListResponse,
    status_code=200,
    summary="Get donors",
    description="Retrieve all donors or filter by various criteria",
)
async def get_donors(
    email: Optional[str] = Query(None, description="Filter by email (partial match)"),
    complete_name: Optional[str] = Query(None, description="Filter by complete name (partial match)"),
    first_name: Optional[str] = Query(None, description="Filter by first name (partial match)"),
    last_name: Optional[str] = Query(None, description="Filter by last name (partial match)"),
    city: Optional[str] = Query(None, description="Filter by city (partial match)"),
    state: Optional[str] = Query(None, description="Filter by state code"),
    status_code: Optional[int] = Query(None, description="Filter by status code"),
    limit: Optional[int] = Query(100, description="Maximum number of results", le=1000),
    offset: Optional[int] = Query(0, description="Number of records to skip"),
    session: AsyncSession = Depends(get_session),
) -> DonorsListResponse:
    """
    Get list of donors with optional filtering and pagination.

    Args:
        email: Optional email filter
        complete_name: Optional complete name filter
        first_name: Optional first name filter
        last_name: Optional last name filter
        city: Optional city filter
        state: Optional state filter
        status_code: Optional status code filter
        limit: Maximum results
        offset: Records to skip
        session: Database session (injected)

    Returns:
        DonorsListResponse with count and list of donors

    Example:
        GET /api/v1/donors
        GET /api/v1/donors?email=john@example.com
        GET /api/v1/donors?last_name=Smith&city=New York
        GET /api/v1/donors?limit=50&offset=0
    """
    logger.info(
        "Retrieving donors",
        extra={
            "email_filter": email,
            "complete_name_filter": complete_name,
            "first_name_filter": first_name,
            "last_name_filter": last_name,
            "limit": limit,
            "offset": offset,
        },
    )

    try:
        query = select(Donors)

        # Apply filters
        if email:
            query = query.where(Donors.EMail.ilike(f"%{email}%"))
        if complete_name:
            query = query.where(Donors.CompleteName.ilike(f"%{complete_name}%"))
        if first_name:
            query = query.where(Donors.FirstName.ilike(f"%{first_name}%"))
        if last_name:
            query = query.where(Donors.LastName.ilike(f"%{last_name}%"))
        if city:
            query = query.where(Donors.City.ilike(f"%{city}%"))
        if state:
            query = query.where(Donors.State == state)
        if status_code is not None:
            query = query.where(Donors.StatusCode == status_code)

        # Order and paginate
        query = query.order_by(Donors.DonorId).limit(limit).offset(offset)

        result = await session.execute(query)
        donors = result.scalars().all()
        logger.info(f"Retrieved {len(donors)} donors")

        # Convert to response models
        donor_models = [DonorsModel.model_validate(donor) for donor in donors]

        return DonorsListResponse(
            count=len(donor_models),
            items=donor_models,
            status="success",
        )

    except Exception as e:
        logger.error(f"Error retrieving donors: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving donors: {str(e)}",
        )


@router.get(
    "/search",
    response_model=DonorsListResponse,
    status_code=200,
    summary="Search donors by name",
    description="Search donors by name (searches CompleteName, FirstName, LastName)",
)
async def search_donors(
    q: str = Query(..., description="Search term", min_length=1),
    limit: Optional[int] = Query(50, description="Maximum number of results", le=1000),
    session: AsyncSession = Depends(get_session),
) -> DonorsListResponse:
    """
    Search donors by name.

    Args:
        q: Search term
        limit: Maximum results
        session: Database session (injected)

    Returns:
        DonorsListResponse with matching donors

    Example:
        GET /api/v1/donors/search?q=John
        GET /api/v1/donors/search?q=Smith&limit=10
    """
    logger.info(f"Searching donors with term: {q}")

    try:
        search_pattern = f"%{q}%"
        query = select(Donors).where(
            or_(
                Donors.CompleteName.ilike(search_pattern),
                Donors.FirstName.ilike(search_pattern),
                Donors.LastName.ilike(search_pattern),
            )
        ).limit(limit)

        result = await session.execute(query)
        donors = result.scalars().all()
        logger.info(f"Found {len(donors)} donors matching '{q}'")

        donor_models = [DonorsModel.model_validate(donor) for donor in donors]

        return DonorsListResponse(
            count=len(donor_models),
            items=donor_models,
            status="success",
        )

    except Exception as e:
        logger.error(f"Error searching donors: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching donors: {str(e)}",
        )


@router.get(
    "/by-email/{email}",
    response_model=DonorsResponse,
    status_code=200,
    summary="Find donor by email",
    description="Find a donor by exact email address",
)
async def get_donor_by_email(
    email: str,
    session: AsyncSession = Depends(get_session),
) -> DonorsResponse:
    """
    Find a donor by email address.

    Args:
        email: Email address
        session: Database session (injected)

    Returns:
        DonorsResponse with the donor

    Raises:
        HTTPException: 404 if donor not found

    Example:
        GET /api/v1/donors/by-email/john@example.com
    """
    logger.info(f"Finding donor by email: {email}")

    try:
        query = select(Donors).where(Donors.EMail.ilike(email))
        result = await session.execute(query)
        donor = result.scalar_one_or_none()

        if not donor:
            logger.warning(f"Donor not found with email: {email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Donor not found with email: {email}",
            )

        donor_model = DonorsModel.model_validate(donor)
        return DonorsResponse(item=donor_model, user=None, status="success")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding donor by email: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error finding donor: {str(e)}",
        )


@router.get(
    "/{donor_id}",
    response_model=DonorsResponse,
    status_code=200,
    summary="Get donor by ID",
    description="Retrieve a single donor by ID",
)
async def get_donor_by_id(
    donor_id: int,
    session: AsyncSession = Depends(get_session),
) -> DonorsResponse:
    """
    Get a single donor by ID.

    Args:
        donor_id: Donor identifier
        session: Database session (injected)

    Returns:
        DonorsResponse with the donor

    Raises:
        HTTPException: 404 if donor not found

    Example:
        GET /api/v1/donors/123
    """
    logger.info(f"Retrieving donor with donor_id={donor_id}")

    try:
        query = select(Donors).where(Donors.DonorId == donor_id)
        result = await session.execute(query)
        donor = result.scalar_one_or_none()

        if not donor:
            logger.warning(f"Donor not found: donor_id={donor_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Donor not found with donor_id={donor_id}",
            )

        donor_model = DonorsModel.model_validate(donor)
        return DonorsResponse(item=donor_model, user=None, status="success")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving donor: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving donor: {str(e)}",
        )


@router.post(
    "",
    response_model=DonorsResponse,
    status_code=201,
    summary="Create a new donor",
    description="Create a new donor record with automatic name parsing",
)
async def create_donor(
    donor_data: DonorsCreateModel,
    session: AsyncSession = Depends(get_session),
) -> DonorsResponse:
    """
    Create a new donor record.

    FirstName, MiddleName, and LastName are automatically derived from CompleteName.

    Args:
        donor_data: Donor data
        session: Database session (injected)

    Returns:
        DonorsResponse with the created donor

    Example:
        POST /api/v1/donors
        {
            "completeName": "John Michael Doe",
            "email": "john@example.com",
            "phoneNumber": "555-1234"
        }
    """
    logger.info(f"Creating donor: {donor_data.CompleteName}")

    try:
        # Parse the complete name
        first_name, middle_name, last_name = parse_complete_name(donor_data.CompleteName)

        # Create new donor
        from datetime import datetime
        new_donor = Donors(
            CompleteName=donor_data.CompleteName,
            FirstName=first_name,
            MiddleName=middle_name,
            LastName=last_name,
            NamePrefix=donor_data.NamePrefix,
            Suffix=donor_data.Suffix,
            CompanyName=donor_data.CompanyName,
            TaxReceiptName=donor_data.TaxReceiptName,
            AddressLine1=donor_data.AddressLine1,
            AddressLine2=donor_data.AddressLine2,
            City=donor_data.City,
            State=donor_data.State,
            PostalCode=donor_data.PostalCode,
            CountryCode=donor_data.CountryCode,
            PhoneNumber=donor_data.PhoneNumber,
            EMail=donor_data.EMail,
            Occupation=donor_data.Occupation,
            Physician=donor_data.Physician,
            IncorrectAddress=donor_data.IncorrectAddress,
            PublishinDonorList=donor_data.PublishinDonorList,
            TaxReceiptRequired=donor_data.TaxReceiptRequired,
            StatusCode=donor_data.StatusCode,
            CreatedBy=donor_data.CreatedBy,
            CreatedDate=datetime.utcnow(),
        )

        session.add(new_donor)
        await session.commit()
        await session.refresh(new_donor)

        donor_model = DonorsModel.model_validate(new_donor)
        logger.info(f"Created donor with donor_id={new_donor.DonorId}")

        return DonorsResponse(item=donor_model, user=None, status="success")

    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating donor: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating donor: {str(e)}",
        )


@router.put(
    "/{donor_id}",
    response_model=DonorsResponse,
    status_code=200,
    summary="Update a donor",
    description="Update an existing donor record with automatic name parsing",
)
async def update_donor(
    donor_id: int,
    donor_data: DonorsUpdateModel,
    session: AsyncSession = Depends(get_session),
) -> DonorsResponse:
    """
    Update an existing donor record.

    If CompleteName is updated, FirstName, MiddleName, and LastName are automatically re-derived.

    Args:
        donor_id: Donor identifier
        donor_data: Updated donor data
        session: Database session (injected)

    Returns:
        DonorsResponse with the updated donor

    Raises:
        HTTPException: 404 if donor not found

    Example:
        PUT /api/v1/donors/123
        {
            "completeName": "John Michael Smith",
            "email": "john.smith@example.com"
        }
    """
    logger.info(f"Updating donor with donor_id={donor_id}")

    try:
        query = select(Donors).where(Donors.DonorId == donor_id)
        result = await session.execute(query)
        donor = result.scalar_one_or_none()

        if not donor:
            logger.warning(f"Donor not found: donor_id={donor_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Donor not found with donor_id={donor_id}",
            )

        # Update fields if provided
        if donor_data.CompleteName is not None:
            donor.CompleteName = donor_data.CompleteName
            # Re-parse the name
            first, middle, last = parse_complete_name(donor_data.CompleteName)
            donor.FirstName = first
            donor.MiddleName = middle
            donor.LastName = last

        if donor_data.NamePrefix is not None:
            donor.NamePrefix = donor_data.NamePrefix
        if donor_data.Suffix is not None:
            donor.Suffix = donor_data.Suffix
        if donor_data.CompanyName is not None:
            donor.CompanyName = donor_data.CompanyName
        if donor_data.TaxReceiptName is not None:
            donor.TaxReceiptName = donor_data.TaxReceiptName
        if donor_data.AddressLine1 is not None:
            donor.AddressLine1 = donor_data.AddressLine1
        if donor_data.AddressLine2 is not None:
            donor.AddressLine2 = donor_data.AddressLine2
        if donor_data.City is not None:
            donor.City = donor_data.City
        if donor_data.State is not None:
            donor.State = donor_data.State
        if donor_data.PostalCode is not None:
            donor.PostalCode = donor_data.PostalCode
        if donor_data.CountryCode is not None:
            donor.CountryCode = donor_data.CountryCode
        if donor_data.PhoneNumber is not None:
            donor.PhoneNumber = donor_data.PhoneNumber
        if donor_data.EMail is not None:
            donor.EMail = donor_data.EMail
        if donor_data.Occupation is not None:
            donor.Occupation = donor_data.Occupation
        if donor_data.Physician is not None:
            donor.Physician = donor_data.Physician
        if donor_data.IncorrectAddress is not None:
            donor.IncorrectAddress = donor_data.IncorrectAddress
        if donor_data.PublishinDonorList is not None:
            donor.PublishinDonorList = donor_data.PublishinDonorList
        if donor_data.TaxReceiptRequired is not None:
            donor.TaxReceiptRequired = donor_data.TaxReceiptRequired
        if donor_data.StatusCode is not None:
            donor.StatusCode = donor_data.StatusCode

        from datetime import datetime
        donor.ModifiedBy = donor_data.ModifiedBy
        donor.ModifiedDate = datetime.utcnow()

        await session.commit()
        await session.refresh(donor)

        donor_model = DonorsModel.model_validate(donor)
        logger.info(f"Updated donor with donor_id={donor_id}")

        return DonorsResponse(item=donor_model, user=None, status="success")

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating donor: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating donor: {str(e)}",
        )


@router.delete(
    "/{donor_id}",
    status_code=204,
    summary="Delete a donor",
    description="Delete a donor record by ID",
)
async def delete_donor(
    donor_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Delete a donor record.

    Args:
        donor_id: Donor identifier
        session: Database session (injected)

    Raises:
        HTTPException: 404 if donor not found

    Example:
        DELETE /api/v1/donors/123
    """
    logger.info(f"Deleting donor with donor_id={donor_id}")

    try:
        query = select(Donors).where(Donors.DonorId == donor_id)
        result = await session.execute(query)
        donor = result.scalar_one_or_none()

        if not donor:
            logger.warning(f"Donor not found: donor_id={donor_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Donor not found with donor_id={donor_id}",
            )

        await session.delete(donor)
        await session.commit()

        logger.info(f"Deleted donor with donor_id={donor_id}")

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting donor: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting donor: {str(e)}",
        )
