"""
Test script to verify cache refresh functionality.

Run this test to ensure the background cache refresh task works correctly.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.cache_manager import (
    initialize_caches,
    start_background_cache_refresh,
    stop_background_cache_refresh,
    warm_all_caches,
)


@pytest.mark.asyncio
async def test_background_refresh_task_starts_and_stops():
    """Test that the background refresh task starts and stops correctly."""
    # Initialize caches first
    initialize_caches()
    
    # Start the background task
    await start_background_cache_refresh(refresh_interval=1)  # Short interval for testing
    
    # Verify task is running
    from src.core.cache_manager import _background_refresh_task
    assert _background_refresh_task is not None
    assert not _background_refresh_task.done()
    
    # Stop the task
    await stop_background_cache_refresh()
    
    # Verify task stopped
    from src.core.cache_manager import _background_refresh_task
    assert _background_refresh_task is None


@pytest.mark.asyncio
async def test_background_refresh_task_refreshes_caches():
    """Test that the background task actually refreshes caches."""
    # Initialize caches
    initialize_caches()
    
    # Mock the warm_all_caches function to track calls
    with patch('src.core.cache_manager.warm_all_caches', new_callable=AsyncMock) as mock_warm:
        mock_warm.return_value = {
            'company_count': 1,
            'donation_type_count': 2,
            'kiosk_donation_type_count': 3,
            'kiosk_service_type_count': 4,
            'provider_configuration_count': 5,
            'total_count': 15
        }
        
        # Start the background task with short interval
        await start_background_cache_refresh(refresh_interval=2)
        
        # Wait for at least one refresh cycle
        await asyncio.sleep(3)
        
        # Stop the task
        await stop_background_cache_refresh()
        
        # Verify warm_all_caches was called at least once
        assert mock_warm.call_count >= 1


@pytest.mark.asyncio
async def test_background_refresh_handles_errors():
    """Test that the background task handles errors gracefully."""
    # Initialize caches
    initialize_caches()
    
    # Mock warm_all_caches to raise an error
    with patch('src.core.cache_manager.warm_all_caches', new_callable=AsyncMock) as mock_warm:
        mock_warm.side_effect = Exception("Database error")
        
        # Start the background task
        await start_background_cache_refresh(refresh_interval=1)
        
        # Wait for at least one refresh cycle
        await asyncio.sleep(2)
        
        # Verify task is still running despite the error
        from src.core.cache_manager import _background_refresh_task
        assert _background_refresh_task is not None
        assert not _background_refresh_task.done()
        
        # Stop the task
        await stop_background_cache_refresh()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
