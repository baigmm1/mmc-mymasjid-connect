"""
In-memory cache management for application data.

Provides a flexible caching mechanism with TTL support and type safety
for caching database query results and other frequently accessed data.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Generic, Optional, TypeVar

from src.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class CacheDict(Generic[T]):
    """
    Generic in-memory cache with TTL (time-to-live) support.

    Provides thread-safe caching with automatic expiration and refresh capabilities.
    Suitable for caching database query results and other frequently accessed data.

    Type Parameters:
        T: Type of values stored in the cache

    Attributes:
        ttl_seconds: Time-to-live for cached items in seconds
        refresh_on_access: Whether to refresh TTL on each access
        name: Cache instance name for logging purposes

    Example:
        # Create a cache for Company objects with 5-minute TTL
        company_cache = CacheDict[Company](
            ttl_seconds=300,
            name="CompanyCache"
        )

        # Store item
        await company_cache.set(1, company_obj)

        # Retrieve item
        company = await company_cache.get(1)

        # Bulk load with loader function
        await company_cache.load_all(loader_func)
    """

    def __init__(
        self,
        ttl_seconds: int = 300,  # Default 5 minutes
        refresh_on_access: bool = False,
        name: str = "Cache",
    ):
        """
        Initialize cache instance.

        Args:
            ttl_seconds: Time-to-live for cached items (default: 300 seconds)
            refresh_on_access: If True, reset TTL on each access (default: False)
            name: Cache name for logging and identification (default: "Cache")
        """
        self._cache: Dict[Any, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self.ttl_seconds = ttl_seconds
        self.refresh_on_access = refresh_on_access
        self.name = name
        logger.info(
            f"Initialized {self.name} with TTL={ttl_seconds}s, refresh_on_access={refresh_on_access}"
        )

    async def get(self, key: Any) -> Optional[T]:
        """
        Retrieve item from cache.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached value if exists and not expired, None otherwise
        """
        async with self._lock:
            if key not in self._cache:
                logger.debug(f"{self.name}: Cache miss for key={key}")
                return None

            entry = self._cache[key]
            expires_at = entry["expires_at"]

            # Check if expired
            if datetime.now() >= expires_at:
                logger.debug(f"{self.name}: Expired entry for key={key}")
                del self._cache[key]
                return None

            # Refresh TTL if configured
            if self.refresh_on_access:
                entry["expires_at"] = datetime.now() + timedelta(seconds=self.ttl_seconds)
                logger.debug(f"{self.name}: Refreshed TTL for key={key}")

            logger.debug(f"{self.name}: Cache hit for key={key}")
            return entry["value"]

    async def set(self, key: Any, value: T) -> None:
        """
        Store item in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
        """
        async with self._lock:
            expires_at = datetime.now() + timedelta(seconds=self.ttl_seconds)
            self._cache[key] = {
                "value": value,
                "expires_at": expires_at,
                "created_at": datetime.now(),
            }
            logger.debug(
                f"{self.name}: Cached key={key}, expires at {expires_at.isoformat()}"
            )

    async def delete(self, key: Any) -> bool:
        """
        Remove item from cache.

        Args:
            key: Cache key to remove

        Returns:
            True if item was deleted, False if key didn't exist
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"{self.name}: Deleted key={key}")
                return True
            return False

    async def clear(self) -> int:
        """
        Clear all items from cache.

        Returns:
            Number of items that were cleared
        """
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"{self.name}: Cleared {count} items from cache")
            return count

    async def get_all(self) -> Dict[Any, T]:
        """
        Get all non-expired items from cache.

        Returns:
            Dictionary of all valid cached items
        """
        async with self._lock:
            now = datetime.now()
            valid_items = {}
            expired_keys = []

            for key, entry in self._cache.items():
                if now >= entry["expires_at"]:
                    expired_keys.append(key)
                else:
                    valid_items[key] = entry["value"]

            # Clean up expired entries
            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.debug(
                    f"{self.name}: Removed {len(expired_keys)} expired entries during get_all"
                )

            return valid_items

    async def size(self) -> int:
        """
        Get current cache size (including expired items).

        Returns:
            Number of items currently in cache
        """
        async with self._lock:
            return len(self._cache)

    async def cleanup_expired(self) -> int:
        """
        Remove all expired items from cache.

        Returns:
            Number of expired items removed
        """
        async with self._lock:
            now = datetime.now()
            expired_keys = [
                key
                for key, entry in self._cache.items()
                if now >= entry["expires_at"]
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.info(
                    f"{self.name}: Cleaned up {len(expired_keys)} expired entries"
                )

            return len(expired_keys)

    async def load_all(
        self,
        loader: Callable[[], Any],
        key_extractor: Optional[Callable[[T], Any]] = None,
    ) -> int:
        """
        Load multiple items into cache using a loader function.

        Useful for pre-populating cache from database queries.

        Args:
            loader: Async or sync function that returns iterable of items
            key_extractor: Function to extract cache key from item.
                          If None, items are assumed to be (key, value) tuples.

        Returns:
            Number of items loaded into cache

        Example:
            # With key extractor
            await cache.load_all(
                loader=lambda: session.execute(select(Company)).scalars().all(),
                key_extractor=lambda c: c.CompanyId
            )

            # With (key, value) tuples
            await cache.load_all(
                loader=lambda: [(1, obj1), (2, obj2)]
            )
        """
        try:
            # Execute loader (handle both async and sync)
            if asyncio.iscoroutinefunction(loader):
                items = await loader()
            else:
                items = loader()

            count = 0
            if key_extractor:
                # Extract key from each item
                for item in items:
                    key = key_extractor(item)
                    await self.set(key, item)
                    count += 1
            else:
                # Assume items are (key, value) tuples
                for key, value in items:
                    await self.set(key, value)
                    count += 1

            logger.info(f"{self.name}: Loaded {count} items into cache")
            return count

        except Exception as e:
            logger.error(f"{self.name}: Error loading items into cache: {e}")
            raise

    async def get_or_load(
        self,
        key: Any,
        loader: Callable[[Any], Any],
    ) -> Optional[T]:
        """
        Get item from cache or load it using loader function if not cached.

        Args:
            key: Cache key
            loader: Async or sync function that takes key and returns value

        Returns:
            Cached or newly loaded value

        Example:
            company = await cache.get_or_load(
                key=1,
                loader=lambda k: session.get(Company, k)
            )
        """
        # Try to get from cache first
        value = await self.get(key)
        if value is not None:
            return value

        # Load from source
        try:
            if asyncio.iscoroutinefunction(loader):
                value = await loader(key)
            else:
                value = loader(key)

            if value is not None:
                await self.set(key, value)

            return value

        except Exception as e:
            logger.error(f"{self.name}: Error loading value for key={key}: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        now = datetime.now()
        total = len(self._cache)
        expired = sum(
            1 for entry in self._cache.values() if now >= entry["expires_at"]
        )
        active = total - expired

        return {
            "name": self.name,
            "total_items": total,
            "active_items": active,
            "expired_items": expired,
            "ttl_seconds": self.ttl_seconds,
            "refresh_on_access": self.refresh_on_access,
        }
