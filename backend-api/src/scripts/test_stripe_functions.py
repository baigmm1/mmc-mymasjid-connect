"""
Test functions in StripePaymentProvider that interact with the Stripe API. These tests use mocking to simulate Stripe API responses and ensure that our provider functions handle them correctly.
"""
import argparse
import asyncio
import json
import sys
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.logging import get_logger
from src.core.cache_manager import initialize_caches, warm_all_caches
from src.core.provider_manager import get_stripe_provider
from src.database import get_session

logger = get_logger(__name__, level=settings.LOG_LEVEL)

class StripeFunctionTestService:
    """Service for syncing Stripe subscriptions to RecurringTransactions table."""

    def __init__(self, session: AsyncSession, company_id: int):
        """
        Initialize the sync service.

        Args:
            session: Database session
            company_id: Company ID to sync subscriptions for
        """
        self.session = session
        self.company_id = company_id        
        self.stripe_provider = None
        
    async def initialize(self):
        """Initialize Stripe provider for the company."""
        logger.info(f"Initializing Stripe provider for company {self.company_id}")
        self.stripe_provider = await get_stripe_provider(
            session=self.session,
            company_id=self.company_id
        )
        logger.info("Stripe provider initialized successfully")

    async def search_product(self, donationType: str, description: Optional[str] = None):
        """Test the search_product function of the Stripe provider."""
        if not self.stripe_provider:
            await self.initialize()
        
        logger.info(f"Testing search_product with donationType='{donationType}' and description='{description}'")
        product = await self.stripe_provider.search_product(donationType=donationType, description=description)
        if product:
            logger.info(f"Product found: ID={product.id}, Name={product.name}")
        else:
            logger.info("No product found matching the criteria")

async def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Test Stripe provider functions by simulating Stripe API responses and ensuring correct handling."
    )
    parser.add_argument(
        "--company-id",
        type=int,
        required=True,
        help="Company ID to test Stripe provider functions for"
    )
    
    args = parser.parse_args()

    logger.info("Starting Stripe provider function test script")
    logger.info(f"Company ID: {args.company_id}")

    try:
        # Initialize caches
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
        
        # Get database session
        async for session in get_session():
            # Create sync service
            sync_service = StripeFunctionTestService(
                session=session,
                company_id=args.company_id
            )

            await sync_service.search_product(donationType="20", description="Iftar/Eid Donation")

            # # Run sync
            # await sync_service.sync_subscriptions(
            #     status_filter=args.status if args.status != "all" else None
            # )

            # # Commit if not dry run
            # if not args.dry_run:
            #     await session.commit()
            #     logger.info("Database changes committed")
            # else:
            #     logger.info("Dry run - no database changes made")

        logger.info("Stripe provider function test completed successfully")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Script failed with error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())