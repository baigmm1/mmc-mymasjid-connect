"""
Unit tests for cache implementation.

Tests the CacheDict class and cache manager functionality.
"""

import asyncio
from datetime import datetime, timedelta

import pytest

from src.core.cache import CacheDict


@pytest.mark.asyncio
async def test_cache_set_and_get():
    """Test basic cache set and get operations."""
    cache = CacheDict[str](ttl_seconds=60, name="TestCache")

    # Set a value
    await cache.set("key1", "value1")

    # Get the value
    value = await cache.get("key1")
    assert value == "value1"


@pytest.mark.asyncio
async def test_cache_miss():
    """Test cache miss returns None."""
    cache = CacheDict[str](ttl_seconds=60, name="TestCache")

    # Get non-existent key
    value = await cache.get("nonexistent")
    assert value is None


@pytest.mark.asyncio
async def test_cache_expiration():
    """Test cache item expiration."""
    cache = CacheDict[str](ttl_seconds=1, name="TestCache")

    # Set a value with 1 second TTL
    await cache.set("key1", "value1")

    # Immediately get should work
    value = await cache.get("key1")
    assert value == "value1"

    # Wait for expiration
    await asyncio.sleep(1.1)

    # Should be expired now
    value = await cache.get("key1")
    assert value is None


@pytest.mark.asyncio
async def test_cache_delete():
    """Test cache item deletion."""
    cache = CacheDict[str](ttl_seconds=60, name="TestCache")

    # Set a value
    await cache.set("key1", "value1")
    assert await cache.get("key1") == "value1"

    # Delete the value
    deleted = await cache.delete("key1")
    assert deleted is True

    # Should be gone now
    value = await cache.get("key1")
    assert value is None

    # Delete non-existent key
    deleted = await cache.delete("key1")
    assert deleted is False


@pytest.mark.asyncio
async def test_cache_clear():
    """Test clearing all cache items."""
    cache = CacheDict[str](ttl_seconds=60, name="TestCache")

    # Set multiple values
    await cache.set("key1", "value1")
    await cache.set("key2", "value2")
    await cache.set("key3", "value3")

    # Clear all
    count = await cache.clear()
    assert count == 3

    # All should be gone
    assert await cache.get("key1") is None
    assert await cache.get("key2") is None
    assert await cache.get("key3") is None


@pytest.mark.asyncio
async def test_cache_get_all():
    """Test getting all cache items."""
    cache = CacheDict[str](ttl_seconds=60, name="TestCache")

    # Set multiple values
    await cache.set("key1", "value1")
    await cache.set("key2", "value2")
    await cache.set("key3", "value3")

    # Get all
    all_items = await cache.get_all()
    assert len(all_items) == 3
    assert all_items["key1"] == "value1"
    assert all_items["key2"] == "value2"
    assert all_items["key3"] == "value3"


@pytest.mark.asyncio
async def test_cache_size():
    """Test getting cache size."""
    cache = CacheDict[str](ttl_seconds=60, name="TestCache")

    # Initial size
    size = await cache.size()
    assert size == 0

    # Add items
    await cache.set("key1", "value1")
    await cache.set("key2", "value2")

    size = await cache.size()
    assert size == 2


@pytest.mark.asyncio
async def test_cache_cleanup_expired():
    """Test cleaning up expired items."""
    cache = CacheDict[str](ttl_seconds=1, name="TestCache")

    # Add items
    await cache.set("key1", "value1")
    await cache.set("key2", "value2")

    # Wait for expiration
    await asyncio.sleep(1.1)

    # Add new item (should not expire)
    await cache.set("key3", "value3")

    # Cleanup expired
    count = await cache.cleanup_expired()
    assert count == 2

    # Only key3 should remain
    assert await cache.get("key1") is None
    assert await cache.get("key2") is None
    assert await cache.get("key3") == "value3"


@pytest.mark.asyncio
async def test_cache_refresh_on_access():
    """Test TTL refresh on access."""
    cache = CacheDict[str](ttl_seconds=2, refresh_on_access=True, name="TestCache")

    # Set a value
    await cache.set("key1", "value1")

    # Access after 1 second (should refresh TTL)
    await asyncio.sleep(1)
    value = await cache.get("key1")
    assert value == "value1"

    # Access after another 1 second (total 2 seconds, but refreshed at 1)
    await asyncio.sleep(1)
    value = await cache.get("key1")
    assert value == "value1"  # Should still be valid due to refresh


@pytest.mark.asyncio
async def test_cache_get_or_load():
    """Test get_or_load functionality."""
    cache = CacheDict[str](ttl_seconds=60, name="TestCache")

    # Mock loader function
    async def loader(key):
        return f"loaded_{key}"

    # First call should load
    value = await cache.get_or_load("key1", loader)
    assert value == "loaded_key1"

    # Second call should get from cache
    value = await cache.get_or_load("key1", loader)
    assert value == "loaded_key1"

    # Verify it's actually cached
    size = await cache.size()
    assert size == 1


@pytest.mark.asyncio
async def test_cache_load_all_with_extractor():
    """Test loading multiple items with key extractor."""
    cache = CacheDict[dict](ttl_seconds=60, name="TestCache")

    # Mock data
    items = [
        {"id": 1, "name": "Item 1"},
        {"id": 2, "name": "Item 2"},
        {"id": 3, "name": "Item 3"},
    ]

    # Load with key extractor
    count = await cache.load_all(
        loader=lambda: items,
        key_extractor=lambda item: item["id"]
    )
    assert count == 3

    # Verify items are cached
    item1 = await cache.get(1)
    assert item1["name"] == "Item 1"

    item2 = await cache.get(2)
    assert item2["name"] == "Item 2"


@pytest.mark.asyncio
async def test_cache_load_all_with_tuples():
    """Test loading multiple items with (key, value) tuples."""
    cache = CacheDict[str](ttl_seconds=60, name="TestCache")

    # Mock data as tuples
    items = [
        ("key1", "value1"),
        ("key2", "value2"),
        ("key3", "value3"),
    ]

    # Load without key extractor
    count = await cache.load_all(loader=lambda: items)
    assert count == 3

    # Verify items are cached
    assert await cache.get("key1") == "value1"
    assert await cache.get("key2") == "value2"
    assert await cache.get("key3") == "value3"


@pytest.mark.asyncio
async def test_cache_stats():
    """Test cache statistics."""
    cache = CacheDict[str](ttl_seconds=1, name="TestCache")

    # Add items
    await cache.set("key1", "value1")
    await cache.set("key2", "value2")

    # Get stats immediately
    stats = cache.get_stats()
    assert stats["name"] == "TestCache"
    assert stats["total_items"] == 2
    assert stats["active_items"] == 2
    assert stats["expired_items"] == 0
    assert stats["ttl_seconds"] == 1

    # Wait for expiration
    await asyncio.sleep(1.1)

    # Get stats after expiration
    stats = cache.get_stats()
    assert stats["total_items"] == 2
    assert stats["active_items"] == 0
    assert stats["expired_items"] == 2


@pytest.mark.asyncio
async def test_cache_composite_key():
    """Test cache with composite (tuple) keys."""
    cache = CacheDict[str](ttl_seconds=60, name="TestCache")

    # Set values with composite keys
    await cache.set((1, 10), "value_1_10")
    await cache.set((1, 20), "value_1_20")
    await cache.set((2, 10), "value_2_10")

    # Get values
    assert await cache.get((1, 10)) == "value_1_10"
    assert await cache.get((1, 20)) == "value_1_20"
    assert await cache.get((2, 10)) == "value_2_10"
    assert await cache.get((1, 30)) is None


@pytest.mark.asyncio
async def test_cache_type_safety():
    """Test cache with different types."""
    # String cache
    str_cache = CacheDict[str](ttl_seconds=60, name="StringCache")
    await str_cache.set("key", "value")
    assert await str_cache.get("key") == "value"

    # Integer cache
    int_cache = CacheDict[int](ttl_seconds=60, name="IntCache")
    await int_cache.set("key", 123)
    assert await int_cache.get("key") == 123

    # Dictionary cache
    dict_cache = CacheDict[dict](ttl_seconds=60, name="DictCache")
    await dict_cache.set("key", {"id": 1, "name": "Test"})
    result = await dict_cache.get("key")
    assert result["id"] == 1
    assert result["name"] == "Test"
