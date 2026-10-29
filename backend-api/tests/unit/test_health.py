"""
Unit tests for health endpoint handler.

Tests verify the health endpoint logic in isolation,
without running the full FastAPI application.

Test markers:
- @pytest.mark.unit: Unit test (isolated component testing)
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.api.v1.endpoints.health import get_health
from src.config import settings
from src.models.health import HealthStatus


@pytest.mark.unit
class TestHealthEndpointHandler:
    """Unit tests for health endpoint handler."""

    @pytest.mark.asyncio
    async def test_get_health_returns_health_status_model(self):
        """Test that get_health returns HealthStatus model instance."""
        result = await get_health()

        assert isinstance(result, HealthStatus)

    @pytest.mark.asyncio
    async def test_get_health_status_is_ok(self):
        """Test that get_health always returns ok status."""
        result = await get_health()

        assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_get_health_includes_timestamp(self):
        """Test that get_health includes current timestamp."""
        from datetime import timezone
        before = datetime.now(timezone.utc)
        result = await get_health()
        after = datetime.now(timezone.utc)

        assert result.timestamp is not None
        assert before <= result.timestamp <= after

    @pytest.mark.asyncio
    async def test_get_health_includes_version(self):
        """Test that get_health includes API version from settings."""
        result = await get_health()

        assert result.version == settings.API_VERSION

    @pytest.mark.asyncio
    async def test_get_health_includes_environment(self):
        """Test that get_health includes environment from settings."""
        result = await get_health()

        assert result.environment == settings.ENVIRONMENT

    @pytest.mark.asyncio
    async def test_get_health_model_validation(self):
        """Test that returned model passes Pydantic validation."""
        result = await get_health()

        # Pydantic validation happens on model creation
        # If it didn't pass, the creation would have raised ValidationError
        assert result.model_validate(result.model_dump()) == result

    @pytest.mark.asyncio
    async def test_get_health_serializes_to_json(self):
        """Test that health status can be serialized to JSON."""
        result = await get_health()

        json_data = result.model_dump_json()
        assert isinstance(json_data, str)
        assert "status" in json_data
        assert "timestamp" in json_data

    @pytest.mark.asyncio
    async def test_get_health_with_different_environments(self):
        """Test get_health reflects different environment settings."""
        original_env = settings.ENVIRONMENT

        try:
            # Test with different environment values
            with patch.object(settings, "ENVIRONMENT", "testing"):
                result = await get_health()
                assert result.environment == "testing"

            with patch.object(settings, "ENVIRONMENT", "production"):
                result = await get_health()
                assert result.environment == "production"
        finally:
            # Restore original
            settings.ENVIRONMENT = original_env

    @pytest.mark.asyncio
    async def test_get_health_timestamp_is_recent(self):
        """Test that timestamp is within reasonable range (not cached)."""
        import time

        result1 = await get_health()
        time.sleep(0.1)  # Sleep 100ms
        result2 = await get_health()

        # Timestamps should be different (not cached)
        assert result2.timestamp > result1.timestamp

        # But very close (within 1 second)
        delta = (result2.timestamp - result1.timestamp).total_seconds()
        assert 0.05 < delta < 1.0
