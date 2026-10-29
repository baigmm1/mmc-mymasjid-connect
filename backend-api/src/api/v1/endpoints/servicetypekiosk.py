"""
ServiceType endpoints for managing service type data for kiosks.

Provides GET endpoints for retrieving service types with optional filtering.
All endpoints require companyId for filtering.

Endpoints:
    GET /api/v1/kiosk/servicetype/{company_id} - Get all service types for a company with optional filters
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.cache_manager import (
    clear_kiosk_service_type_cache,
    get_kiosk_service_types_for_company_from_cache,
    warm_kiosk_service_type_cache,
)
from src.core.logging import get_logger
from src.database import get_session
from src.database.models.donation_type import DonationType
from src.models.service_type import (
    ServiceTypeListResponse,
    ServiceTypeModel,
    ServiceTypeResponse,
)

router = APIRouter(prefix="/kiosk/servicetypes", tags=["kioskservicetype"])
logger = get_logger(__name__, level=settings.LOG_LEVEL)


@router.get(
    "/{company_id}",
    response_model=ServiceTypeListResponse,
    status_code=200,
    summary="Get service types for a company",
    description="Retrieve all service types for a specific company with optional filtering",
)
async def get_kiosk_service_types(
    company_id: int,
    refresh: bool = Query(False, description="Force cache refresh"),
    session: AsyncSession = Depends(get_session),
) -> ServiceTypeListResponse:
    """
    Get list of service types for a specific company with optional filtering.

    Args:
        company_id: Company identifier (required)
        refresh: Force cache refresh if True (default: False)
        session: Database session (injected)

    Returns:
        ServiceTypeListResponse with count and list of service types

    Example:
        GET /api/v1/servicetype/kiosk/1
        GET /api/v1/servicetype/kiosk/1?refresh=true
    """
    logger.info(
        f"Retrieving service types for company {company_id} (refresh={refresh})",
        extra={
            "company_id": company_id,
            "refresh": refresh,
        },
    )
    print(f"Retrieving kiosk service types for company {company_id} (refresh={refresh})")
    try:
        # Force cache refresh if requested
        if refresh:
            logger.info(f"Forcing cache refresh for company {company_id}")
            await clear_kiosk_service_type_cache()
            await warm_kiosk_service_type_cache(session)
        
        service_types = await get_kiosk_service_types_for_company_from_cache(company_id)
        # Sort by SortOrder for consistent display
        service_types = sorted(
            service_types,
            key=lambda dt: (dt.SortOrder or 0, dt.DonationType)
        )
        logger.info(f"Retrieved {len(service_types)} service types from cache for company {company_id}")

        # Convert database objects to response models
        service_type_models = [
            ServiceTypeModel.model_validate(dt) for dt in service_types
        ]

        return ServiceTypeListResponse(
            count=len(service_type_models),
            items=service_type_models,
            status="success"
        )
    except Exception as e:
        logger.error(
            f"Error retrieving service types: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise