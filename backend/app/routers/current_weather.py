"""Current weather router — real-time weather conditions.

Provides the latest weather readings for Tamil Nadu districts.
"""

from datetime import date
from typing import Optional

import structlog
from fastapi import APIRouter, Query

from app.services.weather_service import WeatherService

router = APIRouter(prefix="/current-weather", tags=["current weather"])
log = structlog.get_logger()
weather_service = WeatherService()


@router.get("", include_in_schema=False)
@router.get("/")
async def get_current_weather(
    district: Optional[str] = Query(None, description="Filter by district name"),
    date: Optional[date] = Query(None, description="Filter by observation date (YYYY-MM-DD)"),
):
    """Get current weather conditions across Tamil Nadu.

    Returns the most recent weather observations or historical day's actual observations.
    Optionally filter by a specific district or specific date.
    """
    log.info("current_weather_requested", district=district, date=str(date) if date else None)
    return await weather_service.get_current_weather(district=district, date_param=date)


weather_current_router = APIRouter(prefix="/weather/current", tags=["current weather"])


@weather_current_router.get("", include_in_schema=False)
@weather_current_router.get("/")
async def get_weather_current_alias(
    district: Optional[str] = Query(None, description="Filter by district name"),
    date: Optional[date] = Query(None, description="Filter by observation date (YYYY-MM-DD)"),
):
    """Compatibility alias endpoint for /api/weather/current."""
    return await get_current_weather(district=district, date=date)
