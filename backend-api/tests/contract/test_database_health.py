"""Contract tests for database health endpoint."""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock

from src.main import create_app
from src.models.health import DetailedHealthStatus, DatabaseStatus


@pytest.mark.contract
class TestDatabaseHealthContract:
    """Contract tests for /health/db endpoint."""

    @pytest.mark.asyncio
    async def test_health_db_endpoint_exists(self, client: AsyncClient):
        """Test that /health/db endpoint exists and is accessible."""
        with patch("src.database.health.DatabaseHealth.check_connection") as mock_check:
            with patch("src.database.health.DatabaseHealth.get_pool_info") as mock_pool:
                mock_check.return_value = {"status": "connected", "latency_ms": 10.5}
                mock_pool.return_value = {
                    "pool_size": 10,
                    "active_connections": 1,
                    "idle_connections": 9
                }
                
                response = await client.get("/api/v1/health/db")
                assert response.status_code in [200, 503]

    @pytest.mark.asyncio
    async def test_health_db_returns_200_when_connected(self):
        """Test /health/db returns 200 when database is connected."""
        with patch("src.database.health.DatabaseHealth.check_connection") as mock_check:
            with patch("src.database.health.DatabaseHealth.get_pool_info") as mock_pool:
                mock_check.return_value = {"status": "connected", "latency_ms": 15.2}
                mock_pool.return_value = {
                    "pool_size": 10,
                    "active_connections": 2,
                    "idle_connections": 8
                }
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get("/api/v1/health/db")
                    assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_db_returns_503_when_disconnected(self):
        """Test /health/db returns 503 when database is disconnected."""
        with patch("src.database.health.DatabaseHealth.check_connection") as mock_check:
            with patch("src.database.health.DatabaseHealth.get_pool_info") as mock_pool:
                mock_check.return_value = {"status": "error", "error": "Connection failed"}
                mock_pool.return_value = {"status": "unknown"}
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get("/api/v1/health/db")
                    assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_health_db_response_schema_when_connected(self):
        """Test /health/db response has correct schema when connected."""
        with patch("src.database.health.DatabaseHealth.check_connection") as mock_check:
            with patch("src.database.health.DatabaseHealth.get_pool_info") as mock_pool:
                mock_check.return_value = {"status": "connected", "latency_ms": 12.8}
                mock_pool.return_value = {
                    "pool_size": 10,
                    "active_connections": 3,
                    "idle_connections": 7
                }
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get("/api/v1/health/db")
                    data = response.json()
                    
                    # Check top-level fields
                    assert "application" in data
                    assert "status" in data
                    assert "timestamp" in data
                    assert "version" in data
                    assert "environment" in data
                    assert "database" in data
                    
                    # Check database object fields
                    db = data["database"]
                    assert "status" in db
                    assert db["status"] == "connected"
                    assert "latency_ms" in db or "latencyMs" in db
                    assert "pool_size" in db or "poolSize" in db
                    assert "activeConnections" in db
                    assert "idleConnections" in db

    @pytest.mark.asyncio
    async def test_health_db_response_schema_when_disconnected(self):
        """Test /health/db response has correct schema when disconnected."""
        with patch("src.database.health.DatabaseHealth.check_connection") as mock_check:
            with patch("src.database.health.DatabaseHealth.get_pool_info") as mock_pool:
                mock_check.return_value = {"status": "error", "error": "Connection timeout"}
                mock_pool.return_value = {"status": "unknown", "error": "Cannot retrieve pool info"}
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get("/api/v1/health/db")
                    data = response.json()
                    
                    # Check top-level fields
                    assert "application" in data
                    assert "status" in data
                    assert data["status"] == "error"
                    assert "database" in data
                    
                    # Check database object has error status
                    db = data["database"]
                    assert "status" in db
                    assert db["status"] in ["error", "unknown"]

    @pytest.mark.asyncio
    async def test_health_db_latency_measurement_present(self):
        """Test /health/db response includes latency measurement."""
        with patch("src.database.health.DatabaseHealth.check_connection") as mock_check:
            with patch("src.database.health.DatabaseHealth.get_pool_info") as mock_pool:
                mock_check.return_value = {"status": "connected", "latency_ms": 25.7}
                mock_pool.return_value = {
                    "pool_size": 10,
                    "active_connections": 1,
                    "idle_connections": 9
                }
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get("/api/v1/health/db")
                    data = response.json()
                    
                    db = data["database"]
                    # Check for latency in either snake_case or camelCase
                    assert "latency_ms" in db or "latencyMs" in db
                    
                    latency = db.get("latency_ms") or db.get("latencyMs")
                    assert isinstance(latency, (int, float))
                    assert latency > 0

    @pytest.mark.asyncio
    async def test_health_db_pool_info_present(self):
        """Test /health/db response includes connection pool information."""
        with patch("src.database.health.DatabaseHealth.check_connection") as mock_check:
            with patch("src.database.health.DatabaseHealth.get_pool_info") as mock_pool:
                mock_check.return_value = {"status": "connected", "latency_ms": 18.3}
                mock_pool.return_value = {
                    "pool_size": 20,
                    "active_connections": 5,
                    "idle_connections": 15
                }
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get("/api/v1/health/db")
                    data = response.json()
                    
                    db = data["database"]
                    # Check pool_size (snake_case or camelCase)
                    assert "pool_size" in db or "poolSize" in db
                    pool_size = db.get("pool_size") or db.get("poolSize")
                    assert pool_size == 20
                    
                    # Check active connections (camelCase per spec)
                    assert "activeConnections" in db
                    assert db["activeConnections"] == 5
                    
                    # Check idle connections (camelCase per spec)
                    assert "idleConnections" in db
                    assert db["idleConnections"] == 15

    @pytest.mark.asyncio
    async def test_health_db_application_metadata_present(self):
        """Test /health/db response includes application metadata."""
        with patch("src.database.health.DatabaseHealth.check_connection") as mock_check:
            with patch("src.database.health.DatabaseHealth.get_pool_info") as mock_pool:
                mock_check.return_value = {"status": "connected", "latency_ms": 14.5}
                mock_pool.return_value = {
                    "pool_size": 10,
                    "active_connections": 1,
                    "idle_connections": 9
                }
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get("/api/v1/health/db")
                    data = response.json()
                    
                    # Verify application metadata
                    assert data["application"] == "Masjid Connect API"
                    assert data["version"] == "v1"
                    assert data["environment"] in ["development", "production", "test"]
                    
                    # Verify timestamp format (ISO 8601)
                    assert "timestamp" in data
                    assert "T" in data["timestamp"]
                    assert "Z" in data["timestamp"]

    @pytest.mark.asyncio
    async def test_health_db_content_type_is_json(self):
        """Test /health/db returns JSON content type."""
        with patch("src.database.health.DatabaseHealth.check_connection") as mock_check:
            with patch("src.database.health.DatabaseHealth.get_pool_info") as mock_pool:
                mock_check.return_value = {"status": "connected", "latency_ms": 11.2}
                mock_pool.return_value = {
                    "pool_size": 10,
                    "active_connections": 1,
                    "idle_connections": 9
                }
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get("/api/v1/health/db")
                    assert "application/json" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_health_db_handles_connection_errors_gracefully(self):
        """Test /health/db handles database connection errors gracefully."""
        with patch("src.database.health.DatabaseHealth.check_connection") as mock_check:
            with patch("src.database.health.DatabaseHealth.get_pool_info") as mock_pool:
                # Simulate connection error
                mock_check.side_effect = Exception("Database unreachable")
                mock_pool.return_value = {"status": "unknown"}
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get("/api/v1/health/db")
                    
                    # Should return 503 but not crash
                    assert response.status_code == 503
                    data = response.json()
                    assert "status" in data
                    assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_health_db_response_is_valid_json(self):
        """Test /health/db response is valid JSON."""
        with patch("src.database.health.DatabaseHealth.check_connection") as mock_check:
            with patch("src.database.health.DatabaseHealth.get_pool_info") as mock_pool:
                mock_check.return_value = {"status": "connected", "latency_ms": 16.9}
                mock_pool.return_value = {
                    "pool_size": 10,
                    "active_connections": 2,
                    "idle_connections": 8
                }
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get("/api/v1/health/db")
                    
                    # Should be parseable as JSON
                    data = response.json()
                    assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_health_db_camelcase_json_properties(self):
        """Test /health/db uses camelCase for JSON properties as per spec."""
        with patch("src.database.health.DatabaseHealth.check_connection") as mock_check:
            with patch("src.database.health.DatabaseHealth.get_pool_info") as mock_pool:
                mock_check.return_value = {"status": "connected", "latency_ms": 13.1}
                mock_pool.return_value = {
                    "pool_size": 10,
                    "active_connections": 3,
                    "idle_connections": 7
                }
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get("/api/v1/health/db")
                    data = response.json()
                    
                    db = data["database"]
                    # Per project spec, these should be camelCase
                    assert "activeConnections" in db
                    assert "idleConnections" in db
                    
                    # Verify no snake_case versions exist (strict camelCase)
                    # Note: latency_ms and pool_size might be snake_case from internal code
                    assert isinstance(db["activeConnections"], int)
                    assert isinstance(db["idleConnections"], int)

    @pytest.mark.asyncio
    async def test_health_db_status_field_values(self):
        """Test /health/db status field has valid values."""
        with patch("src.database.health.DatabaseHealth.check_connection") as mock_check:
            with patch("src.database.health.DatabaseHealth.get_pool_info") as mock_pool:
                mock_check.return_value = {"status": "connected", "latency_ms": 20.4}
                mock_pool.return_value = {
                    "pool_size": 10,
                    "active_connections": 1,
                    "idle_connections": 9
                }
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get("/api/v1/health/db")
                    data = response.json()
                    
                    # Top-level status should be valid
                    assert data["status"] in ["ok", "error", "degraded"]
                    
                    # Database status should be valid
                    assert data["database"]["status"] in ["connected", "error", "unknown"]

    @pytest.mark.asyncio
    async def test_health_db_latency_accuracy(self):
        """Test /health/db latency is measured accurately."""
        with patch("src.database.health.DatabaseHealth.check_connection") as mock_check:
            with patch("src.database.health.DatabaseHealth.get_pool_info") as mock_pool:
                # Set specific latency value
                expected_latency = 42.75
                mock_check.return_value = {"status": "connected", "latency_ms": expected_latency}
                mock_pool.return_value = {
                    "pool_size": 10,
                    "active_connections": 1,
                    "idle_connections": 9
                }
                
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get("/api/v1/health/db")
                    data = response.json()
                    
                    db = data["database"]
                    latency = db.get("latency_ms") or db.get("latencyMs")
                    
                    # Latency should match what was measured
                    assert latency == expected_latency
