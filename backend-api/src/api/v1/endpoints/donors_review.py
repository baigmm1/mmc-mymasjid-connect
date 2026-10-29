"""
DonorsReview endpoints for managing donor records pending review.

Provides endpoints for retrieving and creating donor review records.

Endpoints:
    GET /api/v1/donors-review - Get all or filtered donor review records
    GET /api/v1/donors-review/{donor_id} - Get single donor review record by ID
    GET /api/v1/donors-review/by-company/{company_id} - Get all donor reviews for a company
    POST /api/v1/donors-review - Create a new donor review record
    DELETE /api/v1/donors-review/{donor_id} - Delete a donor review record
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.logging import get_logger
from src.database import get_session
from src.database.models.donors_review import DonorsReview
from src.models.donors_review import (
    DonorsReviewCreateModel,
    DonorsReviewListResponse,
    DonorsReviewModel,
    DonorsReviewResponse,
)

router = APIRouter(prefix="/donors-review", tags=["donors-review"])
logger = get_logger(__name__, level=settings.LOG_LEVEL)


@router.get(
    "",
    response_model=DonorsReviewListResponse,
    status_code=200,
    summary="Get donor review records",
    description="Retrieve all donor review records or filter by various criteria",
)
async def get_donors_review(
    company_id: Optional[int] = Query(None, description="Filter by company ID"),
    email: Optional[str] = Query(None, description="Filter by email (partial match)"),
    complete_name: Optional[str] = Query(None, description="Filter by complete name (partial match)"),
    city: Optional[str] = Query(None, description="Filter by city (partial match)"),
    state: Optional[str] = Query(None, description="Filter by state code"),
    session: AsyncSession = Depends(get_session),
) -> DonorsReviewListResponse:
    """
    Get list of donor review records with optional filtering.

    Args:
        company_id: Optional company ID filter
        email: Optional email filter (case-insensitive partial match)
        complete_name: Optional name filter (case-insensitive partial match)
        city: Optional city filter (case-insensitive partial match)
        state: Optional state code filter
        session: Database session (injected)

    Returns:
        DonorsReviewListResponse with count and list of donor review records

    Example:
        GET /api/v1/donors-review
        GET /api/v1/donors-review?company_id=1
        GET /api/v1/donors-review?email=john@example.com
        GET /api/v1/donors-review?company_id=1&city=New York
    """
    logger.info(
        "Retrieving donor review records",
        extra={
            "company_id_filter": company_id,
            "email_filter": email,
            "complete_name_filter": complete_name,
            "city_filter": city,
            "state_filter": state,
        },
    )

    try:
        query = select(DonorsReview)

        if company_id is not None:
            query = query.where(DonorsReview.CompanyId == company_id)
            logger.debug(f"Applied company_id filter: {company_id}")
        if email:
            query = query.where(DonorsReview.EMail.ilike(f"%{email}%"))
            logger.debug(f"Applied email filter: {email}")
        if complete_name:
            query = query.where(DonorsReview.CompleteName.ilike(f"%{complete_name}%"))
            logger.debug(f"Applied complete_name filter: {complete_name}")
        if city:
            query = query.where(DonorsReview.City.ilike(f"%{city}%"))
            logger.debug(f"Applied city filter: {city}")
        if state:
            query = query.where(DonorsReview.State == state)
            logger.debug(f"Applied state filter: {state}")

        # Order by DonorId
        query = query.order_by(DonorsReview.DonorId)

        result = await session.execute(query)
        donors = result.scalars().all()
        logger.info(f"Retrieved {len(donors)} donor review records")

        # Convert to response models
        donor_models = [DonorsReviewModel.model_validate(donor) for donor in donors]

        return DonorsReviewListResponse(
            count=len(donor_models),
            items=donor_models,
            status="success",
        )

    except Exception as e:
        logger.error(f"Error retrieving donor review records: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving donor review records: {str(e)}",
        )


@router.get(
    "/{donor_id}",
    response_model=DonorsReviewResponse,
    status_code=200,
    summary="Get donor review record by ID",
    description="Retrieve a single donor review record by donor ID",
)
async def get_donor_review_by_id(
    donor_id: int,
    session: AsyncSession = Depends(get_session),
) -> DonorsReviewResponse:
    """
    Get a single donor review record by ID.

    Args:
        donor_id: Donor identifier
        session: Database session (injected)

    Returns:
        DonorsReviewResponse with the donor review record

    Raises:
        HTTPException: 404 if donor review record not found

    Example:
        GET /api/v1/donors-review/1
    """
    logger.info(f"Retrieving donor review record for donor_id={donor_id}")

    try:
        query = select(DonorsReview).where(DonorsReview.DonorId == donor_id)
        result = await session.execute(query)
        donor = result.scalar_one_or_none()

        if not donor:
            logger.warning(f"Donor review record not found: donor_id={donor_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Donor review record not found for donor_id={donor_id}",
            )

        donor_model = DonorsReviewModel.model_validate(donor)

        logger.info(f"Successfully retrieved donor review record for donor_id={donor_id}")
        return DonorsReviewResponse(
            item=donor_model,
            status="success",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving donor review record for donor_id={donor_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving donor review record: {str(e)}",
        )


@router.get(
    "/by-company/{company_id}",
    response_model=DonorsReviewListResponse,
    status_code=200,
    summary="Get donor review records by company",
    description="Retrieve all donor review records for a specific company",
)
async def get_donors_review_by_company(
    company_id: int,
    session: AsyncSession = Depends(get_session),
) -> DonorsReviewListResponse:
    """
    Get all donor review records for a specific company.

    Args:
        company_id: Company identifier
        session: Database session (injected)

    Returns:
        DonorsReviewListResponse with count and list of donor review records

    Example:
        GET /api/v1/donors-review/by-company/1
    """
    logger.info(f"Retrieving all donor review records for company_id={company_id}")

    try:
        query = select(DonorsReview).where(DonorsReview.CompanyId == company_id).order_by(DonorsReview.DonorId)
        result = await session.execute(query)
        donors = result.scalars().all()

        logger.info(f"Retrieved {len(donors)} donor review records for company_id={company_id}")

        # Convert to response models
        donor_models = [DonorsReviewModel.model_validate(donor) for donor in donors]

        return DonorsReviewListResponse(
            count=len(donor_models),
            items=donor_models,
            status="success",
        )

    except Exception as e:
        logger.error(
            f"Error retrieving donor review records for company_id={company_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving donor review records: {str(e)}",
        )


@router.post(
    "",
    response_model=DonorsReviewResponse,
    status_code=201,
    summary="Create a new donor review record",
    description="Add a new donor record for review",
)
async def create_donor_review(
    donor_data: DonorsReviewCreateModel,
    session: AsyncSession = Depends(get_session),
) -> DonorsReviewResponse:
    """
    Create a new donor review record.

    Args:
        donor_data: Donor review data
        session: Database session (injected)

    Returns:
        DonorsReviewResponse with the created donor review record

    Example:
        POST /api/v1/donors-review
        {
            "companyId": 1,
            "completeName": "John Doe",
            "email": "john@example.com",
            "phoneNumber": "555-1234"
        }
    """
    logger.info(
        f"Creating donor review record for company_id={donor_data.CompanyId}",
        extra={"company_id": donor_data.CompanyId, "complete_name": donor_data.CompleteName},
    )

    try:
        # Create new donor review record
        new_donor = DonorsReview(
            CompanyId=donor_data.CompanyId,
            NamePrefix=donor_data.NamePrefix,
            CompleteName=donor_data.CompleteName,
            AddressLine1=donor_data.AddressLine1,
            AddressLine2=donor_data.AddressLine2,
            City=donor_data.City,
            State=donor_data.State,
            PostalCode=donor_data.PostalCode,
            CountryCode=donor_data.CountryCode,
            PhoneNumber=donor_data.PhoneNumber,
            EMail=donor_data.EMail,
        )

        session.add(new_donor)
        await session.commit()
        await session.refresh(new_donor)

        donor_model = DonorsReviewModel.model_validate(new_donor)

        logger.info(f"Successfully created donor review record with donor_id={new_donor.DonorId}")
        return DonorsReviewResponse(
            item=donor_model,
            status="success",
        )

    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating donor review record: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating donor review record: {str(e)}",
        )


@router.delete(
    "/{donor_id}",
    status_code=204,
    summary="Delete a donor review record",
    description="Delete a donor review record by ID",
)
async def delete_donor_review(
    donor_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """
    Delete a donor review record.

    Args:
        donor_id: Donor identifier
        session: Database session (injected)

    Raises:
        HTTPException: 404 if donor review record not found

    Example:
        DELETE /api/v1/donors-review/1
    """
    logger.info(f"Deleting donor review record for donor_id={donor_id}")

    try:
        # Check if record exists
        query = select(DonorsReview).where(DonorsReview.DonorId == donor_id)
        result = await session.execute(query)
        donor = result.scalar_one_or_none()

        if not donor:
            logger.warning(f"Donor review record not found: donor_id={donor_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Donor review record not found for donor_id={donor_id}",
            )

        # Delete the record
        delete_query = delete(DonorsReview).where(DonorsReview.DonorId == donor_id)
        await session.execute(delete_query)
        await session.commit()

        logger.info(f"Successfully deleted donor review record for donor_id={donor_id}")

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(
            f"Error deleting donor review record for donor_id={donor_id}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting donor review record: {str(e)}",
        )
