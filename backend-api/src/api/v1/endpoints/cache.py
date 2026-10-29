"""
Cache management endpoints for administrative operations.

Provides endpoints for monitoring and managing application caches.
These endpoints are useful for debugging and manual cache operations.

Endpoints:
    GET /api/v1/cache/stats - Get cache statistics
    POST /api/v1/cache/clear - Clear all caches
    POST /api/v1/cache/refresh - Refresh all caches from database
    POST /api/v1/cache/refresh/company - Refresh company cache
    POST /api/v1/cache/refresh/donation-types - Refresh donation types cache
    POST /api/v1/cache/refresh/kiosk-donation-types - Refresh kiosk donation types cache
    POST /api/v1/cache/refresh/kiosk-service-types - Refresh kiosk service types cache
    POST /api/v1/cache/refresh/provider-configurations - Refresh provider configurations cache
"""

from typing import Dict

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.cache_manager import (
    clear_all_caches,
    clear_company_cache,
    clear_donation_type_cache,
    clear_kiosk_donation_type_cache,
    clear_kiosk_service_type_cache,
    clear_provider_configuration_cache,
    get_cache_stats,
    warm_all_caches,
    warm_company_cache,
    warm_donation_type_cache,
    warm_kiosk_donation_type_cache,
    warm_kiosk_service_type_cache,
    warm_provider_configuration_cache,
)
from src.core.logging import get_logger
from src.database import get_session

router = APIRouter(prefix="/cache", tags=["cache"])
logger = get_logger(__name__, level=settings.LOG_LEVEL)


class CacheStatsResponse(BaseModel):
    """Response schema for cache statistics."""

    stats: Dict
    status: str = "success"


class CacheOperationResponse(BaseModel):
    """Response schema for cache operations."""

    message: str
    details: Dict
    status: str = "success"


@router.get(
    "/stats",
    response_model=CacheStatsResponse,
    status_code=200,
    summary="Get cache statistics",
    description="Retrieve statistics for all application caches",
)
async def get_stats() -> CacheStatsResponse:
    """
    Get statistics for all application caches.

    Returns comprehensive statistics including:
    - Total items in each cache
    - Active (non-expired) items
    - Expired items
    - TTL configuration
    - Refresh settings

    Returns:
        CacheStatsResponse with cache statistics

    Example:
        GET /api/v1/cache/stats
    """
    logger.info("Retrieving cache statistics")

    try:
        stats = get_cache_stats()
        logger.info(f"Cache statistics retrieved: {stats}")

        return CacheStatsResponse(
            stats=stats,
            status="success"
        )

    except Exception as e:
        logger.error(
            f"Error retrieving cache statistics: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise


@router.post(
    "/clear",
    response_model=CacheOperationResponse,
    status_code=200,
    summary="Clear all caches",
    description="Remove all items from all application caches",
)
async def clear_caches() -> CacheOperationResponse:
    """
    Clear all application caches.

    This removes all cached items from all caches. Subsequent requests
    will need to fetch data from the database until caches are warmed again.

    Returns:
        CacheOperationResponse with operation results

    Example:
        POST /api/v1/cache/clear
    """
    logger.info("Clearing all caches")

    try:
        result = await clear_all_caches()
        logger.info(f"All caches cleared: {result}")

        return CacheOperationResponse(
            message="All caches cleared successfully",
            details=result,
            status="success"
        )

    except Exception as e:
        logger.error(
            f"Error clearing caches: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise


@router.post(
    "/refresh",
    response_model=CacheOperationResponse,
    status_code=200,
    summary="Refresh all caches",
    description="Clear and reload all caches from database",
)
async def refresh_caches(
    session: AsyncSession = Depends(get_session),
) -> CacheOperationResponse:
    """
    Refresh all application caches.

    This clears existing caches and reloads them with fresh data from
    the database. Use this after making database changes that should
    be immediately reflected in the cache.

    Args:
        session: Database session (injected)

    Returns:
        CacheOperationResponse with operation results

    Example:
        POST /api/v1/cache/refresh
    """
    logger.info("Refreshing all caches")

    try:
        # Clear existing caches
        clear_result = await clear_all_caches()
        logger.info(f"Caches cleared: {clear_result}")

        # Warm caches with fresh data
        warm_result = await warm_all_caches(session)
        logger.info(f"Caches warmed: {warm_result}")

        return CacheOperationResponse(
            message="All caches refreshed successfully",
            details={
                "cleared": clear_result,
                "loaded": warm_result,
            },
            status="success"
        )

    except Exception as e:
        logger.error(
            f"Error refreshing caches: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise

@router.post(
    "/refresh/company",
    response_model=CacheOperationResponse,
    status_code=200,
    summary="Refresh company cache",
    description="Clear and reload company cache from database",
)
async def refresh_company_cache(
    session: AsyncSession = Depends(get_session),
) -> CacheOperationResponse:
    """
    Refresh company cache.

    This clears the company cache and reloads it with fresh data from
    the database. Use this after making company-related changes.

    Args:
        session: Database session (injected)

    Returns:
        CacheOperationResponse with operation results

    Example:
        POST /api/v1/cache/refresh/company
    """
    logger.info("Refreshing company cache")

    try:
        # Clear company cache
        clear_result = await clear_company_cache()
        logger.info(f"Company cache cleared: {clear_result} items removed")

        # Warm company cache with fresh data
        warm_result = await warm_company_cache(session)
        logger.info(f"Company cache warmed: {warm_result} items loaded")

        return CacheOperationResponse(
            message="Company cache refreshed successfully",
            details={
                "cleared": clear_result,
                "loaded": warm_result,
            },
            status="success"
        )

    except Exception as e:
        logger.error(
            f"Error refreshing company cache: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise


@router.post(
    "/refresh/donation-types",
    response_model=CacheOperationResponse,
    status_code=200,
    summary="Refresh donation types cache",
    description="Clear and reload donation types cache from database",
)
async def refresh_donation_types_cache(
    session: AsyncSession = Depends(get_session),
) -> CacheOperationResponse:
    """
    Refresh donation types cache.

    This clears the donation types cache and reloads it with fresh data from
    the database. Use this after making donation type changes.

    Args:
        session: Database session (injected)

    Returns:
        CacheOperationResponse with operation results

    Example:
        POST /api/v1/cache/refresh/donation-types
    """
    logger.info("Refreshing donation types cache")

    try:
        # Clear donation type cache
        clear_result = await clear_donation_type_cache()
        logger.info(f"Donation types cache cleared: {clear_result} items removed")

        # Warm donation type cache with fresh data
        warm_result = await warm_donation_type_cache(session)
        logger.info(f"Donation types cache warmed: {warm_result} items loaded")

        return CacheOperationResponse(
            message="Donation types cache refreshed successfully",
            details={
                "cleared": clear_result,
                "loaded": warm_result,
            },
            status="success"
        )

    except Exception as e:
        logger.error(
            f"Error refreshing donation types cache: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise


@router.post(
    "/refresh/kiosk-donation-types",
    response_model=CacheOperationResponse,
    status_code=200,
    summary="Refresh kiosk donation types cache",
    description="Clear and reload kiosk donation types cache from database",
)
async def refresh_kiosk_donation_types_cache(
    session: AsyncSession = Depends(get_session),
) -> CacheOperationResponse:
    """
    Refresh kiosk donation types cache.

    This clears the kiosk donation types cache and reloads it with fresh data from
    the database. Use this after making kiosk donation type changes.

    Args:
        session: Database session (injected)

    Returns:
        CacheOperationResponse with operation results

    Example:
        POST /api/v1/cache/refresh/kiosk-donation-types
    """
    logger.info("Refreshing kiosk donation types cache")

    try:
        # Clear kiosk donation type cache
        clear_result = await clear_kiosk_donation_type_cache()
        logger.info(f"Kiosk donation types cache cleared: {clear_result} items removed")

        # Warm kiosk donation type cache with fresh data
        warm_result = await warm_kiosk_donation_type_cache(session)
        logger.info(f"Kiosk donation types cache warmed: {warm_result} items loaded")

        return CacheOperationResponse(
            message="Kiosk donation types cache refreshed successfully",
            details={
                "cleared": clear_result,
                "loaded": warm_result,
            },
            status="success"
        )

    except Exception as e:
        logger.error(
            f"Error refreshing kiosk donation types cache: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise


@router.post(
    "/refresh/kiosk-service-types",
    response_model=CacheOperationResponse,
    status_code=200,
    summary="Refresh kiosk service types cache",
    description="Clear and reload kiosk service types cache from database",
)
async def refresh_kiosk_service_types_cache(
    session: AsyncSession = Depends(get_session),
) -> CacheOperationResponse:
    """
    Refresh kiosk service types cache.

    This clears the kiosk service types cache and reloads it with fresh data from
    the database. Use this after making kiosk service type changes.

    Args:
        session: Database session (injected)

    Returns:
        CacheOperationResponse with operation results

    Example:
        POST /api/v1/cache/refresh/kiosk-service-types
    """
    logger.info("Refreshing kiosk service types cache")

    try:
        # Clear kiosk service type cache
        clear_result = await clear_kiosk_service_type_cache()
        logger.info(f"Kiosk service types cache cleared: {clear_result} items removed")

        # Warm kiosk service type cache with fresh data
        warm_result = await warm_kiosk_service_type_cache(session)
        logger.info(f"Kiosk service types cache warmed: {warm_result} items loaded")

        return CacheOperationResponse(
            message="Kiosk service types cache refreshed successfully",
            details={
                "cleared": clear_result,
                "loaded": warm_result,
            },
            status="success"
        )

    except Exception as e:
        logger.error(
            f"Error refreshing kiosk service types cache: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise


@router.post(
    "/refresh/provider-configurations",
    response_model=CacheOperationResponse,
    status_code=200,
    summary="Refresh provider configurations cache",
    description="Clear and reload provider configurations cache from database",
)
async def refresh_provider_configurations_cache(
    session: AsyncSession = Depends(get_session),
) -> CacheOperationResponse:
    """
    Refresh provider configurations cache.

    This clears the provider configurations cache and reloads it with fresh data from
    the database. Use this after making provider configuration changes.

    Args:
        session: Database session (injected)

    Returns:
        CacheOperationResponse with operation results

    Example:
        POST /api/v1/cache/refresh/provider-configurations
    """
    logger.info("Refreshing provider configurations cache")

    try:
        # Clear provider configuration cache
        clear_result = await clear_provider_configuration_cache()
        logger.info(f"Provider configurations cache cleared: {clear_result} items removed")

        # Warm provider configuration cache with fresh data
        warm_result = await warm_provider_configuration_cache(session)
        logger.info(f"Provider configurations cache warmed: {warm_result} items loaded")

        return CacheOperationResponse(
            message="Provider configurations cache refreshed successfully",
            details={
                "cleared": clear_result,
                "loaded": warm_result,
            },
            status="success"
        )

    except Exception as e:
        logger.error(
            f"Error refreshing provider configurations cache: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise