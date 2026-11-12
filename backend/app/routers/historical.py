"""Historical weather analytics router — historical observations and trends.

Provides multi-day observation records from Microsoft Fabric Lakehouse.
"""

from datetime import date
from typing import Optional

import structlog
from fastapi import APIRouter, Query

from app.services.weather_service import WeatherService

router = APIRouter(prefix="/historical", tags=["historical"])
log = structlog.get_logger()
weather_service = WeatherService()


@router.get("", include_in_schema=False)
@router.get("/")
async def get_historical(
    district: Optional[str] = Query(None, description="Filter by district name"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
):
    """Get historical weather observation records.

    Returns daily temperature, rainfall, and humidity records
    supporting date range and district filtering.
    """
    log.info(
        "historical_requested",
        district=district,
        start_date=str(start_date) if start_date else None,
        end_date=str(end_date) if end_date else None,
    )
    return await weather_service.get_historical_data(
        district=district,
        start_date=start_date,
        end_date=end_date,
    )

