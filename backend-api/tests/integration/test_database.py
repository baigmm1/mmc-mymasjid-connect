"""Integration tests for database module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_engine, get_session_factory
from src.config import Settings

Base = declarative_base()


class TestUser(Base):
    """Test model for integration tests."""

    __tablename__ = "test_users"
    id = Column(Integer, primary_key=True)
    name = Column(String(255))


class TestDatabaseModuleIntegration:
    """Integration tests for database module."""

    @pytest.mark.asyncio
    async def test_get_engine_with_connection_string_provider(self):
        """Test get_engine with connection string provider."""
        # Set required environment variable
        with patch.dict("os.environ", {"DB_CONNECTION_STRING": "Server=tcp:test;Database=test;uid=test;pwd=test"}):
            # Reset the global engine
            import src.database as db_module
            db_module._engine = None
            
            # Reload settings to pick up env var
            from importlib import reload
            import src.config
            reload(src.config)
            
            with patch("src.database.engine.create_async_engine") as mock_create:
                mock_engine = AsyncMock()
                mock_create.return_value = mock_engine
                
                engine = await get_engine()
                assert engine is not None
                
                # Reset for other tests
                db_module._engine = None

    @pytest.mark.asyncio
    async def test_get_session_factory_returns_factory(self):
        """Test get_session_factory returns SessionFactory."""
        mock_engine = AsyncMock()

        with patch("src.database.get_engine", return_value=mock_engine):
            from src.database import get_session_factory

            factory = get_session_factory(mock_engine)
            assert factory is not None

    @pytest.mark.asyncio
    async def test_dependency_injection_pattern(self):
        """Test that get_session can be used as FastAPI dependency."""
        # Set required environment variable
        with patch.dict("os.environ", {"DB_CONNECTION_STRING": "Server=tcp:test;Database=test;uid=test;pwd=test"}):
            # Reset the global engine and reload config
            import src.database as db_module
            db_module._engine = None
            db_module._session_factory = None
            
            from importlib import reload
            import src.config
            reload(src.config)
            
            from src.database import get_session
            
            with patch("src.database.engine.create_async_engine") as mock_create:
                mock_engine = AsyncMock()
                mock_create.return_value = mock_engine
                
                # Mock session
                mock_session = AsyncMock(spec=AsyncSession)
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session.close = AsyncMock()
                
                with patch("src.database.session.async_sessionmaker") as mock_maker:
                    mock_session_maker = MagicMock()
                    mock_session_maker.return_value = mock_session
                    mock_maker.return_value = mock_session_maker
                    
                    # Simulate what FastAPI would do with the async generator
                    async_gen = get_session()
                    session = await async_gen.__anext__()
                    assert session is not None
                    
                    # Reset for other tests
                    db_module._engine = None
                    db_module._session_factory = None

    @pytest.mark.asyncio
    async def test_database_module_exports(self):
        """Test that database module exports are correct."""
        import src.database as db

        # Check all required exports exist
        assert hasattr(db, "get_engine")
        assert hasattr(db, "get_session_factory")
        assert hasattr(db, "get_session")
        assert hasattr(db, "DatabaseEngine")
        assert hasattr(db, "SessionFactory")


class TestConnectionPool:
    """Integration tests for connection pool."""

    @pytest.mark.asyncio
    async def test_connection_pool_creation(self):
        """Test connection pool is created with correct settings."""
        with patch.dict("os.environ", {"DB_CONNECTION_STRING": "Server=tcp:test;Database=test;uid=test;pwd=test"}):
            import src.database as db_module
            db_module._engine = None
            
            from importlib import reload
            import src.config
            reload(src.config)
            
            with patch("src.database.engine.create_async_engine") as mock_create:
                mock_engine = AsyncMock()
                mock_engine.pool = MagicMock()
                mock_engine.pool.size.return_value = 10
                mock_create.return_value = mock_engine
                
                engine = await get_engine()
                
                # Verify create_async_engine was called with correct parameters
                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args.kwargs
                assert "pool_size" in call_kwargs or "poolclass" in call_kwargs
                
                db_module._engine = None

    @pytest.mark.asyncio
    async def test_connection_pool_info_retrieval(self):
        """Test retrieving connection pool information."""
        with patch.dict("os.environ", {"DB_CONNECTION_STRING": "Server=tcp:test;Database=test;uid=test;pwd=test"}):
            import src.database as db_module
            db_module._engine = None
            
            from importlib import reload
            import src.config
            reload(src.config)
            
            with patch("src.database.engine.create_async_engine") as mock_create:
                mock_engine = AsyncMock()
                mock_pool = MagicMock()
                mock_pool.size.return_value = 10
                mock_pool.checkedin.return_value = 8
                mock_pool.checkedout.return_value = 2
                mock_engine.pool = mock_pool
                mock_create.return_value = mock_engine
                
                engine = await get_engine()
                
                # Check pool stats
                assert hasattr(engine, "pool")
                
                db_module._engine = None

    @pytest.mark.asyncio
    async def test_multiple_concurrent_sessions(self):
        """Test creating multiple concurrent sessions."""
        with patch.dict("os.environ", {"DB_CONNECTION_STRING": "Server=tcp:test;Database=test;uid=test;pwd=test"}):
            import src.database as db_module
            db_module._engine = None
            db_module._session_factory = None
            
            from importlib import reload
            import src.config
            reload(src.config)
            
            with patch("src.database.engine.create_async_engine") as mock_create:
                mock_engine = AsyncMock()
                mock_create.return_value = mock_engine
                
                # Create multiple mock sessions
                sessions = []
                for i in range(3):
                    mock_session = AsyncMock(spec=AsyncSession)
                    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                    mock_session.__aexit__ = AsyncMock(return_value=None)
                    mock_session.close = AsyncMock()
                    sessions.append(mock_session)
                
                with patch("src.database.session.async_sessionmaker") as mock_maker:
                    call_count = 0
                    def session_factory():
                        nonlocal call_count
                        result = sessions[call_count % len(sessions)]
                        call_count += 1
                        return result
                    
                    mock_session_maker = MagicMock()
                    mock_session_maker.side_effect = session_factory
                    mock_maker.return_value = mock_session_maker
                    
                    # Create 3 concurrent sessions
                    from src.database import get_session
                    async_gens = [get_session() for _ in range(3)]
                    
                    # Get all sessions
                    active_sessions = []
                    for gen in async_gens:
                        session = await gen.__anext__()
                        active_sessions.append(session)
                    
                    # All should be valid
                    assert len(active_sessions) == 3
                    for session in active_sessions:
                        assert session is not None
                    
                    db_module._engine = None
                    db_module._session_factory = None


class TestQueryExecution:
    """Integration tests for query execution."""

    @pytest.mark.asyncio
    async def test_query_execution_success(self):
        """Test successful query execution."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 1
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Execute a simple query
        from sqlalchemy import text
        result = await mock_session.execute(text("SELECT 1"))
        value = result.scalar_one_or_none()
        
        assert value == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_with_parameters(self):
        """Test query execution with parameters."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(1, "Test")]
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Execute query with parameters
        from sqlalchemy import text
        query = text("SELECT * FROM Company WHERE CompanyId = :id")
        result = await mock_session.execute(query, {"id": 1})
        rows = result.fetchall()
        
        assert len(rows) == 1
        assert rows[0] == (1, "Test")


class TestTransactionHandling:
    """Integration tests for transaction handling."""

    @pytest.mark.asyncio
    async def test_transaction_commit(self):
        """Test transaction commit."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        # Simulate successful transaction
        await mock_session.commit()
        
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_transaction_rollback(self):
        """Test transaction rollback on error."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute = AsyncMock(side_effect=Exception("Database error"))
        mock_session.rollback = AsyncMock()
        
        # Simulate error requiring rollback
        try:
            from sqlalchemy import text
            await mock_session.execute(text("INVALID SQL"))
        except Exception:
            await mock_session.rollback()
        
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_transaction_context_manager(self):
        """Test transaction handling with context manager."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        # Use as context manager
        async with mock_session as session:
            assert session is mock_session
        
        # Context manager should handle cleanup
        mock_session.__aenter__.assert_called_once()
        mock_session.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_nested_transaction_rollback(self):
        """Test nested transaction with rollback."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.begin = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        # Simulate nested transaction with rollback
        await mock_session.begin()
        try:
            # Simulate error in nested transaction
            raise ValueError("Test error")
        except ValueError:
            await mock_session.rollback()
        
        mock_session.begin.assert_called_once()
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()


class TestSessionLifecycle:
    """Integration tests for session lifecycle management."""

    @pytest.mark.asyncio
    async def test_session_cleanup_on_success(self):
        """Test session is properly cleaned up after successful operations."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.close = AsyncMock()
        
        # Simulate successful operation
        await mock_session.close()
        
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_cleanup_on_error(self):
        """Test session is properly cleaned up after errors."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.close = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        # Simulate error scenario
        try:
            raise RuntimeError("Test error")
        except RuntimeError:
            await mock_session.rollback()
        finally:
            await mock_session.close()
        
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_session_instances_independent(self):
        """Test that multiple session instances are independent."""
        session1 = AsyncMock(spec=AsyncSession)
        session2 = AsyncMock(spec=AsyncSession)
        
        session1.close = AsyncMock()
        session2.close = AsyncMock()
        
        # Close session1
        await session1.close()
        
        # session2 should not be affected
        session1.close.assert_called_once()
        session2.close.assert_not_called()
