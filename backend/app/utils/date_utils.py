"""Date and timezone utilities for Tamil Nadu Weather Intelligence Platform.

Strictly enforces Asia/Kolkata (IST) timezone rules and validation for all weather queries.
"""

from datetime import date, datetime, timedelta
from typing import Optional, Tuple
from zoneinfo import ZoneInfo
from fastapi import HTTPException
import structlog

log = structlog.get_logger()

# Official platform timezone: Asia/Kolkata (IST = UTC + 5:30)
try:
    IST_TZ = ZoneInfo("Asia/Kolkata")
except Exception as _tz_err:
    log.error("zoneinfo_asia_kolkata_missing", error=str(_tz_err))
    # Raise informative error pointing to tzdata requirement on Windows
    raise RuntimeError(
        "Required IANA timezone 'Asia/Kolkata' not found. "
        "Please ensure 'tzdata' package is installed in your Python environment: pip install tzdata"
    ) from _tz_err


def validate_timezone_support() -> bool:
    """Validate that Asia/Kolkata timezone is available and functional at startup."""
    try:
        now_ist = datetime.now(IST_TZ)
        log.info(
            "timezone_validated",
            timezone="Asia/Kolkata",
            current_ist=now_ist.strftime("%Y-%m-%d %H:%M:%S %Z"),
            tz_offset=str(now_ist.utcoffset()),
        )
        return True
    except Exception as exc:
        log.critical("timezone_validation_failed", error=str(exc))
        raise RuntimeError(f"Startup timezone validation failed for Asia/Kolkata: {exc}") from exc

# Lakehouse historical observation boundaries
LAKEHOUSE_MIN_DATE = date(2026, 1, 1)
LAKEHOUSE_MAX_HISTORICAL_DATE = date(2026, 11, 3)


def get_ist_now() -> datetime:
    """Get current datetime in Asia/Kolkata timezone."""
    return datetime.now(IST_TZ)


def get_ist_today() -> date:
    """Get today's calendar date in Asia/Kolkata timezone."""
    return get_ist_now().date()


def get_ist_yesterday() -> date:
    """Get yesterday's calendar date in Asia/Kolkata timezone."""
    return get_ist_today() - timedelta(days=1)


def validate_date_range(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    allow_future: bool = False,
) -> Tuple[Optional[date], Optional[date]]:
    """Validate date range for weather queries.
    
    Rules:
    1. start_date must not be greater than end_date.
    2. end_date must not exceed today's calendar date in IST unless allow_future=True.
    
    Raises:
        HTTPException(status_code=400): If any validation rule is violated.
    """
    today = get_ist_today()

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date range: start_date ({start_date}) cannot be greater than end_date ({end_date}).",
        )

    if not allow_future:
        if end_date and end_date > today:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date: end_date ({end_date}) cannot be in the future (today is {today} IST).",
            )
        if start_date and start_date > today:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date: start_date ({start_date}) cannot be in the future (today is {today} IST).",
            )

    return start_date, end_date


def get_preset_date_range(preset_name: str) -> Tuple[date, date]:
    """Calculate exact date boundary for the 13 supported presets in IST."""
    today = get_ist_today()
    preset = preset_name.lower().strip()

    if preset == "today":
        return today, today

    elif preset == "yesterday":
        y = today - timedelta(days=1)
        return y, y

    elif preset in ("last_7_days", "7d"):
        # Today and six preceding calendar dates (7 days inclusive)
        return today - timedelta(days=6), today

    elif preset in ("last_15_days", "15d"):
        return today - timedelta(days=14), today

    elif preset in ("last_30_days", "30d"):
        # Today and 29 preceding calendar dates (30 days inclusive)
        return today - timedelta(days=29), today

    elif preset in ("last_90_days", "90d"):
        return today - timedelta(days=89), today

    elif preset == "this_week":
        # Monday of current week through today
        start_of_week = today - timedelta(days=today.weekday())
        return start_of_week, today

    elif preset == "last_week":
        # Previous Monday through Sunday
        start_of_last_week = today - timedelta(days=today.weekday() + 7)
        end_of_last_week = start_of_last_week + timedelta(days=6)
        return start_of_last_week, end_of_last_week

    elif preset == "this_month":
        # First day of current month through today
        start_of_month = today.replace(day=1)
        return start_of_month, today

    elif preset == "last_month":
        # First through last day of previous month
        first_of_this_month = today.replace(day=1)
        last_of_last_month = first_of_this_month - timedelta(days=1)
        first_of_last_month = last_of_last_month.replace(day=1)
        return first_of_last_month, last_of_last_month

    elif preset == "this_year":
        # January 1 through today
        return today.replace(month=1, day=1), today

    elif preset in ("all_data", "all_available", "all"):
        # Earliest through latest available observation in Lakehouse
        return LAKEHOUSE_MIN_DATE, today

    else:
        # Default to last 7 days
        return today - timedelta(days=6), today


# Alias for backward and test compatibility
get_preset_boundaries = get_preset_date_range
