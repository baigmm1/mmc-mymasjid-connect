"""
Sync Stripe Subscriptions to RecurringTransactions Script

This script retrieves all subscriptions from Stripe for a given company
and synchronizes them with the RecurringTransactions table in the database.

Usage:
    python -m src.scripts.sync_stripe_subscriptions --company-id 10001
    python -m src.scripts.sync_stripe_subscriptions --company-id 10001 --dry-run
    python -m src.scripts.sync_stripe_subscriptions --company-id 10001 --status active

Features:
    - Retrieves all subscriptions from Stripe for a company
    - Compares with existing RecurringTransactions records
    - Creates new recurring transactions for new subscriptions
    - Updates existing recurring transactions with latest Stripe data
    - Supports dry-run mode for testing without database changes
    - Filter by subscription status (active, canceled, all)
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from stripe import Subscription

from src.config import settings
from src.core.logging import get_logger
from src.core.cache_manager import initialize_caches, warm_all_caches
from src.core.provider_manager import get_stripe_provider
from src.core.recurring_transactions_utils import (
    get_recurring_transactions_by_criteria,
    get_recurring_transaction_by_subscription_id,
    create_recurring_transaction,
    update_recurring_transaction,
)
from src.database import get_session
from src.models.recurring_transactions import (
    RecurringTransactionCreateModel,
    RecurringTransactionDetailsCreateModel,
    RecurringTransactionUpdateModel,
    RecurringTransactionStatusEnum,
    RecurringFrequencyEnum,
)
from src.core.donors_utils import find_donor_by_email
from src.core.donors_review_utils import find_donor_review_by_email

logger = get_logger(__name__, level=settings.LOG_LEVEL)


class StripeSubscriptionSyncService:
    """Service for syncing Stripe subscriptions to RecurringTransactions table."""

    def __init__(self, session: AsyncSession, company_id: int, dry_run: bool = False):
        """
        Initialize the sync service.

        Args:
            session: Database session
            company_id: Company ID to sync subscriptions for
            dry_run: If True, don't make any database changes
        """
        self.session = session
        self.company_id = company_id
        self.dry_run = dry_run
        self.stripe_provider = None
        self.stats = {
            "total_stripe_subscriptions": 0,
            "existing_records": 0,
            "new_records": 0,
            "updated_records": 0,
            "skipped_records": 0,
            "errors": 0,
        }

    async def initialize(self):
        """Initialize Stripe provider for the company."""
        logger.info(f"Initializing Stripe provider for company {self.company_id}")
        self.stripe_provider = await get_stripe_provider(
            session=self.session,
            company_id=self.company_id
        )
        logger.info("Stripe provider initialized successfully")

    # async def get_stripe_subscriptions(
    #     self,
    #     status_filter: Optional[str] = None
    # ) -> List[Any]:
    #     """
    #     Retrieve all subscriptions from Stripe.

    #     Args:
    #         status_filter: Filter by status - 'active', 'canceled', 'all', etc.

    #     Returns:
    #         List of Stripe subscription objects
    #     """
    #     logger.info(
    #         f"Fetching subscriptions from Stripe for company {self.company_id}",
    #         extra={"status_filter": status_filter}
    #     )

    #     try:
    #         subscriptions = await self.stripe_provider.get_subscriptions(status=status_filter) # type: ignore
    #         for sub in subscriptions:
    #             logger.info(f"Found subscription: {sub.id} (status: {sub.status})")

    #             # check if we have this subscription in our database and if the status has changed. 

    #         # Example: Get subscriptions for a specific customer
    #         # customer = await self.stripe_provider.get_customer(email)
    #         # if customer:
    #         #     customer_subscriptions = await self.stripe_provider.get_subscriptions(customer.id)
    #         #     subscriptions.extend(customer_subscriptions)
            
    #         # Example: Filter by status if needed
    #         # if status_filter and status_filter != 'all':
    #         #     subscriptions = [s for s in subscriptions if s.status == status_filter]

    #         self.stats["total_stripe_subscriptions"] = len(subscriptions)
    #         logger.info(f"Retrieved {len(subscriptions)} subscriptions from Stripe")
            
    #         return subscriptions

    #     except Exception as e:
    #         logger.error(f"Error fetching subscriptions from Stripe: {str(e)}", exc_info=True)
    #         raise

    async def get_existing_recurring_transactions(self) -> Dict[str, Any]:
        """
        Get existing recurring transactions from database for this company.

        Returns:
            Dictionary mapping SubscriptionId to transaction record
        """
        logger.info(f"Fetching existing recurring transactions for company {self.company_id}")

        try:
            # Use utility function to get all transactions for this company
            result = await get_recurring_transactions_by_criteria(
                session=self.session,
                company_id=self.company_id,
                provider_name="Stripe"
            )
            
            # Convert to dictionary keyed by subscription ID
            transactions_dict = {}
            for transaction in result.items:
                if transaction.subscriptionId:
                    transactions_dict[transaction.subscriptionId] = transaction
            
            self.stats["existing_records"] = len(transactions_dict)
            logger.info(f"Found {len(transactions_dict)} existing recurring transactions")
            
            return transactions_dict

        except Exception as e:
            logger.error(f"Error fetching existing recurring transactions: {str(e)}", exc_info=True)
            # If error, return empty dict
            logger.warning("Error retrieving transactions - returning empty result")
            return {}

    async def create_recurring_transaction_from_stripe(
        self,
        subscription: Subscription,
    ) -> bool:
        """
        Create a new recurring transaction record from Stripe subscription.

        Args:
            subscription: Stripe subscription object
            donor_id: Optional donor ID (will be looked up if not provided)

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Creating new recurring transaction for subscription {subscription.id}")

        if self.dry_run:
            logger.info("[DRY RUN] Would create new recurring transaction")
            self.stats["new_records"] += 1
            return True

        try:
            # Extract subscription details
            subscription_id = subscription.id
            start_date = datetime.fromtimestamp(subscription.start_date) if hasattr(subscription, 'start_date') else datetime.utcnow()
            end_date = datetime.fromtimestamp(subscription.cancel_at) if subscription.cancel_at else datetime(2099, 12, 31)
            status = self._map_stripe_status_to_db_status(subscription.status)
            metadata = subscription.get('metadata', {})
            cause_id = metadata.get('cause', None)

            customer = getattr(subscription, 'customer', None)
            donor_id = 0    # assume anon
            review_donor_id = 0
            customer_id = None
            payment_method_id = None
            if customer:
                customer_id = customer.id if hasattr(customer, 'id') else None
                
            if customer and hasattr(customer, 'email'):
                # Try to find donor by email
                donor_email = customer.email
                logger.info(f"Looking up donor by email: {donor_email}")
                donor = await find_donor_by_email(self.session, donor_email)  # Implement this function to query your donors table
                if donor:
                    donor_id = donor.DonorId
                    logger.info(f"Found donor {donor_id} for email {donor_email}")
                else:
                    donor_review = await find_donor_review_by_email(self.session, company_id=self.company_id, email=donor_email)  # Implement this function to query your donor reviews table
                    if donor_review:
                        review_donor_id = donor_review.DonorId
                        logger.info(f"Found donor review {review_donor_id} for email {donor_email}")
            

            # Determine frequency based on subscription interval
            frequency = RecurringFrequencyEnum.MONTHLY  # Default
            details = []
            total_amount = Decimal("0.00")
            
            # Handle subscription.items - it could be a property or need different access
            items_data = subscription.get("items", {}).get("data", [])                    
            
            if items_data:
                logger.info(f"Processing {len(items_data)} subscription items for subscription {subscription_id}")
                for item in items_data:
                    item_price = item.get("price", None)
                    if item_price:
                        logger.info(f"Processing item with price ID {item_price.get('id', 'N/A')} and amount {item_price.get('unit_amount', 'N/A')}")
                        total_amount +=  Decimal(item_price.get('unit_amount', 0)) / 100 # type: ignore

                        
                        product_id = item_price.get('product', None)
                        donation_type = -1
                        if product_id:
                            product = await self.stripe_provider.get_product_by_id(product_id)  # type: ignore
                            if product and hasattr(product, 'metadata'):
                                donation_type = int(product.metadata.get('donationType', -1))  # type: ignore

                        detail_line = RecurringTransactionDetailsCreateModel(
                            donationType=donation_type, # need to derive
                            priceId=item_price.get('id', None),
                            productId=product_id,
                            causeId=cause_id,
                            amount=Decimal(item_price.get('unit_amount', 0)) / 100, #type: ignore
                            currency=item_price.get('currency', "USD"),
                        )
                        if hasattr(item_price, 'recurring'):
                            interval = item_price.recurring.interval    # type: ignore
                            if interval == 'year':
                                frequency = RecurringFrequencyEnum.YEARLY
                            elif interval == 'week':
                                frequency = RecurringFrequencyEnum.WEEKLY
                            elif interval == 'month':
                                frequency = RecurringFrequencyEnum.MONTHLY
                            elif interval == 'day':
                                frequency = RecurringFrequencyEnum.DAILY
                            elif interval == 'quarter':
                                frequency = RecurringFrequencyEnum.QUARTERLY
                            elif interval == 'halfyear':
                                frequency = RecurringFrequencyEnum.HALFYEAR
                        
                        details.append(detail_line)
                        

            payment_method = subscription.default_payment_method if hasattr(subscription, 'default_payment_method') else None
            if payment_method and hasattr(payment_method, 'id'):
                payment_method_id = payment_method.id   # type: ignore

            # Create transaction data model
            transaction_data = RecurringTransactionCreateModel(
                companyId=self.company_id,
                donorId=donor_id,
                reviewDonorId=review_donor_id,
                startDate=start_date,
                frequency=frequency,
                frequencyCount=1,
                endDate=end_date,
                providerName="Stripe",
                subscriptionId=subscription_id,
                customerId=customer_id,
                paymentMethodId=payment_method_id,
                paymentMethod=self.stripe_provider.extract_payment_method_desc(payment_method) if self.stripe_provider and payment_method else None, # type: ignore
                totalAmount=total_amount,
                status=status,
                details=details,
            )

            # Use utility function to create transaction
            transaction_id = await create_recurring_transaction(
                session=self.session,
                transaction_data=transaction_data,
                created_by=-1,  # System user
            )

            if transaction_id:
                logger.info(f"Successfully created recurring transaction {transaction_id} for subscription {subscription_id}")
                self.stats["new_records"] += 1
                return True
            else:
                logger.error(f"Failed to create recurring transaction for subscription {subscription_id}")
                self.stats["errors"] += 1
                return False

        except Exception as e:
            logger.error(f"Error creating recurring transaction: {str(e)}", exc_info=True)
            self.stats["errors"] += 1
            return False

    # async def update_recurring_transaction_from_stripe(
    #     self,
    #     subscription: Any,
    #     existing_transaction: Any
    # ) -> bool:
    #     """
    #     Update an existing recurring transaction with latest Stripe data.

    #     Args:
    #         subscription: Stripe subscription object
    #         existing_transaction: Existing database record

    #     Returns:
    #         True if successful, False otherwise
    #     """
    #     transaction_id = existing_transaction.transactionId
    #     logger.info(f"Updating recurring transaction {transaction_id} for subscription {subscription.id}")

    #     if self.dry_run:
    #         logger.info("[DRY RUN] Would update existing recurring transaction")
    #         self.stats["updated_records"] += 1
    #         return True

    #     try:
    #         # Check if update is needed by comparing key fields
    #         needs_update = self._check_if_update_needed(subscription, existing_transaction)
            
    #         if not needs_update:
    #             logger.info(f"No update needed for transaction {transaction_id}")
    #             self.stats["skipped_records"] += 1
    #             return True

    #         # Extract updated subscription details
    #         end_date = datetime.fromtimestamp(subscription.cancel_at) if subscription.cancel_at else None
    #         status = self._map_stripe_status_to_db_status(subscription.status)
            
    #         # Get subscription items and calculate total amount
    #         total_amount = Decimal("0.00")
    #         if hasattr(subscription, 'items') and subscription.items.data:
    #             for item in subscription.items.data:
    #                 if hasattr(item, 'price') and item.price.unit_amount:
    #                     total_amount += Decimal(item.price.unit_amount) / 100

    #         # Create update data model
    #         update_data = RecurringTransactionUpdateModel(
    #             donorId=None,
    #             reviewDonorId=None,
    #             endDate=end_date,
    #             paymentMethod=subscription.default_payment_method if hasattr(subscription, 'default_payment_method') else None,
    #             totalAmount=total_amount,
    #             status=status,
    #         )

    #         # Use utility function to update transaction
    #         success = await update_recurring_transaction(
    #             session=self.session,
    #             transaction_id=transaction_id,
    #             transaction_data=update_data,
    #             modified_by=0,  # System user
    #         )

    #         if success:
    #             logger.info(f"Successfully updated recurring transaction {transaction_id}")
    #             self.stats["updated_records"] += 1
    #             return True
    #         else:
    #             logger.error(f"Failed to update recurring transaction {transaction_id}")
    #             self.stats["errors"] += 1
    #             return False

    #     except Exception as e:
    #         logger.error(f"Error updating recurring transaction: {str(e)}", exc_info=True)
    #         self.stats["errors"] += 1
    #         return False

    def _map_stripe_status_to_db_status(self, stripe_status: str) -> int:
        """
        Map Stripe subscription status to database status code.

        Args:
            stripe_status: Stripe status (active, canceled, incomplete, etc.)

        Returns:
            Database status code (1=Active, 2=Canceled, 3=Paused, etc.)
        """
        status_mapping = {
            "active": RecurringTransactionStatusEnum.ACTIVE,
            "canceled": RecurringTransactionStatusEnum.CANCELED,
            "incomplete": RecurringTransactionStatusEnum.INCOMPLETE,
            "incomplete_expired": RecurringTransactionStatusEnum.INCOMPLETE_EXPIRED,
            "past_due": RecurringTransactionStatusEnum.PAST_DUE,
            "trialing": RecurringTransactionStatusEnum.TRIALING,
            "unpaid": RecurringTransactionStatusEnum.UNPAID,
            "paused": RecurringTransactionStatusEnum.PAUSED,
        }
        return status_mapping.get(stripe_status.lower(), RecurringTransactionStatusEnum.INCOMPLETE)

    def _check_if_update_needed(
        self,
        subscription: Any,
        existing_transaction: Any
    ) -> bool:
        """
        Check if the subscription has changes that require database update.

        Args:
            subscription: Stripe subscription object
            existing_transaction: Existing database record

        Returns:
            True if update is needed, False otherwise
        """
        # Compare key fields to determine if update is needed
        
        # Check status
        current_status = self._map_stripe_status_to_db_status(subscription.status)
        db_status = existing_transaction.status
        if current_status != db_status:
            logger.info(f"Status changed: {db_status} -> {current_status}")
            return True

        # Check end date
        stripe_end_date = datetime.fromtimestamp(subscription.cancel_at) if subscription.cancel_at else None
        db_end_date = existing_transaction.endDate
        
        if stripe_end_date and db_end_date:
            # Compare dates (ignore time component for comparison)
            if stripe_end_date.date() != db_end_date.date():
                logger.info(f"End date changed: {db_end_date.date()} -> {stripe_end_date.date()}")
                return True
        elif stripe_end_date or db_end_date:
            # One has end date, other doesn't
            logger.info(f"End date changed: one is None")
            return True

        # Check total amount
        total_amount = Decimal("0.00")
        items = None
        if hasattr(subscription, 'items'):
            items_attr = getattr(subscription, 'items', None)
            if items_attr and hasattr(items_attr, 'data'):
                items = items_attr
        
        if items and hasattr(items, 'data'):
            for item in items.data:
                if hasattr(item, 'price') and item.price.unit_amount:
                    total_amount += Decimal(item.price.unit_amount) / 100
        
        db_amount = existing_transaction.totalAmount
        if db_amount and abs(total_amount - Decimal(str(db_amount))) > Decimal("0.01"):
            logger.info(f"Amount changed: {db_amount} -> {total_amount}")
            return True

        return False

    async def sync_subscriptions(self, status_filter: Optional[str] = None):
        """
        Main sync process - retrieves Stripe subscriptions and syncs to database.

        Args:
            status_filter: Filter subscriptions by status
        """
        logger.info("=" * 80)
        logger.info(f"Starting Stripe subscription sync for company {self.company_id}")
        logger.info(f"Dry run mode: {self.dry_run}")
        logger.info(f"Status filter: {status_filter or 'all'}")
        logger.info("=" * 80)

        try:
            # Initialize Stripe provider
            await self.initialize()

            # Get subscriptions from Stripe
            stripe_subscriptions = await self.stripe_provider.get_subscriptions(status_filter, expand=["data.customer", "data.default_payment_method", "data.items"])  # type: ignore            
            # write the stripe subscriptions to a file for debugging
            # with open(f"stripe_subscriptions_{self.company_id}.json", "w") as f:
            #     f.write(json.dumps([s.to_dict() for s in stripe_subscriptions], default=str, indent=4))

            # Process each subscription
            for subscription in stripe_subscriptions:
                subscription_id = subscription.id
                logger.info(f"Processing subscription: {subscription_id}")

                #Check if we have this subscription in our database
                existing_transaction = await get_recurring_transaction_by_subscription_id(
                    session=self.session,
                    company_id=self.company_id,
                    subscription_id=subscription_id
                )
                if not existing_transaction:
                    # create a new recurring transaction record for this subscription                    
                    await self.create_recurring_transaction_from_stripe(subscription)

            # Print summary
            self._print_summary()

        except Exception as e:
            logger.error(f"Error during subscription sync: {str(e)}", exc_info=True)
            raise

    def _print_summary(self):
        """Print sync summary statistics."""
        logger.info("=" * 80)
        logger.info("SYNC SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Stripe subscriptions: {self.stats['total_stripe_subscriptions']}")
        logger.info(f"Existing DB records: {self.stats['existing_records']}")
        logger.info(f"New records created: {self.stats['new_records']}")
        logger.info(f"Records updated: {self.stats['updated_records']}")
        logger.info(f"Records skipped (no changes): {self.stats['skipped_records']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info("=" * 80)


async def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Sync Stripe subscriptions to RecurringTransactions table"
    )
    parser.add_argument(
        "--company-id",
        type=int,
        required=True,
        help="Company ID to sync subscriptions for"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (no database changes)"
    )
    parser.add_argument(
        "--status",
        type=str,
        choices=["active", "canceled", "all"],
        default="all",
        help="Filter subscriptions by status (default: all)"
    )

    args = parser.parse_args()

    logger.info("Starting Stripe subscription sync script")
    logger.info(f"Company ID: {args.company_id}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info(f"Status filter: {args.status}")

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
            sync_service = StripeSubscriptionSyncService(
                session=session,
                company_id=args.company_id,
                dry_run=args.dry_run
            )

            # Run sync
            await sync_service.sync_subscriptions(
                status_filter=args.status if args.status != "all" else None
            )

            # Commit if not dry run
            if not args.dry_run:
                await session.commit()
                logger.info("Database changes committed")
            else:
                logger.info("Dry run - no database changes made")

        logger.info("Subscription sync completed successfully")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Script failed with error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
