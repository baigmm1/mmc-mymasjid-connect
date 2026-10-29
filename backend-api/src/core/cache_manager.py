"""
Application-wide cache management and initialization.

Manages cache instances for frequently accessed data models including
Company and DonationType data. Provides cache warming on startup and
cache refresh utilities.
"""

import asyncio
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cache import CacheDict
from src.core.logging import get_logger
from src.database.models.company import Company
from src.database.models.donation_type import DonationType
from src.database.models.provider_configuration import ProviderConfiguration

logger = get_logger(__name__)

# Background task control
_background_refresh_task: Optional[asyncio.Task] = None
_shutdown_event: Optional[asyncio.Event] = None

# Global cache instances
# These are initialized on application startup
company_cache: Optional[CacheDict[Company]] = None
donation_type_cache: Optional[CacheDict[DonationType]] = None
kiosk_donation_type_cache: Optional[CacheDict[DonationType]] = None
kiosk_service_type_cache: Optional[CacheDict[DonationType]] = None
provider_configuration_cache: Optional[CacheDict[ProviderConfiguration]] = None

def initialize_caches(
    company_ttl: int = 86400,  # 24 hour default
    donation_type_ttl: int = 86400,  # 24 hour default
    kiosk_donation_type_ttl: int = 86400,  # 24 hour default
    kiosk_service_type_ttl: int = 86400,  # 24 hour default
    provider_configuration_ttl: int = 86400,  # 24 hour default
) -> None:
    """
    Initialize all application cache instances.

    Should be called during application startup (e.g., in lifespan event).

    Args:
        company_ttl: TTL in seconds for company cache (default: 3600 = 1 hour)
        donation_type_ttl: TTL in seconds for donation type cache (default: 3600 = 1 hour)
        provider_configuration_ttl: TTL in seconds for provider configuration cache (default: 86400 = 24 hours)
    """
    global company_cache, donation_type_cache, kiosk_donation_type_cache, kiosk_service_type_cache, provider_configuration_cache

    company_cache = CacheDict[Company](
        ttl_seconds=company_ttl,
        refresh_on_access=False,
        name="CompanyCache",
    )

    donation_type_cache = CacheDict[DonationType](
        ttl_seconds=donation_type_ttl,
        refresh_on_access=False,
        name="DonationTypeCache",
    )

    kiosk_donation_type_cache = CacheDict(
        ttl_seconds=kiosk_donation_type_ttl,
        refresh_on_access=False,
        name="KioskDonationTypeCache",
    )
    kiosk_service_type_cache = CacheDict(
        ttl_seconds=kiosk_service_type_ttl,
        refresh_on_access=False,
        name="KioskServiceTypeCache",
    )

    provider_configuration_cache = CacheDict[ProviderConfiguration](
        ttl_seconds=provider_configuration_ttl,
        refresh_on_access=False,
        name="ProviderConfigurationCache",
    )

    logger.info(
        f"Initialized application caches: Company (TTL={company_ttl}s), "
        f"DonationType (TTL={donation_type_ttl}s),"
        f"KioskDonationType (TTL={kiosk_donation_type_ttl}s), "
        f"KioskServiceType (TTL={kiosk_service_type_ttl}s), "
        f"ProviderConfiguration (TTL={provider_configuration_ttl}s)"
    )


async def warm_company_cache(session: AsyncSession) -> int:
    """
    Pre-load all companies into cache.

    Args:
        session: Database session

    Returns:
        Number of companies loaded into cache

    Raises:
        RuntimeError: If company_cache is not initialized
    """
    if company_cache is None:
        raise RuntimeError("Company cache not initialized. Call initialize_caches() first.")

    logger.info("Warming company cache...")

    try:
        # Query all companies (excluding master config with CompanyId=0)
        result = await session.execute(
            select(Company).where(Company.CompanyId != 0)
        )
        companies = result.scalars().all()

        # Load into cache
        count = 0
        for company in companies:
            await company_cache.set(company.CompanyId, company)
            count += 1

        logger.info(f"Warmed company cache with {count} companies")
        return count

    except Exception as e:
        logger.error(f"Error warming company cache: {e}")
        raise


async def warm_donation_type_cache(session: AsyncSession) -> int:
    """
    Pre-load all donation types into cache.

    Cache key format: (company_id, donation_type)

    Args:
        session: Database session

    Returns:
        Number of donation types loaded into cache

    Raises:
        RuntimeError: If donation_type_cache is not initialized
    """
    if donation_type_cache is None:
        raise RuntimeError("Donation type cache not initialized. Call initialize_caches() first.")

    logger.info("Warming donation type cache...")

    try:
        # Query all donation types
        result = await session.execute(select(DonationType))
        donation_types = result.scalars().all()

        # Load into cache with composite key (CompanyId, DonationType)
        count = 0
        for dt in donation_types:
            cache_key = (dt.CompanyId, dt.DonationType)
            await donation_type_cache.set(cache_key, dt)
            count += 1

        logger.info(f"Warmed donation type cache with {count} donation types")
        return count

    except Exception as e:
        logger.error(f"Error warming donation type cache: {e}")
        raise

async def warm_kiosk_donation_type_cache(session: AsyncSession) -> int:
    """
    Pre-load all donation types into cache.

    Cache key format: (company_id, donation_type)

    Args:
        session: Database session

    Returns:
        Number of donation types loaded into cache

    Raises:
        RuntimeError: If donation_type_cache is not initialized
    """

    if kiosk_donation_type_cache is None:
        raise RuntimeError("Kiosk donation type cache not initialized. Call initialize_caches() first.")

    logger.info("Warming kiosk donation type cache...")

    try:
        query = select(DonationType).where(DonationType.StatusCode == 2)
        query = query.where(DonationType.ShowKiosk == 1)
        query = query.where(DonationType.TaxReceipt == 1)
        #query = query.order_by(DonationType.SortOrder, DonationType.DonationType)

        result = await session.execute(query)
        donation_types = result.scalars().all()

        # Load into cache with composite key (CompanyId, DonationType)
        count = 0
        for dt in donation_types:
            cache_key = (dt.CompanyId, dt.DonationType)
            await kiosk_donation_type_cache.set(cache_key, dt)
            count += 1

        logger.info(f"Warmed kiosk donation type cache with {count} donation types")
        return count

    except Exception as e:
        logger.error(f"Error warming kiosk donation type cache: {e}")
        raise

async def warm_kiosk_service_type_cache(session: AsyncSession) -> int:
    """
    Pre-load all donation types into cache.

    Cache key format: (company_id, donation_type)

    Args:
        session: Database session

    Returns:
        Number of donation types loaded into cache

    Raises:
        RuntimeError: If donation_type_cache is not initialized
    """

    if kiosk_service_type_cache is None:
        raise RuntimeError("Kiosk service type cache not initialized. Call initialize_caches() first.")

    logger.info("Warming kiosk service type cache...")

    try:
        query = select(DonationType).where(DonationType.StatusCode == 2)
        query = query.where(DonationType.ShowKiosk == 1)
        query = query.where(DonationType.TaxReceipt == 0)
        #query = query.order_by(DonationType.SortOrder, DonationType.DonationType)

        result = await session.execute(query)
        service_types = result.scalars().all()

        # Load into cache with composite key (CompanyId, DonationType)
        count = 0
        for dt in service_types:
            cache_key = (dt.CompanyId, dt.DonationType)
            await kiosk_service_type_cache.set(cache_key, dt)
            count += 1

        logger.info(f"Warmed kiosk service type cache with {count} donation types")
        return count

    except Exception as e:
        logger.error(f"Error warming kiosk service type cache: {e}")
        raise

async def warm_all_caches(session: AsyncSession) -> dict:
    """
    Warm all application caches.

    Convenient function to warm all caches at once during startup.

    Args:
        session: Database session

    Returns:
        Dictionary with cache warming statistics
    """
    logger.info("Warming all caches...")

    company_count = await warm_company_cache(session)
    donation_type_count = await warm_donation_type_cache(session)
    kiosk_dontation_type_count = await warm_kiosk_donation_type_cache(session)
    kiosk_service_type_count = await warm_kiosk_service_type_cache(session)
    provider_configuration_count = await warm_provider_configuration_cache(session)

    stats = {
        "company_count": company_count,
        "donation_type_count": donation_type_count,
        "kiosk_donation_type_count": kiosk_dontation_type_count, 
        "kiosk_service_type_count": kiosk_service_type_count,
        "provider_configuration_count": provider_configuration_count,
        "total_count": company_count + donation_type_count + kiosk_dontation_type_count + kiosk_service_type_count + provider_configuration_count,
    }

    logger.info(f"All caches warmed: {stats}")
    return stats


async def get_company_from_cache(
    company_id: int,
    session: Optional[AsyncSession] = None,
) -> Optional[Company]:
    """
    Get company from cache, with fallback to database if not cached.

    Args:
        company_id: Company identifier
        session: Optional database session for fallback query

    Returns:
        Company object if found, None otherwise

    Raises:
        RuntimeError: If company_cache is not initialized
    """
    if company_cache is None:
        raise RuntimeError("Company cache not initialized. Call initialize_caches() first.")

    # Try cache first
    company = await company_cache.get(company_id)
    if company is not None:
        logger.debug(f"Company {company_id} retrieved from cache")
        return company

    # Fallback to database if session provided
    if session is not None:
        logger.debug(f"Company {company_id} not in cache, querying database")
        result = await session.execute(
            select(Company).where(Company.CompanyId == company_id)
        )
        company = result.scalar_one_or_none()

        if company is not None:
            # Store in cache for future requests
            await company_cache.set(company_id, company)
            logger.debug(f"Company {company_id} loaded from database and cached")

        return company

    return None


async def get_companies_from_cache() -> List[Company]:
    """
    Get all companies from cache.

    Returns:
        List of all cached companies

    Raises:
        RuntimeError: If company_cache is not initialized
    """
    if company_cache is None:
        raise RuntimeError("Company cache not initialized. Call initialize_caches() first.")

    cached_items = await company_cache.get_all()
    return list(cached_items.values())


async def get_donation_type_from_cache(
    company_id: int,
    donation_type: int,
    session: Optional[AsyncSession] = None,
) -> Optional[DonationType]:
    """
    Get donation type from cache, with fallback to database if not cached.

    Args:
        company_id: Company identifier
        donation_type: Donation type identifier
        session: Optional database session for fallback query

    Returns:
        DonationType object if found, None otherwise

    Raises:
        RuntimeError: If donation_type_cache is not initialized
    """
    if donation_type_cache is None:
        raise RuntimeError("Donation type cache not initialized. Call initialize_caches() first.")

    cache_key = (company_id, donation_type)

    # Try cache first
    dt = await donation_type_cache.get(cache_key)
    if dt is not None:
        logger.debug(f"DonationType {cache_key} retrieved from cache")
        return dt

    # Fallback to database if session provided
    if session is not None:
        logger.debug(f"DonationType {cache_key} not in cache, querying database")
        result = await session.execute(
            select(DonationType).where(
                DonationType.CompanyId == company_id,
                DonationType.DonationType == donation_type,
            )
        )
        dt = result.scalar_one_or_none()

        if dt is not None:
            # Store in cache for future requests
            await donation_type_cache.set(cache_key, dt)
            logger.debug(f"DonationType {cache_key} loaded from database and cached")

        return dt

    return None


async def get_donation_types_for_company_from_cache(
    company_id: int,
) -> List[DonationType]:
    """
    Get all donation types for a company from cache.

    Args:
        company_id: Company identifier

    Returns:
        List of donation types for the specified company

    Raises:
        RuntimeError: If donation_type_cache is not initialized
    """
    if donation_type_cache is None:
        raise RuntimeError("Donation type cache not initialized. Call initialize_caches() first.")

    cached_items = await donation_type_cache.get_all()

    # Filter by company_id
    company_donation_types = [
        dt for key, dt in cached_items.items()
        if isinstance(key, tuple) and key[0] == company_id
    ]

    return company_donation_types

async def get_kiosk_donation_types_for_company_from_cache(
    company_id: int,
) -> List[DonationType]:
    """
    Get all donation types for a company from cache.

    Args:
        company_id: Company identifier

    Returns:
        List of donation types for the specified company

    Raises:
        RuntimeError: If donation_type_cache is not initialized
    """
    if kiosk_donation_type_cache is None:
        raise RuntimeError("Kiosk donation type cache not initialized. Call initialize_caches() first.")

    cached_items = await kiosk_donation_type_cache.get_all()

    # Filter by company_id
    company_donation_types = [
        dt for key, dt in cached_items.items()
        if isinstance(key, tuple) and key[0] == company_id
    ]

    return company_donation_types

async def get_kiosk_service_types_for_company_from_cache(
    company_id: int,
) -> List[DonationType]:
    """
    Get all donation types for a company from cache.

    Args:
        company_id: Company identifier

    Returns:
        List of donation types for the specified company

    Raises:
        RuntimeError: If donation_type_cache is not initialized
    """
    if kiosk_service_type_cache is None:
        raise RuntimeError("Kiosk service type cache not initialized. Call initialize_caches() first.")

    cached_items = await kiosk_service_type_cache.get_all()

    # Filter by company_id
    company_donation_types = [
        dt for key, dt in cached_items.items()
        if isinstance(key, tuple) and key[0] == company_id
    ]

    return company_donation_types

async def clear_company_cache() -> int:
    """
    Clear all entries from company cache.

    Returns:
        Number of items cleared

    Raises:
        RuntimeError: If company_cache is not initialized
    """
    if company_cache is None:
        raise RuntimeError("Company cache not initialized. Call initialize_caches() first.")

    return await company_cache.clear()


async def clear_donation_type_cache() -> int:
    """
    Clear all entries from donation type cache.

    Returns:
        Number of items cleared

    Raises:
        RuntimeError: If donation_type_cache is not initialized
    """
    if donation_type_cache is None:
        raise RuntimeError("Donation type cache not initialized. Call initialize_caches() first.")

    return await donation_type_cache.clear()

async def clear_kiosk_donation_type_cache() -> int:
    """
    Clear all entries from kiosk donation type cache.

    Returns:
        Number of items cleared

    Raises:
        RuntimeError: If kiosk_donation_type_cache is not initialized
    """
    if kiosk_donation_type_cache is None:
        raise RuntimeError("Kiosk donation type cache not initialized. Call initialize_caches() first.")

    return await kiosk_donation_type_cache.clear()

async def clear_kiosk_service_type_cache() -> int:
    """
    Clear all entries from kiosk service type cache.

    Returns:
        Number of items cleared

    Raises:
        RuntimeError: If kiosk_service_type_cache is not initialized
    """
    if kiosk_service_type_cache is None:
        raise RuntimeError("Kiosk service type cache not initialized. Call initialize_caches() first.")

    return await kiosk_service_type_cache.clear()


async def warm_provider_configuration_cache(session: AsyncSession) -> int:
    """
    Pre-load all provider configurations into cache.

    Cache key format: (company_id, provider)

    Args:
        session: Database session

    Returns:
        Number of provider configurations loaded into cache

    Raises:
        RuntimeError: If provider_configuration_cache is not initialized
    """
    if provider_configuration_cache is None:
        raise RuntimeError("Provider configuration cache not initialized. Call initialize_caches() first.")

    logger.info("Warming provider configuration cache...")

    try:
        # Query all provider configurations
        result = await session.execute(select(ProviderConfiguration))
        configurations = result.scalars().all()

        # Load into cache with composite key (CompanyId, Provider)
        count = 0
        for config in configurations:
            cache_key = (config.CompanyId, config.Provider)
            await provider_configuration_cache.set(cache_key, config)
            count += 1

        logger.info(f"Warmed provider configuration cache with {count} configurations")
        return count

    except Exception as e:
        logger.error(f"Error warming provider configuration cache: {e}")
        raise


async def get_provider_configuration_from_cache(
    company_id: int,
    provider: str,
    session: Optional[AsyncSession] = None,
) -> Optional[ProviderConfiguration]:
    """
    Get provider configuration from cache, with fallback to database if not cached.

    Args:
        company_id: Company identifier
        provider: Provider name
        session: Optional database session for fallback query

    Returns:
        ProviderConfiguration object if found, None otherwise

    Raises:
        RuntimeError: If provider_configuration_cache is not initialized
    """
    if provider_configuration_cache is None:
        raise RuntimeError("Provider configuration cache not initialized. Call initialize_caches() first.")

    cache_key = (company_id, provider)

    # Try cache first
    config = await provider_configuration_cache.get(cache_key)
    if config is not None:
        logger.debug(f"ProviderConfiguration {cache_key} retrieved from cache")
        return config

    # Fallback to database if session provided
    if session is not None:
        logger.debug(f"ProviderConfiguration {cache_key} not in cache, querying database")
        result = await session.execute(
            select(ProviderConfiguration).where(
                ProviderConfiguration.CompanyId == company_id,
                ProviderConfiguration.Provider == provider,
            )
        )
        config = result.scalar_one_or_none()

        if config is not None:
            # Store in cache for future requests
            await provider_configuration_cache.set(cache_key, config)
            logger.debug(f"ProviderConfiguration {cache_key} loaded from database and cached")

        return config

    return None


async def get_provider_configurations_from_cache() -> List[ProviderConfiguration]:
    """
    Get all provider configurations from cache.

    Returns:
        List of all cached provider configurations

    Raises:
        RuntimeError: If provider_configuration_cache is not initialized
    """
    if provider_configuration_cache is None:
        raise RuntimeError("Provider configuration cache not initialized. Call initialize_caches() first.")

    cached_items = await provider_configuration_cache.get_all()
    return list(cached_items.values())


async def get_provider_configurations_for_company_from_cache(
    company_id: int,
) -> List[ProviderConfiguration]:
    """
    Get all provider configurations for a company from cache.

    Args:
        company_id: Company identifier

    Returns:
        List of provider configurations for the specified company

    Raises:
        RuntimeError: If provider_configuration_cache is not initialized
    """
    if provider_configuration_cache is None:
        raise RuntimeError("Provider configuration cache not initialized. Call initialize_caches() first.")

    cached_items = await provider_configuration_cache.get_all()

    # Filter by company_id
    company_configs = [
        config for key, config in cached_items.items()
        if isinstance(key, tuple) and key[0] == company_id
    ]

    return company_configs


async def clear_provider_configuration_cache() -> int:
    """
    Clear all entries from provider configuration cache.

    Returns:
        Number of items cleared

    Raises:
        RuntimeError: If provider_configuration_cache is not initialized
    """
    if provider_configuration_cache is None:
        raise RuntimeError("Provider configuration cache not initialized. Call initialize_caches() first.")

    return await provider_configuration_cache.clear()


async def clear_all_caches() -> dict:
    """
    Clear all application caches.

    Returns:
        Dictionary with clearing statistics
    """
    company_cleared = await clear_company_cache()
    donation_type_cleared = await clear_donation_type_cache()
    kiosk_donation_type_cleared = await clear_kiosk_donation_type_cache()
    kiosk_service_type_cleared = await clear_kiosk_service_type_cache()
    provider_configuration_cleared = await clear_provider_configuration_cache()

    stats = {
        "company_cleared": company_cleared,
        "donation_type_cleared": donation_type_cleared,
        "kiosk_donation_type_cleared": kiosk_donation_type_cleared,
        "kiosk_service_type_cleared": kiosk_service_type_cleared,
        "provider_configuration_cleared": provider_configuration_cleared,
        "total_cleared": company_cleared + donation_type_cleared + kiosk_donation_type_cleared + kiosk_service_type_cleared + provider_configuration_cleared,
    }

    logger.info(f"All caches cleared: {stats}")
    return stats


def get_cache_stats() -> dict:
    """
    Get statistics for all caches.

    Returns:
        Dictionary with cache statistics
    """
    stats = {}

    if company_cache is not None:
        stats["company_cache"] = company_cache.get_stats()

    if donation_type_cache is not None:
        stats["donation_type_cache"] = donation_type_cache.get_stats()

    if kiosk_donation_type_cache is not None:
        stats["kiosk_donation_type_cache"] = kiosk_donation_type_cache.get_stats()

    if kiosk_service_type_cache is not None:
        stats["kiosk_service_type_cache"] = kiosk_service_type_cache.get_stats()

    if provider_configuration_cache is not None:
        stats["provider_configuration_cache"] = provider_configuration_cache.get_stats()

    return stats


async def _background_cache_refresh(refresh_interval: int = 21600) -> None:
    """
    Background task to periodically refresh all caches.
    
    This task runs continuously and refreshes caches at the specified interval
    to prevent cache expiration. Defaults to 6 hours (21600 seconds) to refresh
    well before the 24-hour TTL expires.
    
    Args:
        refresh_interval: Interval in seconds between cache refreshes (default: 6 hours)
    """
    global _shutdown_event
    
    logger.info(f"Starting background cache refresh task (interval: {refresh_interval}s)")
    
    # Import here to avoid circular dependency
    from src.database import get_session
    
    while _shutdown_event is not None and not _shutdown_event.is_set():
        try:
            # Wait for the refresh interval or until shutdown
            await asyncio.wait_for(_shutdown_event.wait(), timeout=refresh_interval)
            # If we get here, shutdown was signaled
            break
        except asyncio.TimeoutError:
            # Timeout is expected - time to refresh caches
            pass
        
        # Refresh caches
        try:
            logger.info("Background cache refresh: Starting cache refresh...")
            
            async for session in get_session():
                stats = await warm_all_caches(session)
                logger.info(f"Background cache refresh: Completed successfully - {stats}")
                break  # Only need one session
                
        except Exception as e:
            logger.error(
                f"Background cache refresh: Error refreshing caches: {e}",
                exc_info=True
            )
    
    logger.info("Background cache refresh task stopped")


async def start_background_cache_refresh(refresh_interval: int = 21600) -> None:
    """
    Start the background cache refresh task.
    
    Should be called during application startup. The task will run continuously
    until stop_background_cache_refresh() is called.
    
    Args:
        refresh_interval: Interval in seconds between cache refreshes (default: 6 hours)
    """
    global _background_refresh_task, _shutdown_event
    
    if _background_refresh_task is not None:
        logger.warning("Background cache refresh task is already running")
        return
    
    _shutdown_event = asyncio.Event()
    _background_refresh_task = asyncio.create_task(_background_cache_refresh(refresh_interval))
    logger.info("Background cache refresh task started")


async def stop_background_cache_refresh() -> None:
    """
    Stop the background cache refresh task.
    
    Should be called during application shutdown.
    """
    global _background_refresh_task, _shutdown_event
    
    if _shutdown_event is not None:
        _shutdown_event.set()
    
    if _background_refresh_task is not None:
        try:
            await asyncio.wait_for(_background_refresh_task, timeout=5.0)
            logger.info("Background cache refresh task stopped successfully")
        except asyncio.TimeoutError:
            logger.warning("Background cache refresh task did not stop gracefully, cancelling")
            _background_refresh_task.cancel()
            try:
                await _background_refresh_task
            except asyncio.CancelledError:
                pass
        finally:
            _background_refresh_task = None
            _shutdown_event = None
