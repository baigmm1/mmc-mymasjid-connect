"""
Pledges endpoints for recording and managing donor pledges.

Provides CRUD endpoints for pledge management.

Endpoints:
    GET  /api/v1/pledges                    - List all pledges (with optional filters)
    GET  /api/v1/pledges/{pledge_id}        - Get a single pledge by ID
    POST /api/v1/pledges                    - Create a new pledge
    PUT  /api/v1/pledges/{pledge_id}        - Update an existing pledge
    DELETE /api/v1/pledges/{pledge_id}      - Delete a pledge
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.logging import get_logger
from src.database import get_session
from src.database.models.pledges import Pledges
from src.models.pledges import (
    PledgeCreateModel,
    PledgeListResponse,
    PledgeModel,
    PledgeSingleResponse,
    PledgeUpdateModel,
)
from src.core.dependencies import User, get_current_user_optional, get_current_user_required
from src.core.donors_utils import find_donor_by_email, get_donor_by_user_id
from src.core.cache_manager import get_company_from_cache, get_donation_type_from_cache

router = APIRouter(prefix="/pledges", tags=["pledges"])
logger = get_logger(__name__, level=settings.LOG_LEVEL)


# ---------------------------------------------------------------------------
# GET /pledges
# ---------------------------------------------------------------------------

@router.get(
    "/{company_id}",
    response_model=PledgeListResponse,
    status_code=status.HTTP_200_OK,
    summary="List pledges",
    description="Retrieve all pledges with optional filters by donor, status, or date range.",
)
async def list_pledges(
    company_id: int,
    donor_id: Optional[int] = Query(None, description="Filter by donor ID"),
    #review_donor_id: Optional[int] = Query(None, description="Filter by review donor ID"),
    status_code: Optional[int] = Query(None, description="Filter by status code"),
    pledge_donation_type: Optional[int] = Query(None, description="Filter by donation type ID"),
    date_from: Optional[datetime] = Query(None, description="Filter pledges on or after this date"),
    date_to: Optional[datetime] = Query(None, description="Filter pledges on or before this date"),
    current_user: User = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_session),
) -> PledgeListResponse:
    """
    List pledges with optional filtering.

    Args:
        donor_id: Optional donor ID filter
        review_donor_id: Optional review donor ID filter
        status_code: Optional status code filter
        pledge_donation_type: Optional donation type filter
        date_from: Optional start date filter on DatePledged
        date_to: Optional end date filter on DatePledged
        session: Database session (injected)

    Returns:
        PledgeListResponse with count and list of pledges

    Example:
        GET /api/v1/pledges
        GET /api/v1/pledges?donor_id=10001&status_code=1
        GET /api/v1/pledges?date_from=2025-01-01&date_to=2025-12-31
    """
    logger.info(
        "Retrieving pledges",
        extra={
            "company_id_filter": company_id,
            "donor_id_filter": donor_id,
            "status_code_filter": status_code,
        },
    )

    try:
        donor = await get_donor_by_user_id(session, current_user.id, active_only=True)

        query = select(Pledges).where(Pledges.CompanyId == company_id)

        if donor_id is not None:
            query = query.where(Pledges.DonorId == donor_id)
        else:
            # If no donor_id filter, only show pledges for the current logged in donor
            query = query.where(Pledges.DonorId == donor.DonorId) # type: ignore

        # if review_donor_id is not None:
        #     query = query.where(Pledges.ReviewDonorId == review_donor_id)
        if status_code is not None:
            query = query.where(Pledges.StatusCode == status_code)
        if pledge_donation_type is not None:
            query = query.where(Pledges.PledgeDonationType == pledge_donation_type)
        if date_from is not None:
            query = query.where(Pledges.DatePledged >= date_from)
        if date_to is not None:
            query = query.where(Pledges.DatePledged <= date_to)

        query = query.order_by(Pledges.DatePledged.desc())

        result = await session.execute(query)
        pledges = result.scalars().all()
        logger.info(f"Retrieved {len(pledges)} pledge records")
        # get donation type descriptions for any pledges that have a donation type
        pledge_items = []
        for pledge in pledges:
            pledge_data = PledgeModel.model_validate(pledge)
            donation_type = await get_donation_type_from_cache(pledge.CompanyId, pledge.PledgeDonationType, session) if pledge.PledgeDonationType else None
            if donation_type:                
                pledge_data.PledgeDonationTypeDescription = donation_type.DetailedTextHeader
            pledge_items.append(pledge_data)

        return PledgeListResponse(count=len(pledge_items), items=pledge_items, status="success")

    except Exception as e:
        logger.error(f"Error retrieving pledges: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving pledges: {str(e)}",
        )


# ---------------------------------------------------------------------------
# GET /pledges/{pledge_id}
# ---------------------------------------------------------------------------

@router.get(
    "/{company_id}/{pledge_id}",
    response_model=PledgeSingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a pledge by ID",
    description="Retrieve a single pledge record by its primary key.",
)
async def get_pledge(
    company_id: int,
    pledge_id: int,
    current_user: User = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_session),
) -> PledgeSingleResponse:
    """
    Get a single pledge by its PledgeRecordID.

    Args:
        company_id: Company ID to filter
        pledge_id: PledgeRecordID to look up
        current_user: The currently authenticated user (injected)
        session: Database session (injected)

    Returns:
        PledgeSingleResponse with the pledge data

    Raises:
        HTTPException 404: If the pledge is not found
        HTTPException 500: On database error
    """
    logger.info(f"Retrieving pledge with ID {pledge_id}")

    try:
        result = await session.execute(
            select(Pledges).where(Pledges.PledgeRecordID == pledge_id, Pledges.CompanyId == company_id)
        )
        pledge = result.scalar_one_or_none()

        if pledge is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pledge with ID {pledge_id} not found",
            )

        return PledgeSingleResponse(
            item=PledgeModel.model_validate(pledge),
            status="success",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving pledge {pledge_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving pledge: {str(e)}",
        )


# ---------------------------------------------------------------------------
# POST /pledges
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=PledgeSingleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new pledge",
    description="Record a new donor pledge.",
)
async def create_pledge(
    payload: PledgeCreateModel,
    current_user: User = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> PledgeSingleResponse:
    """
    Create a new pledge record.

    Args:
        payload: Pledge data from request body
        session: Database session (injected)

    Returns:
        PledgeSingleResponse with the newly created pledge

    Raises:
        HTTPException 400: On validation error
        HTTPException 500: On database error

    Example:
        POST /api/v1/pledges
        {
            "pledgeBy": "John Doe",
            "pledgeEmail": "john@example.com",
            "amountPledged": 500.00,
            "datePledged": "2025-02-24T00:00:00",
            "pledgeDonationType": 1,
            "statusCode": 1
        }
    """
    logger.info(
        "Creating new pledge",
        extra={"pledge_by": payload.PledgeBy, "amount": float(payload.AmountPledged or 0)},
    )

    try:
        now = datetime.utcnow()
        current_logged_donor = None
        if current_user:
            current_logged_donor = await get_donor_by_user_id(session, current_user.id, active_only=True)

        # 1. Validate transaction data
        if not payload.CompanyId:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CompanyId is required"
            )
        
        company = await get_company_from_cache(payload.CompanyId, session)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ID {payload.CompanyId} not found"
            )  
        
        if payload.DonorId is None:
            # check if we have a donor id for the email
            if payload.PledgeEmail:
                donor_record = await find_donor_by_email(session, payload.PledgeEmail)
                if donor_record:                    
                    payload.DonorId = donor_record.DonorId
                    logger.info(f"Found existing donor with ID {payload.DonorId} for email {payload.PledgeEmail}")

        pledge = Pledges(
            CompanyId=payload.CompanyId,
            DonorId=payload.DonorId,
            ReviewDonorId=payload.ReviewDonorId,
            PledgeBy=payload.PledgeBy,
            PledgeEmail=payload.PledgeEmail,
            PledgePhoneNumber=payload.PledgePhoneNumber,
            PledgeDonationType=payload.PledgeDonationType,
            AmountPledged=payload.AmountPledged,
            DatePledged=payload.DatePledged,
            DateConfirmed=payload.DateConfirmed,
            StatusCode=payload.StatusCode,
            CreatedBy=current_logged_donor.DonorId if current_logged_donor else payload.CreatedBy,
            CreatedDate=now,
            ModifiedBy=current_logged_donor.DonorId if current_logged_donor else payload.CreatedBy,
            ModifiedDate=now,
        )

        session.add(pledge)
        await session.commit()
        await session.refresh(pledge)

        logger.info(f"Created pledge with ID {pledge.PledgeRecordID}")

        return PledgeSingleResponse(
            item=PledgeModel.model_validate(pledge),
            status="created",
        )

    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating pledge: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating pledge: {str(e)}",
        )


# ---------------------------------------------------------------------------
# PUT /pledges/{pledge_id}
# ---------------------------------------------------------------------------

@router.put(
    "/{company_id}/{pledge_id}",
    response_model=PledgeSingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a pledge",
    description="Update an existing pledge record. Only supplied fields are updated.",
)
async def update_pledge(
    company_id: int,
    pledge_id: int,
    payload: PledgeUpdateModel,
    current_user: User = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session),
) -> PledgeSingleResponse:
    """
    Update an existing pledge by its PledgeRecordID.

    Only the fields provided in the request body are updated (partial update).

    Args:
        company_id: Company ID to filter
        pledge_id: PledgeRecordID to update
        payload: Fields to update
        session: Database session (injected)

    Returns:
        PledgeSingleResponse with the updated pledge

    Raises:
        HTTPException 404: If pledge is not found
        HTTPException 500: On database error
    """
    logger.info(f"Updating pledge with ID {pledge_id}")

    try:
        current_logged_donor = None
        if current_user:
            current_logged_donor = await get_donor_by_user_id(session, current_user.id, active_only=True)

        result = await session.execute(
            select(Pledges).where(Pledges.PledgeRecordID == pledge_id, Pledges.CompanyId == company_id)
        )
        pledge = result.scalar_one_or_none()

        if pledge is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pledge with ID {pledge_id} not found",
            )

        # Apply only the fields that were explicitly provided
        update_data = payload.model_dump(exclude_unset=True, by_alias=False)
        for field, value in update_data.items():
            setattr(pledge, field, value)

        # Always update ModifiedDate
        pledge.ModifiedDate = datetime.utcnow()
        pledge.ModifiedBy = current_logged_donor.DonorId if current_logged_donor else pledge.ModifiedBy

        await session.commit()
        await session.refresh(pledge)

        logger.info(f"Updated pledge with ID {pledge_id}")

        return PledgeSingleResponse(
            item=PledgeModel.model_validate(pledge),
            status="updated",
        )

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error updating pledge {pledge_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating pledge: {str(e)}",
        )


# ---------------------------------------------------------------------------
# DELETE /pledges/{pledge_id}
# ---------------------------------------------------------------------------

@router.delete(
    "/{company_id}/{pledge_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a pledge",
    description="Permanently remove a pledge record by ID.",
)
async def delete_pledge(
    company_id: int,
    pledge_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Delete a pledge by its PledgeRecordID.

    Args:
        company_id: Company ID to filter
        pledge_id: PledgeRecordID to delete
        session: Database session (injected)

    Raises:
        HTTPException 404: If pledge is not found
        HTTPException 500: On database error
    """
    logger.info(f"Deleting pledge with ID {pledge_id}")

    try:
        result = await session.execute(
            select(Pledges).where(Pledges.PledgeRecordID == pledge_id, Pledges.CompanyId == company_id)
        )
        pledge = result.scalar_one_or_none()

        if pledge is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pledge with ID {pledge_id} not found",
            )

        await session.delete(pledge)
        await session.commit()

        logger.info(f"Deleted pledge with ID {pledge_id}")

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting pledge {pledge_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting pledge: {str(e)}",
        )
