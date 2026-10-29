"""
Test script for prayer times service

Run with: python test_prayer_times.py
"""

import asyncio
import sys
sys.path.insert(0, 'src')

from src.services.prayer_times_service import PrayerTimesService


async def test_prayer_times():
    """Test fetching prayer times"""
    print("Testing Prayer Times Service...")
    print("=" * 60)
    
    service = PrayerTimesService(masjid_id="ZyLj4YdQ")
    
    try:
        result = await service.fetch_prayer_times()
        
        print(f"Date: {result.date}")
        print(f"Hijri Date: {result.hijri_date}")
        print(f"Sunrise: {result.sunrise}")
        print("\nPrayer Times:")
        print("-" * 60)
        
        for prayer in result.prayers:
            next_marker = " ← NEXT" if prayer.is_next else ""
            past_marker = " (PAST)" if prayer.is_past else ""
            print(f"{prayer.name:10s} | Adhan: {prayer.adhan_time:10s} | Iqamah: {prayer.iqamah_time:10s}{past_marker}{next_marker}")
        
        if result.jumuah:
            print("\nJumuah Times:")
            print("-" * 60)
            for jumuah in result.jumuah:
                print(f"{jumuah.name}: {jumuah.time}")
        
        if result.next_day_changes:
            print(f"\nNext Day Changes: {result.next_day_changes}")
        
        print("\n" + "=" * 60)
        print("✅ Prayer times fetched successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_prayer_times())
