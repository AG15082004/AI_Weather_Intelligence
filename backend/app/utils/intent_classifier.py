"""Intent classification and parameter extraction for Tamil Nadu Weather Intelligence.

Detects one of 15 supported intents, extracts target metrics, aggregations,
districts, and date windows with Pydantic validation.
"""

import json
import re
from typing import Any, Dict, Optional
import structlog

from app.schemas.ai import (
    AggregationType,
    DateRangeSpecification,
    ExtractedIntent,
    IntentType,
    MetricType,
)
from app.utils.date_extractor import extract_date_range
from app.utils.district_extractor import extract_districts

log = structlog.get_logger()

# Keyword and pattern mappings for supported intents
TYPO_REPLACEMENTS = [
    (r"\btemparature\b", "temperature"),
    (r"\btempature\b", "temperature"),
    (r"\btemperatue\b", "temperature"),
    (r"\brainfal\b", "rainfall"),
    (r"\brainfll\b", "rainfall"),
    (r"\bdistrct\b", "district"),
    (r"\bdistricts\b", "districts"),
    (r"\baverge\b", "average"),
    (r"\bhumidty\b", "humidity"),
]


def normalize_query_text(query: str) -> str:
    """Normalize common typos in user weather queries."""
    q = query
    for pat, rep in TYPO_REPLACEMENTS:
        q = re.sub(pat, rep, q, flags=re.IGNORECASE)
    return q


INTENT_PATTERNS = [
    # Dashboard generation requests
    (
        r"\b(build|generate|create|make|design)\b.*\b(dashboard|board|view)\b|\b(dashboard request|new dashboard)\b",
        "dashboard_request",
    ),
    # Missing observations / Data quality / completeness
    (
        r"\b(missing|unmeasured|data quality|gaps?|incomplete|unreported|null|completeness|missing observations?|missing data)\b",
        "data_quality_inquiry",
    ),
    # Monthly patterns / seasonality
    (
        r"\b(monthly|month by month|seasonal|seasonality|monthly patterns?|monthly trends?|monthly weather)\b",
        "monthly_patterns",
    ),
    # Weather bulletin / formal report
    (
        r"\b(bulletin|weather report|report for|comprehensive report|executive summary)\b",
        "weather_report",
    ),
    # Rankings (hottest, coldest, wettest, highest, lowest, top, rank, maximum, minimum)
    (
        r"\b(which district|what district|hottest|coldest|warmest|wettest|rainiest|highest|lowest|maximum|minimum|top\s*\d*|most rain|most rainfall|peak|rank|ranking)\b",
        "weather_ranking",
    ),
    # Date comparisons (compare today vs yesterday, this week vs last week)
    (
        r"\b(compare|diff|versus|vs)\b.*\b(today|yesterday|this week|last week|this month|last month|period)\b",
        "date_comparison",
    ),
    # District comparisons (compare X and Y)
    (
        r"\b(compare|comparison|versus|vs|difference between)\b",
        "district_comparison",
    ),
    # Weather trends
    (
        r"\b(trend|trends|over time|trajectory|history of|pattern|hourly change)\b",
        "weather_trend",
    ),
    # District intelligence / profile (coordinates, elevation, geography, climate zone)
    (
        r"\b(profile|elevation|coordinates|latitude|longitude|agro-climatic|climate zone|tell me about .* climate)\b",
        "district_intelligence",
    ),
    # Statewide summary / overview / average across TN
    (
        r"\b(statewide|state wide|overall|summary|whole state|across tamil nadu|across tn|entire state|average temperature across|average across|state average)\b",
        "statewide_summary",
    ),
    # Air Quality analysis
    (
        r"\b(aqi|air quality|pollution|pm2\.5|pm10|pollutant|smog|unhealthy air|cleanest air)\b",
        "air_quality_analysis",
    ),
    # Rainfall analysis
    (
        r"\b(rain|rainfall|precipitation|monsoon|shower|drizzle|dry day|rainy day|mm of rain)\b",
        "rainfall_analysis",
    ),
    # Temperature analysis
    (
        r"\b(temp|temperature|heat|hot|cold|degrees?|celsius|°c|feels like)\b",
        "temperature_analysis",
    ),
    # Historical weather
    (
        r"\b(historical|history|archives?|in the past|back in|on 2026-|was the weather)\b",
        "historical_weather",
    ),
    # Current weather
    (
        r"\b(current|currently|now|live|present condition|today's weather|weather today|weather right now|how is the weather)\b",
        "current_weather",
    ),
]

METRIC_PATTERNS = [
    (r"\b(aqi|air quality|pm2\.5|pm10|pollution|cleanest|polluted)\b", "air_quality"),
    (r"\b(rain|rainfall|precipitation|monsoon|shower|wet|wettest)\b", "rainfall"),
    (r"\b(temp|temperature|temparature|heat|hot|hottest|cold|coldest|warm|warmest|degree|celsius|°c|feels like)\b", "temperature"),
    (r"\b(humidity|relative humidity|moisture)\b", "humidity"),
    (r"\b(wind|wind speed|gust|breeze)\b", "wind"),
]

NON_WEATHER_PATTERNS = [
    r"\b(cricket|football|match|score|election|politics|movie|actor|cinema|capital of|who is|stock market|bitcoin)\b"
]


def classify_intent_rule_based(query: str) -> ExtractedIntent:
    """Fast, accurate rule-based classification into supported intents."""
    normalized_q = normalize_query_text(query.strip())
    q_clean = normalized_q
    q_lower = q_clean.lower()

    # 1. Non-weather intent check
    if any(re.search(pat, q_lower) for pat in NON_WEATHER_PATTERNS):
        return ExtractedIntent(
            intent="unknown_intent",
            metric="general",
            aggregation="current",
            confidence=0.95,
            raw_query=q_clean,
        )

    # 2. Extract entities
    districts = extract_districts(q_clean)
    primary_district = districts[0] if districts else None
    date_range = extract_date_range(q_clean)

    # 3. Detect Metric
    metric: MetricType = "general"
    for pat, m in METRIC_PATTERNS:
        if re.search(pat, q_lower):
            metric = m  # type: ignore
            break

    # 4. Multi-district comparison check: if multiple districts found and comparison keyword present
    if len(districts) >= 2 or (
        ("compare" in q_lower or "vs" in q_lower or "versus" in q_lower)
        and districts
    ):
        return ExtractedIntent(
            intent="district_comparison",
            metric=metric if metric != "general" else "temperature",
            aggregation="comparison",
            district=primary_district,
            districts=districts,
            date_range=date_range,
            confidence=0.95,
            raw_query=q_clean,
        )

    # 5. Detect Intent from patterns
    detected_intent: IntentType = "general_weather_question"
    for pat, intent_name in INTENT_PATTERNS:
        if re.search(pat, q_lower):
            detected_intent = intent_name  # type: ignore
            break

    # 6. Specific refinements for rankings and aggregations
    aggregation: AggregationType = "current"
    sort_order = None

    if detected_intent == "weather_ranking":
        if any(w in q_lower for w in ["hottest", "highest", "warmest", "max", "maximum", "peak", "most rain", "top"]):
            sort_order = "descending"
            aggregation = "maximum"
        elif any(w in q_lower for w in ["coldest", "lowest", "min", "minimum", "least", "bottom"]):
            sort_order = "ascending"
            aggregation = "minimum"
        else:
            sort_order = "descending"
            aggregation = "ranking"

        if metric == "general":
            if any(w in q_lower for w in ["rain", "wet", "precipitation"]):
                metric = "rainfall"
            elif any(w in q_lower for w in ["aqi", "pollution", "air"]):
                metric = "air_quality"
            else:
                metric = "temperature"

    elif detected_intent == "weather_trend":
        aggregation = "trend"
    elif detected_intent in ("district_comparison", "date_comparison"):
        aggregation = "comparison"
    elif detected_intent == "statewide_summary":
        aggregation = "average"
    elif detected_intent == "monthly_patterns":
        aggregation = "trend"
    elif detected_intent == "data_quality_inquiry":
        aggregation = "current"

    # If general intent with a specific district and no special keywords, treat as current weather or historical based on date
    if detected_intent == "general_weather_question" and primary_district:
        if date_range.preset in ("today",) and not date_range.is_explicit:
            detected_intent = "current_weather"
        elif date_range.preset in ("yesterday", "last_7_days", "custom", "all_available"):
            detected_intent = "historical_weather"

    return ExtractedIntent(
        intent=detected_intent,
        metric=metric,
        aggregation=aggregation,
        district=primary_district,
        districts=districts,
        date_range=date_range,
        sort_order=sort_order,  # type: ignore
        confidence=0.9,
        raw_query=q_clean,
    )

