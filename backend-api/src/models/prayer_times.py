"""
Prayer Times Models

Pydantic models for prayer times data from AthanPlus API
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PrayerTime(BaseModel):
    """Individual prayer time"""
    name: str = Field(..., description="Prayer name (Fajr, Dhuhr, Asr, Maghrib, Isha)")
    adhan_time: str = Field(..., description="Adhan (call to prayer) time")
    iqamah_time: str = Field(..., description="Iqamah (congregation) time")
    is_past: bool = Field(False, description="Whether this prayer time has passed")
    is_next: bool = Field(False, description="Whether this is the next upcoming prayer")


class JumuahTime(BaseModel):
    """Jumuah prayer time"""
    name: str = Field(..., description="Jumuah name (Jumuah 1, Jumuah 2, etc)")
    time: str = Field(..., description="Jumuah time")


class PrayerTimesResponse(BaseModel):
    """Prayer times response"""
    date: str = Field(..., description="Prayer times date (e.g., 'Thursday, Feb 5, 2026')")
    hijri_date: Optional[str] = Field(None, description="Hijri date (e.g., 'Shaban 17, 1447')")
    prayers: list[PrayerTime] = Field(..., description="List of prayer times")
    jumuah: list[JumuahTime] = Field(default_factory=list, description="Jumuah times")
    sunrise: Optional[str] = Field(None, description="Sunrise time")
    next_day_changes: Optional[str] = Field(None, description="Next day timing changes")
