"""Rainfall router — precipitation data and trends.

Provides rainfall measurements and analysis for Tamil Nadu districts.
"""

from datetime import date
from typing import Optional

import structlog
from fastapi import APIRouter, Query

from app.services.weather_service import WeatherService

router = APIRouter(prefix="/rainfall", tags=["rainfall"])
log = structlog.get_logger()
weather_service = WeatherService()


@router.get("", include_in_schema=False)
@router.get("/")
async def get_rainfall_data(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    district: Optional[str] = Query(None, description="Filter by district name"),
):
    """Get rainfall data for Tamil Nadu districts.

    Returns precipitation levels, cumulative rainfall, and trend data.
    Supports filtering by date range and specific district.
    """
    log.info(
        "rainfall_requested",
        start_date=str(start_date),
        end_date=str(end_date),
        district=district,
    )
    return await weather_service.get_rainfall_data(
        start_date=start_date, end_date=end_date, district=district
    )
