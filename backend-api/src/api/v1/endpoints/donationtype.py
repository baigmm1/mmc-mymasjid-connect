"""
DonationType endpoints for managing donation type data.

Provides GET endpoints for retrieving donation types with optional filtering.
All endpoints require companyId for filtering.

Endpoints:
    GET /api/v1/donationtype/{company_id} - Get all donation types for a company with optional filters
    GET /api/v1/donationtype/{company_id}/{donation_type} - Get single donation type by company and type
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.cache_manager import (
    get_donation_type_from_cache,
    get_donation_types_for_company_from_cache,
    get_kiosk_donation_types_for_company_from_cache,
)
from src.core.logging import get_logger
from src.database import get_session
from src.database.models.donation_type import DonationType
from src.models.donation_type import (
    DonationTypeListResponse,
    DonationTypeModel,
    DonationTypeResponse,
)

router = APIRouter(prefix="/donationtypes", tags=["donationtype"])
logger = get_logger(__name__, level=settings.LOG_LEVEL)


@router.get(
    "/{company_id}",
    response_model=DonationTypeListResponse,
    status_code=200,
    summary="Get donation types for a company",
    description="Retrieve all donation types for a specific company with optional filtering",
)
async def get_donation_types(
    company_id: int,
    status_code: Optional[int] = Query(None, alias="statusCode", description="Filter by status code"),
    tax_receipt: Optional[int] = Query(None, alias="taxReceipt", description="Filter by tax receipt flag (0 or 1)"),
    show_web: Optional[int] = Query(None, alias="showWeb", description="Filter by show on web flag (0 or 1)"),
    show_tablet: Optional[int] = Query(None, alias="showTablet", description="Filter by show on tablet flag (0 or 1)"),
    show_phone: Optional[int] = Query(None, alias="showPhone", description="Filter by show on phone flag (0 or 1)"),
    show_kiosk: Optional[int] = Query(None, alias="showKiosk", description="Filter by show on kiosk flag (0 or 1)"),
    show_pledge: Optional[int] = Query(None, alias="showPledge", description="Filter by show on pledge page flag (0 or 1)"),
    session: AsyncSession = Depends(get_session),
) -> DonationTypeListResponse:
    """
    Get list of donation types for a specific company with optional filtering.

    Args:
        company_id: Company identifier (required)
        status_code: Optional status code filter
        tax_receipt: Optional tax receipt flag filter (0 or 1)
        show_web: Optional show on web flag filter (0 or 1)
        show_tablet: Optional show on tablet flag filter (0 or 1)
        show_phone: Optional show on phone flag filter (0 or 1)
        show_kiosk: Optional show on kiosk flag filter (0 or 1)
        session: Database session (injected)

    Returns:
        DonationTypeListResponse with count and list of donation types

    Example:
        GET /api/v1/donationtypes/1
        GET /api/v1/donationtypes/1?statusCode=1
        GET /api/v1/donationtypes/1?showWeb=1&taxReceipt=1
        GET /api/v1/donationtypes/1?statusCode=1&showTablet=1
    """
    logger.info(
        f"Retrieving donation types for company {company_id}",
        extra={
            "company_id": company_id,
            "status_code_filter": status_code,
            "tax_receipt_filter": tax_receipt,
            "show_web_filter": show_web,
            "show_tablet_filter": show_tablet,
            "show_phone_filter": show_phone,
            "show_kiosk_filter": show_kiosk,
            "show_pledge_filter": show_pledge,
        },
    )

    try:
        # Check if we have filters - if not, use cache
        has_filters = any([
            status_code is not None,
            tax_receipt is not None,
            show_web is not None,
            show_tablet is not None,
            show_phone is not None,
            show_kiosk is not None,
            show_pledge is not None,
        ])

        if not has_filters:
            # No filters, get from cache
            donation_types = await get_donation_types_for_company_from_cache(company_id)
            # Sort by SortOrder for consistent display
            donation_types = sorted(
                donation_types,
                key=lambda dt: (dt.SortOrder or 0, dt.DonationType)
            )
            logger.info(f"Retrieved {len(donation_types)} donation types from cache for company {company_id}")
        else:
            # Has filters, query database
            # Always filter by company_id
            query = select(DonationType).where(DonationType.CompanyId == company_id)

            if status_code is not None:
                query = query.where(DonationType.StatusCode == status_code)
                logger.debug(f"Applied status_code filter: {status_code}")
            if tax_receipt is not None:
                query = query.where(DonationType.TaxReceipt == tax_receipt)
                logger.debug(f"Applied tax_receipt filter: {tax_receipt}")
            if show_web is not None:
                query = query.where(DonationType.ShowWeb == show_web)
                logger.debug(f"Applied show_web filter: {show_web}")
            if show_tablet is not None:
                query = query.where(DonationType.ShowTablet == show_tablet)
                logger.debug(f"Applied show_tablet filter: {show_tablet}")
            if show_phone is not None:
                query = query.where(DonationType.ShowPhone == show_phone)
                logger.debug(f"Applied show_phone filter: {show_phone}")
            if show_kiosk is not None:
                query = query.where(DonationType.ShowKiosk == show_kiosk)
                logger.debug(f"Applied show_kiosk filter: {show_kiosk}")
            if show_pledge is not None:
                query = query.where(DonationType.ShowPledge == show_pledge)
                logger.debug(f"Applied show_pledge filter: {show_pledge}")

            # Order by SortOrder for consistent display
            query = query.order_by(DonationType.SortOrder, DonationType.DonationType)

            result = await session.execute(query)
            donation_types = result.scalars().all()
            logger.info(f"Retrieved {len(donation_types)} donation types from database (filtered) for company {company_id}")

        logger.info(
            f"Retrieved {len(donation_types)} donation types for company {company_id}",
            extra={"count": len(donation_types), "company_id": company_id},
        )

        return DonationTypeListResponse(
            count=len(donation_types),
            items=[DonationTypeModel.model_validate(dt) for dt in donation_types],
            status="success"
        )
    except Exception as e:
        logger.error(
            f"Error retrieving donation types: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise


@router.get(
    "/{company_id}/{donation_type}",
    response_model=DonationTypeResponse,
    status_code=200,
    summary="Get donation type by company and type",
    description="Retrieve a single donation type by company ID and donation type ID",
)
async def get_donation_type_by_id(
    company_id: int,
    donation_type: int,
    session: AsyncSession = Depends(get_session),
) -> DonationTypeResponse:
    """
    Get a single donation type by company ID and donation type ID.

    Args:
        company_id: Company identifier
        donation_type: Donation type identifier
        session: Database session (injected)

    Returns:
        DonationTypeResponse with donation type details

    Raises:
        HTTPException: 404 if donation type not found

    Example:
        GET /api/v1/donationtype/1/10
        GET /api/v1/donationtype/0/5
    """
    logger.info(
        f"Retrieving donation type {donation_type} for company {company_id}",
        extra={"company_id": company_id, "donation_type": donation_type},
    )

    try:
        # Try cache first, fallback to database
        dt = await get_donation_type_from_cache(company_id, donation_type, session)

        if dt is None:
            logger.warning(
                f"Donation type {donation_type} not found for company {company_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Donation type '{donation_type}' not found for company '{company_id}'"
            )

        logger.info(
            f"Retrieved donation type: {dt.ShortName or 'Unnamed'}",
            extra={"company_id": company_id, "donation_type": donation_type}
        )
        return DonationTypeResponse(
            item=DonationTypeModel.model_validate(dt),
            status="success"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving donation type: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise

