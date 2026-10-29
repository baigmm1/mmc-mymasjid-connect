"""Tests for database engine and session factory."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from src.database.engine import DatabaseEngine
from src.database.session import SessionFactory


class TestDatabaseEngine:
    """Tests for DatabaseEngine factory."""

    @pytest.mark.asyncio
    async def test_create_engine_with_default_settings(self):
        """Test engine creation with default settings."""
        conn_str = "Server=tcp:localhost;Database=test;uid=sa;pwd=pass"

        with patch("src.database.engine.create_async_engine") as mock_create:
            mock_engine = MagicMock(spec=AsyncEngine)
            mock_create.return_value = mock_engine

            engine_factory = DatabaseEngine(conn_str)
            engine = await engine_factory.create_engine()

            assert engine == mock_engine
            mock_create.assert_called_once()
            call_args = mock_create.call_args

            # Verify connection string format (aioodbc for async operations)
            assert "mssql+aioodbc:///?odbc_connect=" in call_args[0][0]
            assert call_args[1]["echo"] is False
            assert call_args[1]["pool_size"] == 10
            assert call_args[1]["max_overflow"] == 10
            assert call_args[1]["pool_recycle"] == 300
            assert call_args[1]["pool_pre_ping"] is True

    @pytest.mark.asyncio
    async def test_create_engine_with_custom_settings(self):
        """Test engine creation with custom settings."""
        conn_str = "Server=tcp:localhost;Database=test;uid=sa;pwd=pass"

        with patch("src.database.engine.create_async_engine") as mock_create:
            mock_engine = MagicMock(spec=AsyncEngine)
            mock_create.return_value = mock_engine

            engine_factory = DatabaseEngine(
                conn_str,
                echo=True,
                pool_size=20,
                max_overflow=15,
                pool_recycle=600,
                connect_timeout=60,
            )
            engine = await engine_factory.create_engine()

            assert engine == mock_engine
            call_args = mock_create.call_args
            assert call_args[1]["echo"] is True
            assert call_args[1]["pool_size"] == 20
            assert call_args[1]["max_overflow"] == 15
            assert call_args[1]["pool_recycle"] == 600
            assert call_args[1]["connect_args"]["timeout"] == 60

    def test_init_stores_configuration(self):
        """Test that __init__ stores all configuration."""
        conn_str = "Server=tcp:localhost;Database=test"
        engine_factory = DatabaseEngine(
            conn_str,
            echo=True,
            pool_size=15,
            max_overflow=5,
            pool_recycle=400,
            connect_timeout=45,
        )

        assert engine_factory.connection_string == conn_str
        assert engine_factory.echo is True
        assert engine_factory.pool_size == 15
        assert engine_factory.max_overflow == 5
        assert engine_factory.pool_recycle == 400
        assert engine_factory.connect_timeout == 45


class TestSessionFactory:
    """Tests for SessionFactory."""

    def test_init_creates_session_maker(self):
        """Test that __init__ creates async_sessionmaker."""
        mock_engine = MagicMock(spec=AsyncEngine)
        factory = SessionFactory(mock_engine)

        assert factory.engine == mock_engine
        assert factory.async_session is not None

    @pytest.mark.asyncio
    async def test_get_session_yields_session(self):
        """Test that get_session yields AsyncSession."""
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock the context manager properly
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.close = AsyncMock()

        # Create a mock session maker that returns the mocked session
        mock_session_maker = MagicMock()
        mock_session_maker.return_value = mock_session

        with patch(
            "src.database.session.async_sessionmaker",
            return_value=mock_session_maker,
        ):
            factory = SessionFactory(mock_engine)

            async for session in factory.get_session():
                assert session == mock_session
                break  # Only test one iteration

    @pytest.mark.asyncio
    async def test_get_session_handles_lifecycle(self):
        """Test that get_session properly manages session lifecycle."""
        mock_engine = MagicMock(spec=AsyncEngine)
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock the context manager properly
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        # Create a mock session maker
        mock_session_maker = MagicMock()
        mock_session_maker.return_value = mock_session

        with patch(
            "src.database.session.async_sessionmaker",
            return_value=mock_session_maker,
        ):
            factory = SessionFactory(mock_engine)

            # Test that session is yielded correctly and generator works
            session_count = 0
            async for session in factory.get_session():
                assert session == mock_session
                session_count += 1
                break  # Exit after first yield
            
            # Verify session was yielded
            assert session_count == 1, "Session should be yielded exactly once"

    @pytest.mark.asyncio
    async def test_close_disposes_engine(self):
        """Test that close disposes the engine."""
        mock_engine = AsyncMock(spec=AsyncEngine)
        mock_engine.dispose = AsyncMock()

        factory = SessionFactory(mock_engine)
        await factory.close()

        mock_engine.dispose.assert_called_once()
