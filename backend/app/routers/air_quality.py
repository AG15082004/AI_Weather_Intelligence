"""Air quality router — AQI data for Tamil Nadu.

Provides air quality index readings and pollutant breakdowns.
"""

from datetime import date
from typing import Optional

import structlog
from fastapi import APIRouter, Query

from app.services.weather_service import WeatherService

router = APIRouter(prefix="/air-quality", tags=["air quality"])
log = structlog.get_logger()
weather_service = WeatherService()


@router.get("", include_in_schema=False)
@router.get("/")
async def get_air_quality(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    district: Optional[str] = Query(None, description="Filter by district name"),
):
    """Get air quality index (AQI) data for Tamil Nadu districts.

    Returns AQI readings, dominant pollutants, and health
    category classifications. Supports date range and district filters.
    """
    log.info(
        "air_quality_requested",
        start_date=str(start_date),
        end_date=str(end_date),
        district=district,
    )
    return await weather_service.get_air_quality(
        start_date=start_date, end_date=end_date, district=district
    )
