"""
Pydantic schemas for Dashboard API responses.

These schemas define the structure of JSON responses for donor dashboard endpoints.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class DonationSummaryModel(BaseModel):
    """Summary statistics for donations in a period."""
    start_date: datetime = Field(..., description="Start date of the period")
    end_date: datetime = Field(..., description="End date of the period")
    total_amount: float = Field(..., description="Total Payment amount")    
    total_count: int = Field(..., description="Number of Payments")
    donation_amount: float = Field(..., description="Tax deductible amount")
    donation_count: int = Field(..., description="Number of tax deductible Payments")
    average_donation: float = Field(..., description="Average donation amount")
    services_amount: float = Field(..., description="Service fees amount")
    services_count: int = Field(..., description="Number of service fee Payments")
    trend_percentage: Optional[float] = Field(None, description="Percentage change from previous period")
    trend_direction: Optional[str] = Field(None, description="Trend direction: 'up', 'down', or 'stable'")


class DonationsByPeriodModel(BaseModel):
    """Donation statistics grouped by period."""
    this_month: DonationSummaryModel = Field(..., description="Current month statistics")
    this_year: DonationSummaryModel = Field(..., description="Current year statistics")
    lifetime: DonationSummaryModel = Field(..., description="Lifetime statistics")
    tax_year: DonationSummaryModel = Field(..., description="Tax year (YTD) statistics")


class DonationTrendDataPointModel(BaseModel):
    """Single data point for donation trends chart."""
    period: str = Field(..., description="Period label (e.g., 'Jan', 'Feb', 'Week 1')")
    amount: float = Field(..., description="Total amount for this period")
    count: int = Field(..., description="Number of donations in this period")
    date: datetime = Field(..., description="Date for this data point")


class DonationTrendModel(BaseModel):
    """Donation trend data for charts."""
    period_type: str = Field(..., description="Type of period: 'monthly', 'weekly', 'daily'")
    data_points: list[DonationTrendDataPointModel] = Field(..., description="Trend data points")
    total_amount: float = Field(..., description="Total amount across all periods")
    average_amount: float = Field(..., description="Average amount per period")
    max_amount: float = Field(..., description="Maximum amount in a single period")


class DonationCategoryModel(BaseModel):
    """Donation breakdown by category."""
    category_id: int = Field(..., description="Category/donation type ID")
    category_name: str = Field(..., description="Category/donation type name")
    amount: float = Field(..., description="Total amount for this category")
    percentage: float = Field(..., description="Percentage of total donations")
    count: int = Field(..., description="Number of donations in this category")
    color: Optional[str] = Field(None, description="Chart color for this category")


class RecentDonationModel(BaseModel):
    """Recent donation record."""
    transaction_id: int = Field(..., description="Transaction ID")
    date: datetime = Field(..., description="Transaction date")
    category_id: int = Field(..., description="Primary donation category/type ID")
    category_name: str = Field(..., description="Primary donation category/type name")
    amount: float = Field(..., description="Donation amount")
    payment_method: Optional[str] = Field(None, description="Payment method used")
    status: str = Field(..., description="Transaction status")
    receipt_url: Optional[str] = Field(None, description="URL to receipt/download")


class RecurringDonationModel(BaseModel):
    """Active recurring donation record."""
    transaction_id: int = Field(..., description="Transaction ID")
    subscription_id: str = Field(..., description="Subscription/recurring donation ID")
    amount: float = Field(..., description="Recurring donation amount")
    frequency: str = Field(..., description="Frequency: 'monthly', 'weekly', 'annually'")
    categories: list[str] = Field(..., description="Donation categories/types")
    start_date: datetime = Field(..., description="Start date of recurring donation")
    end_date: Optional[datetime] = Field(None, description="End date if applicable")    
    last_payment_date: Optional[datetime] = Field(None, description="Date of last payment made")
    next_payment_date: Optional[datetime] = Field(None, description="Next scheduled payment date")
    number_of_payments: Optional[int] = Field(None, description="Total number of payments made")
    remaining_payments: Optional[int] = Field(None, description="Number of payments remaining")
    status: str = Field(..., description="Status: 'active', 'paused', 'cancelled'")
    
    payment_method: Optional[str] = Field(None, description="Payment method")


class ImpactMetricModel(BaseModel):
    """Community impact metric."""
    metric_name: str = Field(..., description="Name of the impact metric")
    value: str = Field(..., description="Metric value (could be numeric or text)")
    description: str = Field(..., description="Description of the metric")
    icon: Optional[str] = Field(None, description="Icon identifier for display")


class UpcomingEventModel(BaseModel):
    """Upcoming community event."""
    event_id: int = Field(..., description="Event ID")
    title: str = Field(..., description="Event title")
    date: datetime = Field(..., description="Event date and time")
    location: Optional[str] = Field(None, description="Event location")
    description: Optional[str] = Field(None, description="Event description")
    registration_required: bool = Field(default=False, description="Whether registration is required")
    registration_url: Optional[str] = Field(None, description="Registration URL")


class AnnouncementModel(BaseModel):
    """Community announcement or update."""
    announcement_id: int = Field(..., description="Announcement ID")
    title: str = Field(..., description="Announcement title")
    message: str = Field(..., description="Announcement message")
    date_posted: datetime = Field(..., description="Date posted")
    priority: Optional[str] = Field(None, description="Priority level: 'high', 'medium', 'low'")
    category: Optional[str] = Field(None, description="Category of announcement")


class TaxReceiptModel(BaseModel):
    """Tax receipt information."""
    year: int = Field(..., description="Tax year")
    total_amount: float = Field(..., description="Total tax-deductible amount")
    receipt_url: Optional[str] = Field(None, description="URL to download receipt")
    generated_date: Optional[datetime] = Field(None, description="Date receipt was generated")
    status: str = Field(..., description="Receipt status: 'available', 'pending', 'unavailable'")


class DashboardOverviewResponse(BaseModel):
    """
    Comprehensive dashboard overview with all summary data.
    This endpoint groups related content for efficient loading.
    """
    summary: DonationsByPeriodModel = Field(..., description="Donation summary statistics")
    recent_donations: list[RecentDonationModel] = Field(..., description="Recent donation history")
    recurring_donations: list[RecurringDonationModel] = Field(..., description="Active recurring donations")
    tax_receipts: list[TaxReceiptModel] = Field(..., description="Available tax receipts")


class DashboardChartsResponse(BaseModel):
    """
    Chart data for dashboard visualizations.
    Grouped separately for efficient loading.
    """
    donation_trends: DonationTrendModel = Field(..., description="Donation trend over time")
    category_breakdown: list[DonationCategoryModel] = Field(..., description="Donations by category")


class DashboardCommunityResponse(BaseModel):
    """
    Community-related dashboard data.
    Grouped separately for efficient loading.
    """
    impact_metrics: list[ImpactMetricModel] = Field(..., description="Community impact metrics")
    upcoming_events: list[UpcomingEventModel] = Field(..., description="Upcoming events")
    announcements: list[AnnouncementModel] = Field(..., description="Recent announcements")
