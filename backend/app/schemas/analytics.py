"""Analytics-related Pydantic schemas.

Models for aggregation results, trends, and statistical outputs.
"""

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TrendResult(BaseModel):
    """Result of a trend analysis."""

    direction: str = Field(..., description="Trend direction: increasing/decreasing/stable")
    change: float = Field(0.0, description="Absolute change value")
    start_value: Optional[float] = None
    end_value: Optional[float] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class AggregationResult(BaseModel):
    """Result of a numeric aggregation."""

    count: int = 0
    average: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    sum: Optional[float] = None


class DistrictAggregation(BaseModel):
    """Aggregated statistics for a single district."""

    district: str
    stats: AggregationResult


class DateAggregation(BaseModel):
    """Aggregated statistics for a single date."""

    date: date
    average: Optional[float] = None
    count: int = 0


class ComparisonResult(BaseModel):
    """Result of comparing two districts or time periods."""

    item_a: str
    item_b: str
    metric: str
    value_a: Optional[float] = None
    value_b: Optional[float] = None
    difference: Optional[float] = None
    pct_difference: Optional[float] = None


class AnalyticsResponse(BaseModel):
    """Standard envelope for analytics responses."""

    status: str = "success"
    analysis_type: str = Field(..., description="Type of analysis performed")
    data: Any = Field(default=None, description="Analysis results")
    metadata: Optional[Dict[str, Any]] = None
