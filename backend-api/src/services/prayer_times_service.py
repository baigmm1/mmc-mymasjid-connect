"""
Prayer Times Service

Service for fetching and parsing prayer times from AthanPlus API
"""

import httpx
from bs4 import BeautifulSoup
from datetime import datetime, time as dt_time
from typing import Optional
import re
from src.core.logging import get_logger
from src.config import settings

# Try to import zoneinfo, fallback to pytz if not available
try:
    from zoneinfo import ZoneInfo
    USE_ZONEINFO = True
except ImportError:
    try:
        import pytz
        USE_ZONEINFO = False
    except ImportError:
        raise ImportError("Either zoneinfo (Python 3.9+) or pytz must be available")

from src.models.prayer_times import PrayerTime, PrayerTimesResponse, JumuahTime
logger = get_logger(__name__, level=settings.LOG_LEVEL)

class PrayerTimesService:
    """Service to fetch prayer times from AthanPlus"""
    
    def __init__(self, masjid_id: str = "ZyLj4YdQ"):
        """
        Initialize prayer times service
        
        Args:
            masjid_id: AthanPlus masjid ID (default: ZyLj4YdQ)
        """
        self.masjid_id = masjid_id
        self.base_url = "https://timing.athanplus.com/masjid/widgets/embed"
    
    async def fetch_prayer_times(self) -> PrayerTimesResponse:
        """
        Fetch and parse prayer times from AthanPlus
        
        Returns:
            PrayerTimesResponse with parsed prayer times
        
        Raises:
            httpx.HTTPError: If request fails
            ValueError: If parsing fails
        """
        url = f"{self.base_url}?theme=1&masjid_id={self.masjid_id}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            return self._parse_prayer_times(response.text)
    
    def _parse_prayer_times(self, html: str) -> PrayerTimesResponse:
        """
        Parse prayer times from HTML response
        
        Args:
            html: HTML content from AthanPlus
            
        Returns:
            Parsed PrayerTimesResponse
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract date - look for h2 that contains day of week and date
        date_text = ""
        hijri_date = None
        
        # Find all h2 elements and look for the one with the date pattern
        h2_elements = soup.find_all('h2')
        for h2 in h2_elements:
            text = h2.get_text(strip=True)
            # Look for pattern like "Thursday, Feb 5, 2026"
            if re.search(r'\w+,\s+\w+\s+\d+,\s+\d{4}', text):
                date_text = text
                # Try to find hijri date in next element
                next_elem = h2.find_next_sibling()
                if next_elem:
                    hijri_text = next_elem.get_text(strip=True)
                    # Look for pattern like "Shaban 17, 1447"
                    if re.search(r'\w+\s+\d+,\s+\d{4}', hijri_text):
                        hijri_date = hijri_text
                break
        
        # Find prayer times table
        table = soup.find('table')
        if not table:
            raise ValueError("Could not find prayer times table")
        
        prayers = []
        sunrise_time = None
        jumuah_times = []
        
        # Parse table rows
        rows = table.find_all('tr')[1:]  # Skip header row
        next_prayer_idx = None
        
        # Get current EST time for comparison
        logger.info(f"Determining current time in EST for prayer time comparison - using {'zoneinfo' if USE_ZONEINFO else 'pytz'}")
        try:
            if USE_ZONEINFO:
                est_tz = ZoneInfo("America/New_York")
                now_est = datetime.now(est_tz)
            else:
                est_tz = pytz.timezone("America/New_York")
                now_est = datetime.now(est_tz)
        except Exception as e:
            logger.warning(f"Failed to get EST timezone, falling back to pytz: {e}")
            # Fallback to pytz if zoneinfo fails (e.g., missing tzdata on Windows)
            est_tz = pytz.timezone("America/New_York")
            now_est = datetime.now(est_tz)
        
        current_time_est = now_est.time()
        logger.info(f"Current EST time: {current_time_est}")

        for idx, row in enumerate(rows):
            cols = row.find_all('td')
            if len(cols) < 2:
                continue
            
            prayer_name = cols[0].get_text(strip=True)
            starts_time = cols[1].get_text(strip=True)
            iqamah_time = cols[2].get_text(strip=True) if len(cols) > 2 else starts_time
            
            # Handle Sunrise (not a prayer)
            if prayer_name.lower() == 'sunrise':
                sunrise_time = starts_time
                continue
            
            # Determine if prayer has passed (using EST time)
            is_past = self._is_time_past(starts_time, current_time_est)
            
            # Track for finding next prayer
            if not is_past and next_prayer_idx is None:
                next_prayer_idx = len(prayers)
            
            prayers.append(PrayerTime(
                name=prayer_name,
                adhan_time=starts_time,
                iqamah_time=iqamah_time,
                is_past=is_past,
                is_next=False  # Will set below
            ))
        
        # Mark next prayer
        if next_prayer_idx is not None and next_prayer_idx < len(prayers):
            prayers[next_prayer_idx].is_next = True
        
        # Parse Jumuah times
        jumuah_section = soup.find(string=re.compile(r'Jumuah', re.IGNORECASE))
        if jumuah_section:
            jumuah_parent = jumuah_section.find_parent()
            if jumuah_parent:
                # Find all time elements after Jumuah heading
                time_elements = jumuah_parent.find_next_siblings()
                for elem in time_elements[:2]:  # Usually 2 Jumuah times
                    text = elem.get_text(strip=True)
                    # Extract time and name (e.g., "12:15 PM Jumuah 1")
                    time_match = re.search(r'(\d+:\d+\s*[AP]M)', text)
                    if time_match:
                        jumuah_time = time_match.group(1)
                        if 'Jumuah 1' in text or 'Jumuah1' in text:
                            name = "Jumuah 1"
                        elif 'Jumuah 2' in text or 'Jumuah2' in text:
                            name = "Jumuah 2"
                        else:
                            name = f"Jumuah {len(jumuah_times) + 1}"
                        
                        jumuah_times.append(JumuahTime(name=name, time=jumuah_time))
        
        # Extract next day changes
        next_day_changes = None
        changes_elem = soup.find(string=re.compile(r'from tomorrow', re.IGNORECASE))
        if changes_elem:
            next_day_changes = changes_elem.strip()
        
        return PrayerTimesResponse(
            date=date_text,
            hijri_date=hijri_date,
            prayers=prayers,
            jumuah=jumuah_times,
            sunrise=sunrise_time,
            next_day_changes=next_day_changes
        )
    
    def _is_time_past(self, time_str: str, current_time: dt_time) -> bool:
        """
        Check if a prayer time has passed
        
        Args:
            time_str: Time string (e.g., "5:51 AM")
            current_time: Current time to compare against
            
        Returns:
            True if the time has passed
        """
        try:
            # Parse time string
            time_str = time_str.strip()
            prayer_time = datetime.strptime(time_str, "%I:%M %p").time()
            return current_time > prayer_time
        except (ValueError, AttributeError):
            return False


# Global service instance
_prayer_service: Optional[PrayerTimesService] = None


def get_prayer_times_service(masjid_id: Optional[str] = None) -> PrayerTimesService:
    """
    Get prayer times service instance (singleton)
    
    Args:
        masjid_id: Optional masjid ID to use
        
    Returns:
        PrayerTimesService instance
    """
    global _prayer_service
    
    if _prayer_service is None or (masjid_id and masjid_id != _prayer_service.masjid_id):
        _prayer_service = PrayerTimesService(masjid_id=masjid_id or "ZyLj4YdQ")
    
    return _prayer_service
