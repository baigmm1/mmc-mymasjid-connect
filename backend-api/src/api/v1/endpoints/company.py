"""
Company endpoints for managing company data.

Provides GET endpoints for retrieving companies with optional filtering.

Endpoints:
    GET /api/v1/company - Get all or filtered companies
    GET /api/v1/company/{company_id} - Get single company by ID
    GET /api/v1/company/by-short-name/{short_name} - Get single company by short name
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.cache_manager import get_companies_from_cache, get_company_from_cache
from src.core.logging import get_logger
from src.database import get_session
from src.database.models.company import Company
from src.models.company import (
    CompanyListResponse,
    CompanyModel,
    CompanyResponse,
)

router = APIRouter(prefix="/company", tags=["company"])
logger = get_logger(__name__, level=settings.LOG_LEVEL)


@router.get(
    "",
    response_model=CompanyListResponse,
    status_code=200,
    summary="Get companies",
    description="Retrieve all companies or filter by various criteria",
)
async def get_companies(
    company_name: Optional[str] = Query(None, description="Filter by company name (partial match)"),
    short_name: Optional[str] = Query(None, description="Filter by short name (partial match)"),
    city: Optional[str] = Query(None, description="Filter by city (partial match)"),
    state_code: Optional[str] = Query(None, description="Filter by state code"),
    country_code: Optional[str] = Query(None, description="Filter by country code"),
    session: AsyncSession = Depends(get_session),
) -> CompanyListResponse:
    """
    Get list of companies with optional filtering.

    Args:
        company_name: Optional company name filter (case-insensitive partial match)
        short_name: Optional short name filter (case-insensitive partial match)
        city: Optional city filter (case-insensitive partial match)
        state_code: Optional state code filter
        country_code: Optional country code filter
        session: Database session (injected)

    Returns:
        CompanyListResponse with count and list of companies

    Example:
        GET /api/v1/company
        GET /api/v1/company?company_name=Acme
        GET /api/v1/company?city=New York&state_code=NY
        GET /api/v1/company?country_code=US
    """
    logger.info(
        "Retrieving companies",
        extra={
            "company_name_filter": company_name,
            "short_name_filter": short_name,
            "city_filter": city,
            "state_code_filter": state_code,
            "country_code_filter": country_code,
        },
    )

    try:
        # Try to get from cache first (filters will be applied to cached data)
        if not any([company_name, short_name, city, state_code, country_code]):
            # No filters, can use cached data directly
            companies = await get_companies_from_cache()
            logger.info(f"Retrieved {len(companies)} companies from cache")
        else:
            # Has filters, need to query database
            query = select(Company)

            #default query will return all companies except the master configuration
            query = query.where(Company.CompanyId != 0)

            if company_name:
                query = query.where(Company.CompanyName.ilike(f"%{company_name}%"))
                logger.debug(f"Applied company_name filter: {company_name}")
            if short_name:
                query = query.where(Company.ShortName.ilike(f"%{short_name}%"))
                logger.debug(f"Applied short_name filter: {short_name}")
            if city:
                query = query.where(Company.City.ilike(f"%{city}%"))
                logger.debug(f"Applied city filter: {city}")
            if state_code:
                query = query.where(Company.StateCode == state_code)
                logger.debug(f"Applied state_code filter: {state_code}")
            if country_code:
                query = query.where(Company.CountryCode == country_code)
                logger.debug(f"Applied country_code filter: {country_code}")

            result = await session.execute(query)
            companies = result.scalars().all()
            logger.info(f"Retrieved {len(companies)} companies from database (filtered)")

        logger.info(
            f"Retrieved {len(companies)} companies",
            extra={"count": len(companies)},
        )

        return CompanyListResponse(
            count=len(companies),
            items=[CompanyModel.model_validate(company) for company in companies],
            status="success"
        )
    except Exception as e:
        logger.error(
            f"Error retrieving companies: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise


@router.get(
    "/{company_id}",
    response_model=CompanyResponse,
    status_code=200,
    summary="Get company by ID",
    description="Retrieve a single company by its unique ID",
)
async def get_company_by_id(
    company_id: int,
    session: AsyncSession = Depends(get_session),
) -> CompanyResponse:
    """
    Get a single company by company ID.

    Args:
        company_id: Unique company identifier
        session: Database session (injected)

    Returns:
        CompanyResponse with company details

    Raises:
        HTTPException: 404 if company ID not found

    Example:
        GET /api/v1/company/1
        GET /api/v1/company/100
    """
    logger.info(
        f"Retrieving company by ID: {company_id}",
        extra={"company_id": company_id},
    )

    try:
        # Try cache first, fallback to database
        company = await get_company_from_cache(company_id, session)

        if company is None:
            logger.warning(f"Company ID not found: {company_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ID '{company_id}' not found"
            )

        logger.info(f"Retrieved company: {company.CompanyName}")
        return CompanyResponse(
            item=CompanyModel.model_validate(company),
            status="success"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving company by ID: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise


@router.get(
    "/by-short-name/{short_name}",
    response_model=CompanyResponse,
    status_code=200,
    summary="Get company by short name",
    description="Retrieve a single company by its unique short name",
)
async def get_company_by_short_name(
    short_name: str,
    session: AsyncSession = Depends(get_session),
) -> CompanyResponse:
    """
    Get a single company by short name.

    Args:
        short_name: Unique company short name (case-insensitive)
        session: Database session (injected)

    Returns:
        CompanyResponse with company details

    Raises:
        HTTPException: 404 if short name not found

    Example:
        GET /api/v1/company/by-short-name/MASTER
        GET /api/v1/company/by-short-name/ACME
    """
    logger.info(
        f"Retrieving company by short name: {short_name}",
        extra={"short_name": short_name},
    )

    try:
        query = select(Company).where(Company.ShortName.ilike(short_name))
        result = await session.execute(query)
        company = result.scalar_one_or_none()

        if company is None:
            logger.warning(f"Company short name not found: {short_name}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with short name '{short_name}' not found"
            )

        logger.info(f"Retrieved company: {company.CompanyName}")
        return CompanyResponse(
            item=CompanyModel.model_validate(company),
            status="success"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving company by short name: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise
