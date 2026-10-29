# CLI Scripts Cache Initialization Pattern

## Overview

When creating CLI scripts that interact with the database and use cached data (Company, DonationType, etc.), it's important to initialize the application caches before executing business logic.

## Why Initialize Cache?

CLI scripts run outside the FastAPI application lifecycle, so they don't automatically benefit from the cache initialization that happens during application startup. Without cache initialization:

- Cache lookups will return `None`
- Database queries that depend on cached data may fail
- Performance will be degraded due to repeated database queries
- Provider configuration lookups may fail

## Pattern

### 1. Import Cache Functions

```python
from src.core.cache_manager import initialize_caches, warm_all_caches
from src.database import get_session
```

### 2. Initialize Caches in main()

```python
async def main():
    """Main entry point for the script."""
    # Parse arguments
    args = parse_args()

    try:
        # Initialize caches BEFORE doing any database work
        logger.info("Initializing caches...")
        initialize_caches(
            company_ttl=86400,  # 24 hours
            donation_type_ttl=86400,  # 24 hours
            kiosk_donation_type_ttl=86400,  # 24 hours
            kiosk_service_type_ttl=86400,  # 24 hours
        )
        logger.info("Caches initialized successfully")

        # Warm caches with database data
        logger.info("Warming caches from database...")
        async for session in get_session():
            cache_stats = await warm_all_caches(session)
            logger.info(f"Cache warming completed: {cache_stats}")
            break  # Only need one session for cache warming

        # Now proceed with your script's business logic
        async for session in get_session():
            # Your business logic here
            await do_work(session)
            break

        logger.info("Script completed successfully")

    except Exception as e:
        logger.error(f"Script failed: {str(e)}", exc_info=True)
        sys.exit(1)
```

## Complete Example

Here's a complete example of a CLI script with proper cache initialization:

```python
"""
Example CLI Script with Cache Initialization

Usage:
    python -m src.scripts.example_script --company-id 10001
"""

import argparse
import asyncio
import sys

from src.config import settings
from src.core.logging import get_logger
from src.core.cache_manager import initialize_caches, warm_all_caches
from src.database import get_session

logger = get_logger(__name__, level=settings.LOG_LEVEL)


async def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Example CLI script")
    parser.add_argument("--company-id", type=int, required=True)
    args = parser.parse_args()

    logger.info("Starting example script")
    logger.info(f"Company ID: {args.company_id}")

    try:
        # Step 1: Initialize caches
        logger.info("Initializing caches...")
        initialize_caches(
            company_ttl=86400,
            donation_type_ttl=86400,
            kiosk_donation_type_ttl=86400,
            kiosk_service_type_ttl=86400,
        )
        logger.info("Caches initialized successfully")

        # Step 2: Warm caches from database
        logger.info("Warming caches from database...")
        async for session in get_session():
            cache_stats = await warm_all_caches(session)
            logger.info(f"Cache warming completed: {cache_stats}")
            break

        # Step 3: Execute business logic
        async for session in get_session():
            # Your code that uses cached data
            from src.core.cache_manager import company_cache

            company = await company_cache.get(args.company_id)
            if company:
                logger.info(f"Found company: {company.CompanyName}")
            else:
                logger.error(f"Company {args.company_id} not found")
                sys.exit(1)

            # More business logic here...

            break

        logger.info("Script completed successfully")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Script failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
```

## Cache TTL Configuration

The default TTL (Time To Live) is 24 hours (86400 seconds). You can adjust based on your script's needs:

```python
initialize_caches(
    company_ttl=3600,        # 1 hour
    donation_type_ttl=7200,  # 2 hours
    kiosk_donation_type_ttl=86400,  # 24 hours
    kiosk_service_type_ttl=86400,   # 24 hours
)
```

## When to Skip Cache Warming

For scripts that:

- Only create/update data (don't read cached data)
- Run very frequently and caching overhead isn't beneficial
- Have strict performance requirements

You can initialize without warming:

```python
# Initialize empty caches
initialize_caches()
logger.info("Caches initialized (not warmed)")

# Caches will be populated on-demand as data is accessed
```

## Checklist for New CLI Scripts

- [ ] Import `initialize_caches` and `warm_all_caches`
- [ ] Call `initialize_caches()` at start of `main()`
- [ ] Call `warm_all_caches()` after initialization
- [ ] Add appropriate logging for cache initialization steps
- [ ] Test script to verify cached data is accessible

## References

- **Cache Manager**: `src/core/cache_manager.py`
- **Cache Implementation**: `docs/CACHE_IMPLEMENTATION.md`
- **Main Application**: `src/main.py` (see startup lifespan)
- **Example Script**: `src/scripts/sync_stripe_subscriptions.py`

## Common Issues

### "Cache not initialized" Error

**Cause**: Attempting to access cache before calling `initialize_caches()`

**Solution**: Move `initialize_caches()` call to the beginning of `main()`

### Cache Returns None Despite Data in Database

**Cause**: Caches were initialized but not warmed from database

**Solution**: Call `warm_all_caches()` after initialization

### Script Performance Issues

**Cause**: Cache warming may add startup time for large datasets

**Solution**:

- Skip warming for write-only scripts
- Use smaller TTL values if data changes frequently
- Consider caching only specific entities your script needs
