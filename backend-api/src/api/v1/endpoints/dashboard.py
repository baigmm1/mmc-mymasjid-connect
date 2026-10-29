"""
Dashboard endpoints for donor dashboard data.

Provides endpoints for comprehensive donor dashboard with grouped data loading:
- Overview: Summary stats, recent donations, recurring donations, tax receipts
- Charts: Donation trends and category breakdowns
- Community: Impact metrics, events, and announcements

Endpoints:
    GET /api/v1/dashboard/overview - Get dashboard overview data (summary + lists)
    GET /api/v1/dashboard/charts - Get chart data (trends + categories)
    GET /api/v1/dashboard/community - Get community data (impact + events + announcements)
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.dependencies import User, get_current_user_optional, get_current_user_required
from src.core.donors_utils import get_donor_by_user_id
from src.core.logging import get_logger
from src.database import get_session
from src.database.models.donors import Donors
from src.database.models.transaction_header import TransactionHeader
from src.database.models.transaction_details import TransactionDetails
from src.models.dashboard import (
    DashboardOverviewResponse,
    DashboardChartsResponse,
    DashboardCommunityResponse,
    DonationsByPeriodModel,
    DonationSummaryModel,
    DonationTrendModel,
    DonationTrendDataPointModel,
    DonationCategoryModel,
    RecentDonationModel,
    RecurringDonationModel,
    ImpactMetricModel,
    UpcomingEventModel,
    AnnouncementModel,
    TaxReceiptModel,
)
from src.core.cache_manager import get_company_from_cache
from src.core.stored_procedure_utils import execute_stored_procedure
from src.core.provider_manager import get_stripe_provider
from src.core.transaction_utils import get_transaction_by_criteria
from src.core.recurring_transactions_utils import get_recurring_transactions_by_criteria

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
logger = get_logger(__name__, level=settings.LOG_LEVEL)

# Color palette for donation categories (max 10 categories)
CATEGORY_COLOR_PALETTE = [
    "#3B82F6",  # Blue
    "#10B981",  # Green
    "#F59E0B",  # Amber
    "#EF4444",  # Red
    "#8B5CF6",  # Violet
    "#EC4899",  # Pink
    "#14B8A6",  # Teal
    "#F97316",  # Orange
    "#6366F1",  # Indigo
    "#06B6D4",  # Cyan
]


@router.get(
    "/overview/{company_id}",
    response_model=DashboardOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get donor dashboard overview",
    description="""
    Retrieve comprehensive dashboard overview data including:
    - Donation summaries (this month, this year, lifetime, tax year)
    - Recent donation history
    - Active recurring donations
    - Available tax receipts
    
    This endpoint groups related content for efficient loading.
    """,
)
async def get_dashboard_overview(
    company_id: int,
    current_user: User = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(10, ge=1, le=50, description="Number of recent donations to return"),
) -> DashboardOverviewResponse:
    """
    Get dashboard overview data for the authenticated donor.
    
    Args:
        current_user: Authenticated user
        session: Database session
        limit: Number of recent donations to return
        
    Returns:
        DashboardOverviewResponse with summary, recent donations, recurring donations, and tax receipts
    """
    logger.info(f"Fetching dashboard overview for user: {current_user.id} and company: {company_id}")
    
    try:
        # Find the donor record for the current user
        donor = await _get_donor_for_user(session, current_user)
        
        if not donor:
            logger.warning(f"No donor record found for user: {current_user.id}")
            # Return empty data structure for users without donor records
            return _create_empty_overview_response()
        
        # validate the company
        company = await get_company_from_cache(company_id, session)

        if company is None:
            logger.warning(f"Company ID not found: {company_id}")
            return _create_empty_overview_response()

        # Get donation summaries by period
        summary = await _get_donation_summaries(session, company.CompanyId, donor.DonorId)
        
        # Get recent donations
        recent_donations = await _get_recent_donations(session, company.CompanyId, donor.DonorId, limit)
        
        # Get recurring donations
        recurring_donations = await _get_recurring_donations(session, company.CompanyId, donor.DonorId, donor.EMail)
        #recurring_donations = []
        
        # Get tax receipts
        tax_receipts = await _get_tax_receipts(session, company.CompanyId, donor.DonorId)
        
        return DashboardOverviewResponse(
            summary=summary,
            recent_donations=recent_donations,
            recurring_donations=recurring_donations,
            tax_receipts=tax_receipts,
        )
    except Exception as e:
        logger.error(
            f"Error retrieving companies: {str(e)}",
            extra={"error": str(e), "error_type": type(e).__name__},
            exc_info=True,
        )
        raise

@router.get(
    "/recurring-donations/{company_id}",
    response_model=list[RecurringDonationModel],
    status_code=status.HTTP_200_OK, 
)
async def get_recurring_donations(
    company_id: int,
    current_user: User = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_session),
) -> list[RecurringDonationModel]:
    """
    Get active recurring donations for the authenticated donor.
    
    Args:
        current_user: Authenticated user
        session: Database session
    Returns:
        List of RecurringDonationModel
    """
    logger.info(f"Fetching recurring donations for user: {current_user.id} and company: {company_id}")
    
    # Find the donor record for the current user
    donor = await _get_donor_for_user(session, current_user)
    
    if not donor:
        logger.warning(f"No donor record found for user: {current_user.id}")
        return []
    
    # Get recurring donations
    recurring_donations = await _get_recurring_donations(session, company_id, donor.DonorId, donor.EMail)
    #recurring_donations = []
    return recurring_donations

@router.get(
    "/charts/{company_id}",
    response_model=DashboardChartsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get donor dashboard chart data",
    description="""
    Retrieve chart data for dashboard visualizations:
    - Donation trends over time (monthly view)
    - Donation breakdown by category/type
    
    This endpoint is separate from overview for efficient loading and caching.
    """,
)
async def get_dashboard_charts(
    company_id: int,
    current_user: User = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_session),
    period: str = Query("monthly", regex="^(daily|weekly|monthly)$", description="Trend period type"),
    months: int = Query(12, ge=1, le=24, description="Number of months to include in trend"),
) -> DashboardChartsResponse:
    """
    Get chart data for the authenticated donor.
    
    Args:
        current_user: Authenticated user
        session: Database session
        period: Period type for trends ('daily', 'weekly', 'monthly')
        months: Number of months to include
        
    Returns:
        DashboardChartsResponse with trends and category breakdown
    """
    logger.info(f"Fetching dashboard charts for user: {current_user.id}, period: {period}")
    
    # Find the donor record for the current user
    donor = await _get_donor_for_user(session, current_user)
    
    if not donor:
        logger.warning(f"No donor record found for user: {current_user.id}")
        return _create_empty_charts_response()
    
    # Get donation trends
    donation_trends = await _get_donation_trends(session, company_id, donor.DonorId, period, months)
    
    # Get category breakdown
    category_breakdown = await _get_category_breakdown(session, company_id, donor.DonorId, period, months)
    
    return DashboardChartsResponse(
        donation_trends=donation_trends,
        category_breakdown=category_breakdown,
    )


# @router.get(
#     "/community/{company_id}",
#     response_model=DashboardCommunityResponse,
#     status_code=status.HTTP_200_OK,
#     summary="Get community dashboard data",
#     description="""
#     Retrieve community-related dashboard data:
#     - Impact metrics showing community reach
#     - Upcoming events
#     - Recent announcements and updates
    
#     This data is typically less frequently updated and can be cached longer.
#     """,
# )
# async def get_dashboard_community(
#     company_id: int,
#     current_user: User = Depends(get_current_user_optional),
#     session: AsyncSession = Depends(get_session),
#     event_limit: int = Query(5, ge=1, le=20, description="Number of upcoming events"),
#     announcement_limit: int = Query(5, ge=1, le=20, description="Number of announcements"),
# ) -> DashboardCommunityResponse:
#     """
#     Get community data for the dashboard.
    
#     Args:
#         current_user: Authenticated user
#         session: Database session
#         event_limit: Number of upcoming events to return
#         announcement_limit: Number of announcements to return
        
#     Returns:
#         DashboardCommunityResponse with impact metrics, events, and announcements
#     """
#     logger.info(f"Fetching community dashboard data for user: {current_user.id if current_user else 'anonymous'}, company: {company_id}")
    
#     # Get impact metrics (stub - placeholder)
#     impact_metrics = _get_impact_metrics_stub()
    
#     # Get upcoming events (stub - placeholder)
#     upcoming_events = _get_upcoming_events_stub(event_limit)
    
#     # Get announcements (stub - placeholder)
#     announcements = _get_announcements_stub(announcement_limit)
    
#     return DashboardCommunityResponse(
#         impact_metrics=impact_metrics,
#         upcoming_events=upcoming_events,
#         announcements=announcements,
#     )


# Helper Functions

async def _get_donor_for_user(session: AsyncSession, user: User) -> Optional[Donors]:
    """Get donor record for authenticated user using DonorUserLinks table."""
    return await get_donor_by_user_id(session, user.id, active_only=True)


async def _get_donation_summaries(session: AsyncSession, company_id: int, donor_id: int) -> DonationsByPeriodModel:
    """Get donation summaries for different time periods."""
    now = datetime.now()
    current_year_start = datetime(now.year, 1, 1)
    current_month_start = datetime(now.year, now.month, 1)
    
    # This month summary
    this_month = await _get_period_summary(
        session, company_id, donor_id, current_month_start, now
    )
    
    # This year summary
    this_year = await _get_period_summary(
        session, company_id, donor_id, current_year_start, now
    )
    
    # Lifetime summary
    lifetime = await _get_period_summary(
        session, company_id, donor_id, None, None
    )
    
    # Tax year (same as current year for now)
    tax_year = this_year
    
    return DonationsByPeriodModel(
        this_month=this_month,
        this_year=this_year,
        lifetime=lifetime,
        tax_year=tax_year,
    )


async def _get_period_summary(
    session: AsyncSession,
    company_id: int,
    donor_id: int,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> DonationSummaryModel:
    """Get donation summary for a specific period."""

    # Prepare parameters for stored procedure
    parameters = {
        "DataType": 1,            
        "CompanyId": company_id,
        "DonorId": donor_id,
        "StartDate": start_date,
        "EndDate": end_date,
    }

    summary = DonationSummaryModel(
        start_date=start_date or datetime.min,
        end_date=end_date or datetime.max,
        total_amount=0.0,
        total_count= 0,
        donation_count=0,
        donation_amount=0.0,
        average_donation=0.0,
        services_amount=0.0,
        services_count=0,
        trend_percentage=None,
        trend_direction=None,
    )

    # Calculate previous period for trend comparison
    prev_start_date: Optional[datetime] = None
    prev_end_date: Optional[datetime] = None
    
    if start_date and end_date:
        # Calculate the duration of the current period
        period_duration = end_date - start_date
        # Previous period ends where current period starts, with same duration
        prev_end_date = start_date
        prev_start_date = start_date - period_duration

    # Remove None values
    parameters = {k: v for k, v in parameters.items() if v is not None}

    result = await execute_stored_procedure(
            session=session,
            procedure_name="[dbo].[UIQueryGetTransactions]",
            parameters=parameters,
            fetch_results=True,
            fetch_multiple=False
        )
        
    if not result or len(result) == 0:
        logger.warning(
            "No Data found for donor",
            extra={
                "company_id": company_id,
                "donor_id": donor_id,
            }
        )
        return summary
        
    # Parse transaction data - result is a list, get first element
    row: dict = result[0]  # type: ignore # Type hint to help linter
    if not row:
        logger.warning(
            "No Data found for donor",
            extra={
                "company_id": company_id,
                "donor_id": donor_id,
            }
        )
        return summary
    if row.get("StartDate"):
        summary.start_date = row.get("StartDate")  # type: ignore
    if row.get("EndDate"):
        summary.end_date = row.get("EndDate")  # type: ignore
    if row.get("PaymentAmount"):
        summary.total_amount = float(row.get("PaymentAmount")) # type: ignore
    if row.get("PaymentCount"):
        summary.total_count = int(row.get("PaymentCount")) # type: ignore    
    if row.get("DonationTotalAmount"):
        summary.donation_amount = float(row.get("DonationTotalAmount")) # type: ignore
    if row.get("DonationCount"):
        summary.donation_count = int(row.get("DonationCount")) # type: ignore
    if row.get("ServicesAmount"):
        summary.services_amount = float(row.get("ServicesAmount")) # type: ignore    
    if row.get("ServicesCount"):
        summary.services_count = int(row.get("ServicesCount")) # type: ignore

    if summary.donation_count > 0 and summary.donation_amount > 0:
        summary.average_donation = summary.donation_amount / summary.donation_count
    
    # Calculate trend if we have a valid previous period
    if prev_start_date and prev_end_date and summary.total_amount > 0:
        prev_parameters = {
            "DataType": 1,
            "CompanyId": company_id,
            "DonorId": donor_id,
            "StartDate": prev_start_date,
            "EndDate": prev_end_date,
        }
        
        # Remove None values
        prev_parameters = {k: v for k, v in prev_parameters.items() if v is not None}
        
        try:
            prev_result = await execute_stored_procedure(
                session=session,
                procedure_name="[dbo].[UIQueryGetTransactions]",
                parameters=prev_parameters,
                fetch_results=True,
                fetch_multiple=False
            )
            
            if prev_result and len(prev_result) > 0:
                prev_row: dict = prev_result[0]  # type: ignore
                prev_amount = float(prev_row.get("PaymentAmount", 0) or 0)
                
                # Calculate percentage change
                if prev_amount > 0:
                    change = summary.total_amount - prev_amount
                    summary.trend_percentage = round((change / prev_amount) * 100, 1)
                    
                    # Determine direction
                    if summary.trend_percentage > 0.5:
                        summary.trend_direction = "up"
                    elif summary.trend_percentage < -0.5:
                        summary.trend_direction = "down"
                    else:
                        summary.trend_direction = "flat"
                elif summary.total_amount > 0:
                    # Previous period had no donations, current period does
                    summary.trend_percentage = 100.0
                    summary.trend_direction = "up"
                    
        except Exception as e:
            # Log error but don't fail the main request
            logger.warning(
                f"Failed to calculate trend for period: {str(e)}",
                extra={
                    "company_id": company_id,
                    "donor_id": donor_id,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )
    
    return summary    


async def _get_recent_donations(
    session: AsyncSession,
    company_id: int,
    donor_id: int,
    limit: int,
) -> list[RecentDonationModel]:
    """Get recent donations for donor."""
    recent_donations = []

    # Prepare parameters for stored procedure
    parameters = {
        "DataType": 2,            
        "CompanyId": company_id,
        "DonorId": donor_id,
        "TopN": limit,
    }

    # Remove None values
    parameters = {k: v for k, v in parameters.items() if v is not None}

    result = await execute_stored_procedure(
        session=session,
        procedure_name="[dbo].[UIQueryGetTransactions]",
        parameters=parameters,
        fetch_results=True,
        fetch_multiple=False
    )

    transactions = result or []
    
    for txn in transactions:
        recent_donations.append(RecentDonationModel(
            transaction_id=txn.get("TransactionId"),  # type: ignore
            date=txn.get("TransactionDate"),# type: ignore
            amount=float(txn.get("TotalAmount")),# type: ignore
            category_id=txn.get("CategoryId"),# type: ignore
            category_name=txn.get("CategoryName"),# type: ignore
            payment_method=txn.get("PaymentMethod"),# type: ignore
            status= 'completed',
            receipt_url=None,  
        ))
    
    return recent_donations


async def _get_recurring_donations(
    session: AsyncSession,
    company_id: int,
    donor_id: int,
    donor_email: str | None
) -> list[RecurringDonationModel]:
    """
    Access stripe to get active subscriptions for the donor.
    """

    if not donor_email:
        return []
    
    recurring_transactions = await get_recurring_transactions_by_criteria(
        session=session,
        company_id=company_id,
        donor_id=donor_id,
        status_filter=2,
        provider_name="Stripe",
        include_details=True,
        include_payments=True,
    )
    recurring_donations = []
    for transaction in recurring_transactions.items:
        categories = []
        # Get transaction details to find categories
        # use transaction details to create categories list - we already have this data in transacaction.details
        for detail in transaction.details:  # type: ignore    
            categories.append(detail.description)  # type: ignore
        
        last_payment_date = None
        if transaction.payments and len(transaction.payments) > 0:
            # Assuming payments are ordered by date, get the latest payment
            latest_payment = max(transaction.payments, key=lambda p: p.donationDate)
            last_payment_date = latest_payment.donationDate
        # to calcualte next payment date and remaining payments - we have to access one of the line items
        start_date = transaction.startDate
        end_date= transaction.endDate
        next_payment_date = None
        if transaction.payments and len(transaction.payments) > 0:
            latest_payment = max(transaction.payments, key=lambda p: p.donationDate)
            if transaction.frequency == 1:  # Weekly
                next_payment_date = latest_payment.donationDate + timedelta(weeks=1)
            elif transaction.frequency == 2:  # Monthly 
                next_payment_date = latest_payment.donationDate + timedelta(days=30)  # Approximate month
            elif transaction.frequency == 3:  # Annually
                next_payment_date = latest_payment.donationDate + timedelta(days=365)  # Approx
            
        if last_payment_date and start_date:
            delta_months = (last_payment_date.year - start_date.year) * 12 + (last_payment_date.month - start_date.month)
            payments_made = delta_months + 1  # +1 to include current month

            total_payments = transaction.frequencyCount
            remaining_payments = total_payments - payments_made if total_payments > payments_made else None
        else:
            remaining_payments = None

        recurring_donations.append(RecurringDonationModel(
            transaction_id=transaction.transactionId, # type: ignore
            subscription_id=transaction.subscriptionId, # type: ignore
            status="Active" if transaction.status == 2 else "Unknown", # type: ignore
            amount=transaction.totalAmount,# type: ignore
            frequency=transaction.frequencyDescription if transaction.frequencyDescription else str(transaction.frequency), # type: ignore
            categories=categories,  # Add empty categories list
            start_date = start_date, # type: ignore
            end_date= end_date, # type: ignore
            last_payment_date=last_payment_date,  # We will get this from Stripe
            next_payment_date=next_payment_date,  # We will get this from Stripe
            number_of_payments=transaction.frequencyCount,  # We will get this from Stripe metadata or calculate based on frequency and dates
            remaining_payments=remaining_payments,  # We will calculate this based on total payments and payments made
            payment_method=transaction.paymentMethod if transaction.paymentMethod else None, 
        ))
    
    # # Get Stripe provider (creates or retrieves from cache)
    # stripe = await get_stripe_provider(
    #     session=session,
    #     company_id=company_id
    # )
    
    # # List active subscriptions by customer email
    # subscriptions = await stripe.get_subscriptions(donor_email)
    
    # for sub in subscriptions:
    #     sub_id = sub.get("id")
    #     transaction = await get_transaction_by_criteria(
    #         session=session,
    #         company_id=company_id,
    #         provider_agreement_id=sub_id,
    #     )
    #     if transaction:
    #         categories = []
    #         # Get transaction details to find categories
    #         # use transaction details to create categories list - we already have this data in transaction.details
    #         for detail in transaction.details:  # type: ignore    
    #             if detail.donationTypeId != 99999:            
    #                 categories.append(detail.description)  # type: ignore
            
    #         last_payment_date = None
    #         if sub.get("latest_invoice") and sub.get("latest_invoice", {}).get("created"):
    #             last_payment_date = datetime.fromtimestamp(sub.get("latest_invoice", {}).get("created"))  # type: ignore

    #         payment_method = transaction.PaymentMethod if transaction and transaction.PaymentMethod else None
    #         if sub.get("default_payment_method"):
    #             payment_method_details = sub.get("default_payment_method", {})  # type: ignore
    #             if payment_method_details.get("type") == "card":
    #                 card_details = payment_method_details.get("card", {})
    #                 payment_method = f"{card_details.get("brand")} ****{card_details.get("last4")}"  # type: ignore
            
    #         # to calcualte next payment date and remaining payments - we have to access one of the line items
    #         start_date = datetime.fromtimestamp(sub.get("start_date")) # type: ignore
    #         end_date= datetime.fromtimestamp(sub.get("cancel_at")) if sub.get("cancel_at") else None # type: ignore
    #         next_payment_date = None
    #         remaining_payments = None
    #         items = sub.get("items", {})
    #         if items.get("data"):                
    #             line_item = items.get("data", [])[0] if len(items.get("data", [])) > 0 else None
    #             if line_item and line_item.get("current_period_end"):
    #                 next_payment_date = datetime.fromtimestamp(line_item.get("current_period_end"))  # type: ignore

    #                 if next_payment_date and last_payment_date:
    #                     # Calculate remaining payments based on metadata
    #                     total_payments = int(sub.get("metadata", {}).get("numberofMonths", 0))  # type: ignore
    #                     payments_made = 0
    #                     if last_payment_date and start_date:
    #                         delta_months = (last_payment_date.year - start_date.year) * 12 + (last_payment_date.month - start_date.month)
    #                         payments_made = delta_months + 1  # +1 to include current month

    #                     remaining_payments = total_payments - payments_made if total_payments > payments_made else None

    #         recurring_donations.append(RecurringDonationModel(
    #             subscription_id=sub_id, # type: ignore
    #             status=sub.get("status"),# type: ignore
    #             amount=transaction.TotalAmount,# type: ignore
    #             frequency="Monthly",
    #             categories=categories,  # Add empty categories list
    #             start_date = start_date,
    #             end_date= end_date,
    #             last_payment_date=last_payment_date,
    #             next_payment_date=next_payment_date,
    #             number_of_payments=sub.get("metadata", {}).get("numberofMonths"), # type: ignore
    #             remaining_payments=remaining_payments,
    #             payment_method=payment_method, 
    #         ))
    return recurring_donations

async def _get_tax_receipts(
    session: AsyncSession,
    company_id: int,
    donor_id: int,
) -> list[TaxReceiptModel]:
    """Get available tax receipts for donor."""
    tax_receipts = []

    # Prepare parameters for stored procedure
    parameters = {
        "DataType": 3,            
        "CompanyId": company_id,
        "DonorId": donor_id,
    }

    # Remove None values
    parameters = {k: v for k, v in parameters.items() if v is not None}

    result = await execute_stored_procedure(
        session=session,
        procedure_name="[dbo].[UIQueryGetTransactions]",
        parameters=parameters,
        fetch_results=True,
        fetch_multiple=False
    )

    transactions = result or []
    
    for txn in transactions:
        tax_receipts.append(TaxReceiptModel(
            year=int(txn.get("TaxYear")),  # type: ignore
            total_amount=float(txn.get("TotalDonation")),# type: ignore
            receipt_url=None,  # TODO: Generate receipt URL
            generated_date=txn.get("GeneratedDate"),# type: ignore
            status=txn.get("Status"),# type: ignore
        ))
    
    return tax_receipts


async def _get_donation_trends(
    session: AsyncSession,
    company_id: int,
    donor_id: int,
    period_type: str,
    months: int,
) -> DonationTrendModel:
    """Get donation trends over time."""
    now = datetime.now()
    start_date = now - timedelta(days=months * 30)
    
    # For monthly period, group by month
    if period_type == 'monthly':
        # Prepare parameters for stored procedure
        parameters = {
            "DataType": 4,            
            "CompanyId": company_id,
            "DonorId": donor_id,
            "StartDate": start_date,
            "EndDate": now,
        }

        # Remove None values
        parameters = {k: v for k, v in parameters.items() if v is not None}

        result = await execute_stored_procedure(
            session=session,
            procedure_name="[dbo].[UIQueryGetTransactions]",
            parameters=parameters,
            fetch_results=True,
            fetch_multiple=False
        )

        transactions = result or []
        data_points = []
        total = 0.0
        max_amount = 0.0
        for txn in transactions:
            donation_amount = float(txn.get("TotalDonation")) if txn.get("TotalDonation") else 0.0 # type: ignore
            donation_count = int(txn.get("CountDonation")) if txn.get("CountDonation") else 0 # type: ignore
            year = int(txn.get("DonationYear")) if txn.get("DonationYear") else now.year # type: ignore
            month = int(txn.get("DonationMonth")) if txn.get("DonationMonth") else now.month # type: ignore

            total += donation_amount
            if donation_amount > max_amount:
                max_amount = donation_amount
            date = datetime(year, month, 1)
            period_label = date.strftime('%b %Y')
            
            data_points.append(DonationTrendDataPointModel(
                period=period_label,
                amount=donation_amount,
                count=donation_count,
                date=date,
            ))
        
        average = total / len(data_points) if data_points else 0.0
        
        return DonationTrendModel(
            period_type='monthly',
            data_points=data_points,
            total_amount=total,
            average_amount=average,
            max_amount=max_amount,
        )
    
    # TODO: Implement daily and weekly grouping
    return DonationTrendModel(
        period_type=period_type,
        data_points=[],
        total_amount=0.0,
        average_amount=0.0,
        max_amount=0.0,
    )


async def _get_category_breakdown(
    session: AsyncSession,
    company_id: int,
    donor_id: int,
    period_type: str,
    months: int,
) -> list[DonationCategoryModel]:
    """Get donation breakdown by category/type."""
    category_breakdown = []

    now = datetime.now()
    start_date = now - timedelta(days=months * 30)

    parameters = {
        "DataType": 5,            
        "CompanyId": company_id,
        "DonorId": donor_id,
        "StartDate": start_date,
        "EndDate": now,
    }

    # Remove None values
    parameters = {k: v for k, v in parameters.items() if v is not None}

    result = await execute_stored_procedure(
        session=session,
        procedure_name="[dbo].[UIQueryGetTransactions]",
        parameters=parameters,
        fetch_results=True,
        fetch_multiple=False
    )

    transactions = result or []
    for idx, txn in enumerate(transactions):
        # Assign color from palette, cycling if more than 10 categories
        color = CATEGORY_COLOR_PALETTE[idx % len(CATEGORY_COLOR_PALETTE)]
        
        # Handle "Others" category (donationtype = -1) with a neutral gray color
        donation_type = txn.get("DonationType") # type: ignore
        if donation_type == -1:
            color = "#9CA3AF"  # Gray-400 for "Others"
        
        category_breakdown.append(DonationCategoryModel(
            category_id=donation_type,  # type: ignore
            category_name=txn.get("Description"),# type: ignore
            amount=float(txn.get("TotalDonation")),# type: ignore
            percentage=float(txn.get("PercentOfTotalDonation")),# type: ignore
            count=int(txn.get("CountDonation")),# type: ignore
            color=color,# type: ignore
        ))
    
    return category_breakdown

# def _get_impact_metrics_stub() -> list[ImpactMetricModel]:
#     """Stub for impact metrics - to be implemented."""
#     # TODO: Implement actual impact metrics based on aggregate donation data
#     return [
#         ImpactMetricModel(
#             metric_name="Community Members Helped",
#             value="1,250+",
#             description="Individuals supported through community programs",
#             icon="users",
#         ),
#         ImpactMetricModel(
#             metric_name="Programs Funded",
#             value="15",
#             description="Active community programs and initiatives",
#             icon="academic-cap",
#         ),
#         ImpactMetricModel(
#             metric_name="Total Community Impact",
#             value="$125,000+",
#             description="Total funds distributed to programs this year",
#             icon="currency-dollar",
#         ),
#     ]


# def _get_upcoming_events_stub(limit: int) -> list[UpcomingEventModel]:
#     """Stub for upcoming events - to be implemented."""
#     # TODO: Implement actual events from database
#     now = datetime.now()
#     return [
#         UpcomingEventModel(
#             event_id=1,
#             title="Ramadan Community Iftar",
#             date=now + timedelta(days=10),
#             location="Main Prayer Hall",
#             description="Join us for a community iftar dinner",
#             registration_required=True,
#             registration_url=None,
#         ),
#         UpcomingEventModel(
#             event_id=2,
#             title="Youth Center Grand Opening",
#             date=now + timedelta(days=25),
#             location="New Youth Center",
#             description="Celebrate the opening of our new youth facility",
#             registration_required=False,
#             registration_url=None,
#         ),
#     ][:limit]


# def _get_announcements_stub(limit: int) -> list[AnnouncementModel]:
#     """Stub for announcements - to be implemented."""
#     # TODO: Implement actual announcements from database
#     now = datetime.now()
#     return [
#         AnnouncementModel(
#             announcement_id=1,
#             title="Ramadan Campaign 2026",
#             message="Join us in making this Ramadan special. Our goal is to raise $50,000 for community programs.",
#             date_posted=now - timedelta(days=2),
#             priority="high",
#             category="campaign",
#         ),
#         AnnouncementModel(
#             announcement_id=2,
#             title="New Youth Center Opening",
#             message="Thanks to your generous donations, our new youth center will open next month!",
#             date_posted=now - timedelta(days=5),
#             priority="medium",
#             category="update",
#         ),
#     ][:limit]


def _create_empty_overview_response() -> DashboardOverviewResponse:
    """Create empty overview response for users without donor records."""
    empty_summary = DonationSummaryModel(
        start_date=datetime.min,
        end_date=datetime.max,
        total_amount=0.0,
        total_count=0,
        donation_count=0,
        donation_amount=0.0,
        average_donation=0.0,
        services_amount=0.0,
        services_count=0,
        trend_percentage=None,
        trend_direction=None,
    )
    
    return DashboardOverviewResponse(
        summary=DonationsByPeriodModel(
            this_month=empty_summary,
            this_year=empty_summary,
            lifetime=empty_summary,
            tax_year=empty_summary,
        ),
        recent_donations=[],
        recurring_donations=[],
        tax_receipts=[],
    )


def _create_empty_charts_response() -> DashboardChartsResponse:
    """Create empty charts response for users without donor records."""
    return DashboardChartsResponse(
        donation_trends=DonationTrendModel(
            period_type='monthly',
            data_points=[],
            total_amount=0.0,
            average_amount=0.0,
            max_amount=0.0,
        ),
        category_breakdown=[],
    )
