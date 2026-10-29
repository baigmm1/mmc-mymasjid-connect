"""
Wix Events Provider — fetches upcoming events via POST /events/query.

Uses the Wix Events REST API v1 query endpoint which supports structured
filtering, sorting, and field projection.

Authentication:
    ``Authorization: <api_key>`` header + ``wix-site-id: <site_id>`` header.
    Both values come from application settings (``WIX_API_KEY`` / ``WIX_SITE_ID``).

Endpoint:
    POST  {WIX_API_BASE_URL}/events/query

Request body shape::

    {
        "query": {
            "filter": {"status": {"$eq": "SCHEDULED"}},
            "paging": {"limit": 20},
            "sort": [{"fieldName": "dateAndTimeSettings.startDate"}],
            "fields": ["DETAILS", "TEXTS", "CATEGORIES"],
            "includeDrafts": false
        }
    }

Mapping → UpcomingEvent:
    Wix field                                          → model field
    ────────────────────────────────────────────────── ────────────────────────
    event.id                                           → id
    event.title                                        → title
    event.dateAndTimeSettings.formatted.startDate      → date  (YYYY-MM-DD)
    event.dateAndTimeSettings.formatted.startTime      → time  (e.g. '5:00 PM')
    event.location.name                                → location
    event.categories.categories[].name                 → type  (best-effort)
    event.shortDescription                             → short_description
    event.mainImage.url                                → image_url
    event.eventPageUrl.base + .path                    → event_page_url
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx

from src.config import settings
from src.core.logging import get_logger
from src.models.community import EventType, UpcomingEvent

logger = get_logger(__name__, level=settings.LOG_LEVEL)

# ---------------------------------------------------------------------------
# Type mapping helpers
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Category → EventType mapping
# ---------------------------------------------------------------------------

_CATEGORY_KEYWORD_TO_TYPE: Dict[str, EventType] = {
    "fundraiser": "fundraiser",
    "fundraising": "fundraiser",
    "campaign": "campaign",
    "drive": "campaign",
}

_DEFAULT_EVENT_TYPE: EventType = "event"


def _resolve_event_type(event_data: Dict[str, Any]) -> EventType:
    """
    Best-effort mapping of Wix category names to our :data:`EventType` literals.

    The Wix query response nests categories as::

        event.categories.categories = [{"id": "…", "name": "Featured"}, …]

    Category names are checked for fundraiser/campaign keywords; defaults to
    ``"event"`` when nothing matches.
    """
    categories_wrapper = event_data.get("categories", {})
    category_list: List[Dict[str, Any]] = (
        categories_wrapper.get("categories", [])
        if isinstance(categories_wrapper, dict)
        else []
    )

    for cat in category_list:
        name = cat.get("name", "").lower()
        for keyword, mapped in _CATEGORY_KEYWORD_TO_TYPE.items():
            if keyword in name:
                return mapped

    return _DEFAULT_EVENT_TYPE


def _parse_formatted_date(formatted_date_str: Optional[str]) -> str:
    """
    Convert a Wix formatted date string (e.g. ``"February 28, 2026"``) to
    ``YYYY-MM-DD``.  Returns the raw string unchanged on parse failure.
    """
    if not formatted_date_str:
        return ""
    try:
        return datetime.strptime(formatted_date_str, "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return formatted_date_str


def _map_wix_event(event_data: Dict[str, Any]) -> UpcomingEvent:
    """
    Convert a single raw Wix event object (from the ``events/query`` response)
    to an :class:`UpcomingEvent`.

    Key response fields used::

        event.dateAndTimeSettings.formatted.startDate  → "February 28, 2026"
        event.dateAndTimeSettings.formatted.startTime  → "5:00 PM"
        event.location.name                            → "MALV Gymnasium"
        event.categories.categories[].name             → type mapping
        event.shortDescription                         → teaser text
        event.mainImage.url                            → cover image
        event.eventPageUrl.base + .path                → detail page link
    """
    # --- date / time (use Wix pre-formatted, timezone-localised strings) ---
    date_time_settings: Dict[str, Any] = event_data.get("dateAndTimeSettings", {})
    formatted: Dict[str, Any] = date_time_settings.get("formatted", {})
    display_date: str = _parse_formatted_date(formatted.get("startDate"))
    display_time: str = formatted.get("startTime", "")

    # --- location ---
    location_obj: Dict[str, Any] = event_data.get("location", {})
    location_name: str = (
        location_obj.get("name")
        or location_obj.get("address", {}).get("formattedAddress", "")
        or ""
    )

    # --- event page URL ---
    page_url_obj: Dict[str, Any] = event_data.get("eventPageUrl", {})
    base = page_url_obj.get("base", "").rstrip("/")
    path = page_url_obj.get("path", "")
    event_page_url: Optional[str] = f"{base}{path}" if base and path else None

    # --- cover image ---
    main_image: Dict[str, Any] = event_data.get("mainImage", {})
    image_url: Optional[str] = main_image.get("url") or None

    # --- short description ---
    short_desc: Optional[str] = event_data.get("shortDescription") or None
    if short_desc:
        short_desc = short_desc.strip() or None

    return UpcomingEvent(
        id=str(event_data.get("id", "")),
        title=event_data.get("title", "Untitled Event"),
        date=display_date,
        time=display_time,
        location=location_name,
        type=_resolve_event_type(event_data),
        short_description=short_desc,
        image_url=image_url,
        event_page_url=event_page_url,
    )


# ---------------------------------------------------------------------------
# Provider class
# ---------------------------------------------------------------------------

class WixEventsProvider:
    """
    Async HTTP client for the Wix Events REST API v1.

    Usage (as async context manager)::

        async with WixEventsProvider() as provider:
            events = await provider.get_upcoming_events(limit=10)

    You may also instantiate and close manually::

        provider = WixEventsProvider()
        try:
            events = await provider.get_upcoming_events()
        finally:
            await provider.close()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        site_id: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        """
        Initialise the provider.  Parameters fall back to application settings
        when not supplied explicitly.

        Args:
            api_key:  Wix API key (overrides ``WIX_API_KEY`` setting).
            site_id:  Wix site ID (overrides ``WIX_SITE_ID`` setting).
            base_url: API base URL (overrides ``WIX_API_BASE_URL`` setting).
        """
        self._api_key = api_key
        self._site_id = site_id
        self._base_url = (base_url or settings.WIX_API_BASE_URL).rstrip("/")

        self._client = httpx.AsyncClient(
            headers=self._build_headers(),
            timeout=15.0,
        )

        logger.info(
            "WixEventsProvider initialized",
            extra={
                "base_url": self._base_url,
                "site_id": self._site_id,
                "api_key_set": bool(self._api_key),
            },
        )

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "WixEventsProvider":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": f"MasjidConnect/{settings.API_VERSION} WixEventsProvider/1.0",
        }
        if self._api_key:
            headers["Authorization"] = self._api_key
        if self._site_id:
            headers["wix-site-id"] = self._site_id
        return headers

    def _raise_for_error(self, response: httpx.Response, operation: str) -> None:
        """Parse and raise a descriptive error from a non-2xx Wix API response."""
        try:
            body = response.json()
            message = body.get("message") or body.get("details", {}).get("description", "Unknown error")
        except Exception:
            message = response.text or "Unknown error"

        logger.error(
            "Wix API error",
            extra={
                "operation": operation,
                "status_code": response.status_code,
                "message": message,
            },
        )
        raise WixEventsError(
            f"Wix {operation} failed (HTTP {response.status_code}): {message}"
        )

    def is_configured(self) -> bool:
        """Return ``True`` when both ``api_key`` and ``site_id`` are present."""
        return bool(self._api_key and self._site_id)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_upcoming_events(
        self,
        limit: int = 20,
        status: str = "SCHEDULED",
        include_drafts: bool = False,
    ) -> List[UpcomingEvent]:
        """
        Fetch upcoming events via ``POST events/query`` and return them as
        :class:`UpcomingEvent` objects sorted by start-date ascending.

        Uses the Wix Events v1 query endpoint with a structured request body::

            {
                "query": {
                    "filter": {"status": {"$eq": "SCHEDULED"}},
                    "paging": {"limit": 20},
                    "sort": [{"fieldName": "dateAndTimeSettings.startDate"}],
                    "fields": ["DETAILS", "TEXTS", "CATEGORIES"],
                    "includeDrafts": false
                }
            }

        Args:
            limit:         Maximum number of events to return (default 20).
            status:        Wix event status filter; ``"SCHEDULED"`` returns
                           future events.  Use ``"UPCOMING"`` for events that
                           are published and not yet started.
            include_drafts: Whether to include draft events (default ``False``).

        Returns:
            List of :class:`UpcomingEvent` instances.

        Raises:
            WixEventsError: When the API returns a non-2xx response.
            WixEventsNotConfiguredError: When ``api_key`` or ``site_id`` is absent.
            httpx.RequestError: On network-level failures.
        """
        if not self.is_configured():
            raise WixEventsNotConfiguredError(
                "WixEventsProvider requires both WIX_API_KEY and WIX_SITE_ID "
                "to be configured in application settings."
            )

        url = f"{self._base_url}/events/query"

        body: Dict[str, Any] = {
            "query": {
                "filter": {
                    "status": {"$eq": status},
                },
                "paging": {
                    "limit": limit,
                },
                "sort": [
                    {"fieldName": "dateAndTimeSettings.startDate"},
                ],
                "fields": ["DETAILS", "TEXTS", "CATEGORIES"],
                "includeDrafts": include_drafts,
            }
        }

        logger.info(
            "Querying Wix events (POST events/query)",
            extra={"url": url, "limit": limit, "status": status},
        )

        try:
            response = await self._client.post(url, json=body)
        except httpx.RequestError as exc:
            logger.error("Network error querying Wix events", extra={"error": str(exc)})
            raise
        except Exception as exc:
            logger.error("Unexpected error querying Wix events - wix provider", extra={"error": str(exc)})
            raise

        if response.status_code != 200:
            self._raise_for_error(response, "get_upcoming_events")

        logger.info("Wix events query successful", extra={"status_code": response.status_code})
        payload = response.json()

        paging_meta = payload.get("pagingMetadata", {})
        raw_events: List[Dict[str, Any]] = payload.get("events", [])

        logger.info(f"Mapping {len(raw_events)} raw Wix events to UpcomingEvent models")
        mapped = [_map_wix_event(ev) for ev in raw_events]

        logger.info(
            "Wix events query complete",
            extra={
                "returned": len(mapped),
                "total_available": paging_meta.get("total"),
            },
        )

        return mapped

    async def get_event_by_id(self, event_id: str) -> UpcomingEvent:
        """
        Retrieve a single Wix event by its ID via ``POST events/query``
        with an ``id`` equality filter.

        Args:
            event_id: The Wix event identifier.

        Returns:
            An :class:`UpcomingEvent` instance.

        Raises:
            WixEventsError: On non-2xx responses or when the event is not found.
            WixEventsNotConfiguredError: When credentials are missing.
        """
        if not self.is_configured():
            raise WixEventsNotConfiguredError(
                "WixEventsProvider requires both WIX_API_KEY and WIX_SITE_ID."
            )

        url = f"{self._base_url}/events/query"

        body: Dict[str, Any] = {
            "query": {
                "filter": {"id": {"$eq": event_id}},
                "paging": {"limit": 1},
                "fields": ["DETAILS", "TEXTS", "CATEGORIES"],
                "includeDrafts": False,
            }
        }

        logger.info("Querying single Wix event", extra={"event_id": event_id})

        try:
            response = await self._client.post(url, json=body)
        except httpx.RequestError as exc:
            logger.error(
                "Network error querying Wix event",
                extra={"event_id": event_id, "error": str(exc)},
            )
            raise

        if response.status_code != 200:
            self._raise_for_error(response, f"get_event_by_id({event_id})")

        payload = response.json()
        raw_events: List[Dict[str, Any]] = payload.get("events", [])

        if not raw_events:
            raise WixEventsError(f"Event '{event_id}' not found in Wix.")

        return _map_wix_event(raw_events[0])


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class WixEventsError(Exception):
    """Raised when the Wix Events API returns a non-2xx response."""


class WixEventsNotConfiguredError(WixEventsError):
    """Raised when required Wix credentials are absent from application settings."""
