"""Natural language date extraction and resolution into strict Asia/Kolkata (IST) windows.

Integrates with app.utils.date_utils for official platform timezone boundaries.
"""

import re
from datetime import date
from typing import Optional, Tuple
from app.schemas.ai import DateRangeSpecification
from app.utils.date_utils import (
    get_ist_today,
    get_ist_yesterday,
    get_preset_date_range,
    validate_date_range,
)

PRESET_PATTERNS = [
    (r"\b(today|currently|current|now|present|live)\b", "today"),
    (r"\b(yesterday|previous day|last day)\b", "yesterday"),
    (r"\b(last 7 days|past 7 days|last week|past 7d|7 days)\b", "last_7_days"),
    (r"\b(last 15 days|past 15 days|15 days)\b", "last_15_days"),
    (r"\b(last 30 days|past 30 days|last 30d|30 days)\b", "last_30_days"),
    (r"\b(last 90 days|past 90 days|90 days|3 months)\b", "last_90_days"),
    (r"\b(this week|current week)\b", "this_week"),
    (r"\b(last week|previous week)\b", "last_week"),
    (r"\b(this month|current month)\b", "this_month"),
    (r"\b(last month|previous month)\b", "last_month"),
    (r"\b(this year|current year)\b", "this_year"),
    (r"\b(all data|all time|all available|overall history|entire record)\b", "all_available"),
]

ISO_DATE_REGEX = re.compile(r"\b(202[0-9]-[0-1][0-9]-[0-3][0-9])\b")


def extract_date_range(text: str) -> DateRangeSpecification:
    """Extract and resolve date range from query into validated IST boundaries."""
    if not text:
        # Default to today's current weather if no date specified
        today = get_ist_today()
        return DateRangeSpecification(preset="today", start_date=today, end_date=today, is_explicit=False)

    text_lower = text.lower()

    # 1. Check for explicit ISO dates YYYY-MM-DD
    iso_matches = ISO_DATE_REGEX.findall(text)
    if len(iso_matches) >= 2:
        try:
            d1 = date.fromisoformat(iso_matches[0])
            d2 = date.fromisoformat(iso_matches[1])
            start, end = (d1, d2) if d1 <= d2 else (d2, d1)
            # Enforce validation
            validate_date_range(start, end)
            return DateRangeSpecification(preset="custom", start_date=start, end_date=end, is_explicit=True)
        except Exception:
            pass
    elif len(iso_matches) == 1:
        try:
            d = date.fromisoformat(iso_matches[0])
            validate_date_range(end_date=d)
            return DateRangeSpecification(preset="custom", start_date=d, end_date=d, is_explicit=True)
        except Exception:
            pass

    # 2. Check for natural language presets
    for pattern, preset_key in PRESET_PATTERNS:
        if re.search(pattern, text_lower):
            start, end = get_preset_date_range(preset_key)
            return DateRangeSpecification(preset=preset_key, start_date=start, end_date=end, is_explicit=True)

    # 3. Default fallback: Today
    today = get_ist_today()
    return DateRangeSpecification(preset="today", start_date=today, end_date=today, is_explicit=False)

