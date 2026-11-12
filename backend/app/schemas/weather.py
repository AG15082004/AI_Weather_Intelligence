"""Weather-related Pydantic schemas.

Models matching actual Microsoft Fabric Lakehouse schemas, date-intelligence contracts,
and data-quality metrics.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TemperatureTrendItem(BaseModel):
    """Daily or aggregated temperature point."""

    date: str
    district: Optional[str] = None
    max_temp: Optional[float] = None
    min_temp: Optional[float] = None
    avg_temp: Optional[float] = None


class RainfallTrendItem(BaseModel):
    """Daily or monthly rainfall point with explicit quality indicators."""

    date: str
    district: Optional[str] = None
    rainfall_mm: Optional[float] = None  # None when missing/unreported (never silently converted to 0)
    cumulative_mm: Optional[float] = None
    category: str = "Unmeasured"  # Dry, Light, Moderate, Heavy, or Unmeasured
    status: str = "missing"       # measured_zero, measured_positive, missing
    is_rainy_day: Optional[bool] = None


class DistrictComparisonItem(BaseModel):
    """District-level aggregated meteorological metrics."""

    district: str
    avg_temp: Optional[float] = None
    max_temp: Optional[float] = None
    min_temp: Optional[float] = None
    total_rainfall: Optional[float] = None  # None if missing
    avg_humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    current_temp: Optional[float] = None
    current_condition: Optional[str] = None
    zone: Optional[str] = None


class RainfallQualityMetadata(BaseModel):
    """Data completeness and quality statistics for rainfall measurements."""

    total_days: int = 0
    measured_days: int = 0
    missing_days: int = 0
    measured_zero_days: int = 0
    positive_rainfall_days: int = 0
    completeness_pct: float = 0.0
    status: str = "incomplete"  # complete, partial, unmeasured
    has_positive_rain: bool = False


class WeatherOverviewData(BaseModel):
    """Payload for statewide weather overview."""

    districts_covered: int = 38
    avg_temperature: Optional[float] = None
    max_temperature: Optional[float] = None
    min_temperature: Optional[float] = None
    total_rainfall: Optional[float] = None  # None if all measurements are missing
    avg_humidity: Optional[float] = None
    active_alerts: int = 0
    latest_observation: Optional[str] = None
    rainfall_quality: Optional[RainfallQualityMetadata] = None
    temperature_trend: List[TemperatureTrendItem] = []
    rainfall_trend: List[RainfallTrendItem] = []
    district_comparison: List[DistrictComparisonItem] = []


class CurrentWeatherItem(BaseModel):
    """Current or historical timestamped weather reading for a district."""

    district: str
    temperature: float
    feels_like: float
    humidity: float
    wind_speed: float
    wind_direction: str
    pressure: float
    condition: str
    last_updated: str
    observation_date: Optional[str] = None
    precipitation_mm: Optional[float] = 0.0
    uv_index: Optional[float] = None
    cloud_cover: Optional[float] = None
    visibility_km: Optional[float] = None
    source: Optional[str] = None


class AirQualityItem(BaseModel):
    """Air quality metrics and classifications for a district."""

    district: str
    aqi: int
    category: str
    pm25: float
    pm10: float
    co: float
    no2: float
    so2: float
    o3: float
    us_epa_index: int
    us_epa_category: str
    gb_defra_index: int
    gb_defra_category: str
    dominant_pollutant: Optional[str] = None
    last_updated: str


class MetricDelta(BaseModel):
    """Metric change and percentage difference between two comparison periods."""

    current_val: Optional[float] = None
    previous_val: Optional[float] = None
    absolute_change: Optional[float] = None
    percentage_change: Optional[float] = None
    direction: str = "neutral"  # up, down, neutral, unavailable
    unit: str = ""


class PeriodComparisonData(BaseModel):
    """Comparative analysis across two time windows."""

    period_a_label: str
    period_b_label: str
    period_a_range: Dict[str, str]
    period_b_range: Dict[str, str]
    district: Optional[str] = "Statewide"
    temperature: MetricDelta
    rainfall: MetricDelta
    humidity: MetricDelta


class DataReliabilityMetadata(BaseModel):
    """Data source reliability and freshness metadata."""

    data_source: str = "microsoft_fabric"
    data_status: str = "LIVE"  # LIVE, CACHED, FALLBACK, UNAVAILABLE
    last_successful_refresh: Optional[str] = None
    latest_observation_timestamp: Optional[str] = None
    data_age_seconds: Optional[float] = None
    is_stale: bool = False
    warning: Optional[str] = None


class StandardResponse(BaseModel):
    """Standardized API response wrapper."""

    status: str = "success"
    data: Any
    message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    data_source: Optional[str] = None
    data_status: Optional[str] = None
    last_successful_refresh: Optional[str] = None
    data_age_seconds: Optional[float] = None
    is_stale: Optional[bool] = None
    warning: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
