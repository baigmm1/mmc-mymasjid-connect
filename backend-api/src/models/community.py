"""
Community Pydantic schemas.

Models for the community dashboard card endpoints:
  - Community Impact metrics
  - Upcoming Events
  - Community Updates
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Community Impact
# ---------------------------------------------------------------------------

class CommunityImpactMetric(BaseModel):
    """A single community impact metric."""

    metric_name: str = Field(..., description="Display name of the metric")
    value: int = Field(..., description="Current value")
    formatted_value: str = Field(..., description="Human-readable value (e.g. '1,240')")
    change_percent: float = Field(..., description="Percentage change vs prior period")
    change_label: str = Field(..., description="Human-readable change label (e.g. '+18% this month')")
    icon: Optional[str] = Field(None, description="Icon identifier used by the frontend")

    model_config = {"from_attributes": True, "populate_by_name": True}


class CommunityImpactResponse(BaseModel):
    """Response for the community impact endpoint."""

    company_id: int
    metrics: List[CommunityImpactMetric]
    last_updated: Optional[datetime] = None

    model_config = {"from_attributes": True, "populate_by_name": True}


# ---------------------------------------------------------------------------
# Upcoming Events
# ---------------------------------------------------------------------------

EventType = Literal["fundraiser", "event", "campaign"]


class UpcomingEvent(BaseModel):
    """A single upcoming event."""

    id: str = Field(..., description="Unique event identifier")
    title: str
    date: str = Field(..., description="ISO 8601 date string (YYYY-MM-DD)")
    time: str = Field(..., description="Display time string (e.g. '6:30 PM')")
    location: str
    type: EventType
    # Optional enrichment fields sourced from Wix Events
    short_description: Optional[str] = Field(None, description="Short event description / teaser text")
    image_url: Optional[str] = Field(None, description="URL of the event's main cover image")
    event_page_url: Optional[str] = Field(None, description="Full URL to the event detail page (open in new window)")

    model_config = {"from_attributes": True, "populate_by_name": True}


class UpcomingEventsResponse(BaseModel):
    """Response for the upcoming events endpoint."""

    company_id: int
    events: List[UpcomingEvent]
    total: int = Field(..., description="Total number of events returned")

    model_config = {"from_attributes": True, "populate_by_name": True}


# ---------------------------------------------------------------------------
# Community Updates
# ---------------------------------------------------------------------------

UpdateCategory = Literal["announcement", "achievement", "news", "update"]


class CommunityUpdate(BaseModel):
    """A single community update / news item."""

    id: str = Field(..., description="Unique update identifier")
    title: str
    content: str = Field(..., description="Short summary or body text")
    date: str = Field(..., description="ISO 8601 date string (YYYY-MM-DD)")
    category: UpdateCategory
    author: Optional[str] = None
    is_pinned: bool = Field(False, description="Whether this update is pinned to the top")

    model_config = {"from_attributes": True, "populate_by_name": True}


class CommunityUpdatesResponse(BaseModel):
    """Response for the community updates endpoint."""

    company_id: int
    updates: List[CommunityUpdate]
    total: int = Field(..., description="Total number of updates returned")

    model_config = {"from_attributes": True, "populate_by_name": True}
