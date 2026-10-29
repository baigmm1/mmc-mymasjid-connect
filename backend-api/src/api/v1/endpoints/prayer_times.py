"""
Prayer Times Endpoints

API endpoints for prayer times from AthanPlus
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from src.models.prayer_times import PrayerTimesResponse
from src.services.prayer_times_service import get_prayer_times_service
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_session
from src.core.provider_manager import get_provider_config

router = APIRouter(prefix="/prayer-times", tags=["Prayer Times"])


@router.get("/{company_id}", response_model=PrayerTimesResponse)
async def get_prayer_times(
    company_id: int,    
    session: AsyncSession = Depends(get_session),
):
    """
    Get prayer times for the specified masjid
    
    Fetches and parses prayer times from AthanPlus API including:
    - Five daily prayers (Fajr, Dhuhr, Asr, Maghrib, Isha)
    - Adhan and Iqamah times
    - Sunrise time
    - Jumuah times
    - Next prayer indicator
    - Hijri date
    
    Args:
        masjid_id: AthanPlus masjid ID (default: ZyLj4YdQ)
        
    Returns:
        PrayerTimesResponse with all prayer times
        
    Raises:
        HTTPException: If fetching or parsing fails
    """
    try:
        provider_config = await get_provider_config(
            session=session,
            company_id=company_id,
            provider="AthanPlus"
        )
        masjid_id = "ZyLj4YdQ"

        if provider_config and provider_config.MerchantId:
            masjid_id = provider_config.MerchantId

        service = get_prayer_times_service(masjid_id)
        prayer_times = await service.fetch_prayer_times()
        return prayer_times
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch prayer times: {str(e)}"
        )


@router.get("/{company_id}/next", response_model=dict)
async def get_next_prayer(
    company_id: int,    
    session: AsyncSession = Depends(get_session),    
):
    """
    Get the next upcoming prayer only
    
    Args:
        masjid_id: AthanPlus masjid ID (default: ZyLj4YdQ)
        
    Returns:
        Dictionary with next prayer information
        
    Raises:
        HTTPException: If fetching fails or no next prayer found
    """
    try:
        provider_config = await get_provider_config(
            session=session,
            company_id=company_id,
            provider="AthanPlus"
        )
        masjid_id = "ZyLj4YdQ"

        if provider_config and provider_config.MerchantId:
            masjid_id = provider_config.MerchantId

        service = get_prayer_times_service(masjid_id)
        prayer_times = await service.fetch_prayer_times()
        
        # Find next prayer
        next_prayer = next((p for p in prayer_times.prayers if p.is_next), None)
        
        if not next_prayer:
            raise HTTPException(
                status_code=404,
                detail="No upcoming prayer found"
            )
        
        return {
            "prayer": next_prayer.model_dump(),
            "date": prayer_times.date,
            "hijri_date": prayer_times.hijri_date
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch next prayer: {str(e)}"
        )
