"""Districts router — district-specific weather data.

Provides detailed weather information for individual Tamil Nadu districts.
"""

from datetime import date
from typing import Optional

import structlog
from fastapi import APIRouter, Path, Query

from app.services.weather_service import WeatherService

router = APIRouter(prefix="/districts", tags=["districts"])
log = structlog.get_logger()
weather_service = WeatherService()


@router.get("", include_in_schema=False)
@router.get("/")
async def list_districts(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
):
    """List all 38 Tamil Nadu districts with basic weather info.

    Returns a summary list of all districts with their temperature
    and rainfall readings for the specified date range or latest snapshot.
    """
    log.info("districts_list_requested", start_date=str(start_date), end_date=str(end_date))
    return await weather_service.get_district_data(start_date=start_date, end_date=end_date)


@router.get("/{district_name}")
async def get_district_detail(
    district_name: str = Path(..., description="Name of the Tamil Nadu district"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
):
    """Get detailed weather data for a specific district.

    Returns comprehensive weather information including temperature,
    rainfall, humidity, and wind data for the specified district.
    """
    log.info(
        "district_detail_requested",
        district=district_name,
        start_date=str(start_date),
        end_date=str(end_date),
    )
    return await weather_service.get_district_data(
        district=district_name, start_date=start_date, end_date=end_date
    )
