"""Overview router — high-level weather summary for Tamil Nadu.

Provides aggregated state-wide weather overview data.
"""

from datetime import date
from typing import Optional

import structlog
from fastapi import APIRouter, Query

from app.services.weather_service import WeatherService

router = APIRouter(prefix="/overview", tags=["overview"])
log = structlog.get_logger()
weather_service = WeatherService()


@router.get("", include_in_schema=False)
@router.get("/")
async def get_overview(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
):
    """Get state-wide weather overview for Tamil Nadu.

    Returns high-level weather metrics including temperature averages,
    total rainfall, humidity, and active alerts across all districts.
    """
    log.info("overview_requested", start_date=str(start_date), end_date=str(end_date))
    return await weather_service.get_overview(start_date=start_date, end_date=end_date)


@router.get("/comparison")
async def get_overview_comparison(
    period_a_start: date = Query(..., description="Period A start date (YYYY-MM-DD)"),
    period_a_end: date = Query(..., description="Period A end date (YYYY-MM-DD)"),
    period_b_start: date = Query(..., description="Period B start date (YYYY-MM-DD)"),
    period_b_end: date = Query(..., description="Period B end date (YYYY-MM-DD)"),
    district: Optional[str] = Query(None, description="Filter by district name"),
):
    """Compare two weather periods (e.g., Today vs Yesterday, This Week vs Last Week).

    Returns delta calculations and percentage changes for temperature, rainfall, and humidity.
    """
    log.info(
        "overview_comparison_requested",
        period_a=f"{period_a_start}..{period_a_end}",
        period_b=f"{period_b_start}..{period_b_end}",
        district=district,
    )
    return await weather_service.compare_periods(
        period_a_start=period_a_start,
        period_a_end=period_a_end,
        period_b_start=period_b_start,
        period_b_end=period_b_end,
        district=district,
    )
