"""
Community endpoints for dashboard cards.

Provides hardcoded data for the Community Impact, Upcoming Events, and
Community Updates dashboard cards.  These endpoints are intended to be
the canonical source of truth once connected to the database; for now
they return static mock data that mirrors what is currently hard-coded
in the React components.

Endpoints:
    GET /api/v1/community/{company_id}/impact   - Community impact metrics
    GET /api/v1/community/{company_id}/events   - Upcoming events
    GET /api/v1/community/{company_id}/updates  - Community updates / news
"""

from fastapi import APIRouter, Depends

from src.config import settings
from src.core.logging import get_logger
from src.core.dependencies import User, get_current_user_required, get_current_user_optional
from src.models.community import (
    CommunityImpactMetric,
    CommunityImpactResponse,
    CommunityUpdate,
    CommunityUpdatesResponse,
    UpcomingEvent,
    UpcomingEventsResponse,
)
from src.providers.wix_events_provider import (
    WixEventsNotConfiguredError,
    WixEventsProvider,
)
from src.core.provider_config_utils import get_provider_config

router = APIRouter(prefix="/community", tags=["community"])
logger = get_logger(__name__, level=settings.LOG_LEVEL)


# ---------------------------------------------------------------------------
# Community Impact
# ---------------------------------------------------------------------------

@router.get(
    "/{company_id}/impact",
    response_model=CommunityImpactResponse,
    status_code=200,
    summary="Get community impact metrics",
    description=(
        "Returns community impact statistics for the given company. "
        "Currently returns hardcoded representative values. Requires authentication."
    ),
)
async def get_community_impact(
    company_id: int,
    current_user: User = Depends(get_current_user_optional),
) -> CommunityImpactResponse:
    """Return community impact metrics for the dashboard card."""
    logger.info("Community impact requested", extra={"company_id": company_id, "user": current_user.id if current_user else None})

    metrics = [
        CommunityImpactMetric(
            metric_name="Families Helped",
            value=1240,
            formatted_value="1,240",
            change_percent=18.0,
            change_label="+18% this month",
            icon="users",
        ),
        CommunityImpactMetric(
            metric_name="Meals Provided",
            value=3450,
            formatted_value="3,450",
            change_percent=25.0,
            change_label="+25% this month",
            icon="utensils",
        ),
        CommunityImpactMetric(
            metric_name="Students Supported",
            value=580,
            formatted_value="580",
            change_percent=12.0,
            change_label="+12% this month",
            icon="graduation-cap",
        ),
        CommunityImpactMetric(
            metric_name="Programs Funded",
            value=28,
            formatted_value="28",
            change_percent=0.0,
            change_label="8 active",
            icon="clipboard-list",
        ),
    ]

    return CommunityImpactResponse(
        company_id=company_id,
        metrics=metrics,
        last_updated=None,
    )


# ---------------------------------------------------------------------------
# Upcoming Events
# ---------------------------------------------------------------------------

@router.get(
    "/{company_id}/events",
    response_model=UpcomingEventsResponse,
    status_code=200,
    summary="Get upcoming events",
    description=(
        "Returns the list of upcoming mosque events, campaigns, and fundraisers. "
        "Currently returns hardcoded representative data. Requires authentication."
    ),
)
async def get_upcoming_events(
    company_id: int,
    current_user: User = Depends(get_current_user_optional),
) -> UpcomingEventsResponse:
    """Return upcoming events for the dashboard card, sourced from Wix Events.

    When Wix credentials (``WIX_API_KEY`` / ``WIX_SITE_ID``) are not
    configured, or when the Wix API call fails, the endpoint gracefully falls
    back to the hardcoded representative data so the dashboard card always has
    content to display.
    """
    logger.info("Upcoming events requested", extra={"company_id": company_id, "user": current_user.id if current_user else None})

    # ------------------------------------------------------------------
    # Try Wix Events API first
    # ------------------------------------------------------------------
    try:
        # get wix configuration from provider
        wix_config = await get_provider_config(company_id, "Wix")   
        if not wix_config or not wix_config.APIKey:
            raise WixEventsNotConfiguredError("Wix Events provider is not configured with API key")
        if not wix_config or not wix_config.MerchantId:
            raise WixEventsNotConfiguredError("Wix Events provider is not configured with Site ID") 
        
        async with WixEventsProvider(api_key=wix_config.APIKey, site_id=wix_config.MerchantId) as provider:
            events = await provider.get_upcoming_events(limit=3)

        logger.info(
            "Serving events from Wix",
            extra={"company_id": company_id, "count": len(events)},
        )
        return UpcomingEventsResponse(
            company_id=company_id,
            events=events,
            total=len(events),
        )

    except WixEventsNotConfiguredError:
        logger.info(
            "Wix Events not configured — using hardcoded fallback data",
            extra={"company_id": company_id},
        )
    except Exception as exc:
        logger.warning(
            "Wix Events API call failed — using hardcoded fallback data",
            extra={"company_id": company_id, "error": str(exc)},
        )

    # ------------------------------------------------------------------
    # Fallback: hardcoded representative events
    # ------------------------------------------------------------------
    events = [
        UpcomingEvent(
            id="1",
            title="Daily Iftar - Ramadan 2026",
            short_description=(
                "Join us for daily iftar throughout Ramadan in the Social Hall. "
                "Enjoy a variety of traditional dishes and community fellowship."
            ),
                event_page_url="https://malv.org/events",
                image_url=None,
            date="2026-02-18",
            time="5:30 PM",
            location="Social Hall",
            type="event",
        ),
        UpcomingEvent(
            id="2",
            title="Weekend Iftar - Ramadan 2026",
            short_description=(
                "Join us for the weekend iftar throughout Ramadan in the Social Hall. "
                "Enjoy a variety of traditional dishes and community fellowship."
            ),
            event_page_url="https://malv.org/events",
            image_url=None,
            date="2026-02-21",
            time="5:30 PM",
            location="MALV Gymnasium",
            type="campaign",
        ),
        UpcomingEvent(
            id="3",
            title="Community Fundraiser Dinner",
            short_description=(
                "Join us for a special community fundraiser dinner. "
                "Enjoy a variety of traditional dishes and support our community initiatives."
            ),
            event_page_url="https://malv.org/events",
            image_url=None,
            date="2026-02-28",
            time="5:00 PM",
            location="MALV Gymnasium",
            type="fundraiser",
        ),
    ]

    return UpcomingEventsResponse(
        company_id=company_id,
        events=events,
        total=len(events),
    )


# ---------------------------------------------------------------------------
# Community Updates
# ---------------------------------------------------------------------------

@router.get(
    "/{company_id}/updates",
    response_model=CommunityUpdatesResponse,
    status_code=200,
    summary="Get community updates",
    description=(
        "Returns recent community news and announcements. "
        "Currently returns hardcoded representative data. Requires authentication."
    ),
)
async def get_community_updates(
    company_id: int,
    current_user: User = Depends(get_current_user_optional),
) -> CommunityUpdatesResponse:
    """Return community updates for the dashboard card."""
    logger.info("Community updates requested", extra={"company_id": company_id, "user": current_user.id if current_user else None})

    updates = [
        CommunityUpdate(
            id="1",
            title="Ramadan 2026 Schedule Announced",
            content=(
                "We are pleased to announce the full Ramadan 2026 prayer and iftar schedule. "
                "Daily iftars will be held in the Social Hall throughout the month."
            ),
            date="2026-02-18",
            category="announcement",
            author="Masjid Administration",
            is_pinned=True,
        ),
        # CommunityUpdate(
        #     id="2",
        #     title="Building Fund Reaches 75% of Goal",
        #     content=(
        #         "Alhamdulillah! Thanks to the generosity of our community, the building expansion "
        #         "fund has reached 75% of its $500,000 target."
        #     ),
        #     date="2026-01-10",
        #     category="achievement",
        #     author="Fund Committee",
        #     is_pinned=False,
        # ),
        # CommunityUpdate(
        #     id="3",
        #     title="New Weekend School Registration Open",
        #     content=(
        #         "Registration for the 2026 weekend Islamic school program is now open. "
        #         "Classes are available for ages 5–18."
        #     ),
        #     date="2026-01-05",
        #     category="news",
        #     author="Education Department",
        #     is_pinned=False,
        # ),
        CommunityUpdate(
            id="4",
            title="Food Pantry Volunteer Drive",
            content=(
                "We are looking for volunteers to help with our monthly food pantry distribution. "
                "Sign up through the community portal."
            ),
            date="2025-12-28",
            category="update",
            author="Community Services",
            is_pinned=False,
        ),
    ]

    return CommunityUpdatesResponse(
        company_id=company_id,
        updates=updates,
        total=len(updates),
    )
