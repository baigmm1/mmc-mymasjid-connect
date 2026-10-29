"""
DonationType endpoints for managing donation type data for kiosks.

Provides GET endpoints for retrieving donation types with optional filtering.
All endpoints require companyId for filtering.

Endpoints:
    GET /api/v1/kiosk/donationtype/{company_id} - Get all donation types for a company with optional filters
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.cache_manager import (
    clear_kiosk_donation_type_cache,
    get_kiosk_donation_types_for_company_from_cache,
    warm_kiosk_donation_type_cache,
)
from src.core.logging import get_logger
from src.database import get_session
from src.database.models.donation_type import DonationType
from src.models.donation_type import (
    DonationTypeListResponse,
    DonationTypeModel,
    DonationTypeResponse,
)

router = APIRouter(prefix="/kiosk/donationtypes", tags=["kioskdonationtype"])
logger = get_logger(__name__, level=settings.LOG_LEVEL)


@router.get(
    "/{company_id}",
    response_model=DonationTypeListResponse,
    status_code=200,
    summary="Get donation types for a company",
    description="Retrieve all donation types for a specific company with optional filtering",
)
async def get_kiosk_donation_types(
    company_id: int,
    refresh: bool = Query(False, description="Force cache refresh"),
    session: AsyncSession = Depends(get_session),
) -> DonationTypeListResponse:
    """
    Get list of donation types for a specific company with optional filtering.

    Args:
        company_id: Company identifier (required)
        refresh: Force cache refresh if True (default: False)
        session: Database session (injected)

    Returns:
        DonationTypeListResponse with count and list of donation types

    Example:
        GET /api/v1/donationtype/kiosk/1
        GET /api/v1/donationtype/kiosk/1?refresh=true
    """
    logger.info(
        f"Retrieving donation types for company {company_id} (refresh={refresh})",
        extra={
            "company_id": company_id,
            "refresh": refresh,
        },
    )
    print(f"Retrieving kiosk donation types for company {company_id} (refresh={refresh})")
    try:
        # Force cache refresh if requested
        if refresh:
            logger.info(f"Forcing cache refresh for company {company_id}")
            await clear_kiosk_donation_type_cache()
            await warm_kiosk_donation_type_cache(session)
        
        donation_types = await get_kiosk_donation_types_for_company_from_cache(company_id)
        # Sort by SortOrder for consistent display
        donation_types = sorted(
            donation_types,
            key=lambda dt: (dt.SortOrder or 0, dt.DonationType)
        )
        logger.info(f"Retrieved {len(donation_types)} donation types from cache for company {company_id}")

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