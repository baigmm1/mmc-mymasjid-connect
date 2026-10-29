"""Database initialization and migration guide."""

import sys
from pathlib import Path

# Add the backend-api directory to the path
backend_api_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_api_path))

try:
    from alembic import command
    from alembic.config import Config
except ImportError:
    Config = None
    command = None

from sqlalchemy import inspect


async def initialize_database():
    """Initialize the database with all tables.
    
    This function will:
    1. Create the database engine
    2. Create all tables from the models
    3. Set up any initial data
    
    Usage:
        python -c "
        import asyncio
        from src.database.migrations import initialize_database
        asyncio.run(initialize_database())
        "
    """
    from src.database import get_engine
    from src.database.models import Base
    
    engine = await get_engine()
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("✓ Database initialization complete")


async def verify_database_connection():
    """Verify that the database connection works.
    
    Returns:
        bool: True if connection is successful, False otherwise.
    """
    from src.database import get_engine
    
    try:
        engine = await get_engine()
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        print("✓ Database connection verified")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def create_migration(message: str):
    """Create a new Alembic migration.
    
    Args:
        message: The migration message/description.
        
    Usage:
        python -c "
        from src.database.migrations import create_migration
        create_migration('add_users_table')
        "
    """
    if Config is None:
        print("✗ Alembic not installed. Run: pip install alembic")
        return
    
    config = Config("alembic.ini")
    command.revision(config, autogenerate=True, message=message)
    print(f"✓ Migration '{message}' created")


def upgrade_database(revision: str = "head"):
    """Run migrations up to a specific revision.
    
    Args:
        revision: The target revision (default: 'head').
        
    Usage:
        python -c "
        from src.database.migrations import upgrade_database
        upgrade_database()  # Upgrade to head
        upgrade_database('abc1234')  # Upgrade to specific revision
        "
    """
    if Config is None:
        print("✗ Alembic not installed. Run: pip install alembic")
        return
    
    config = Config("alembic.ini")
    command.upgrade(config, revision)
    print(f"✓ Database upgraded to {revision}")


def downgrade_database(revision: str):
    """Roll back migrations to a specific revision.
    
    Args:
        revision: The target revision to roll back to.
        
    Usage:
        python -c "
        from src.database.migrations import downgrade_database
        downgrade_database('-1')  # Downgrade one revision
        downgrade_database('abc1234')  # Downgrade to specific revision
        "
    """
    if Config is None:
        print("✗ Alembic not installed. Run: pip install alembic")
        return
    
    config = Config("alembic.ini")
    command.downgrade(config, revision)
    print(f"✓ Database downgraded to {revision}")


if __name__ == "__main__":
    import asyncio
    
    print("MMC Database Migration Tool")
    print("=" * 50)
    
    # Example: Initialize database
    asyncio.run(initialize_database())
    
    # Example: Verify connection
    asyncio.run(verify_database_connection())
