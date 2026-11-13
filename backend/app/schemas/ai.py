"""AI Agent schemas — Pydantic models for intent classification, entity extraction,
conversational context, and grounded responses.
"""

from datetime import date
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

# 15 Supported Intents as per Phase 7 Specification
IntentType = Literal[
    "current_weather",
    "historical_weather",
    "temperature_analysis",
    "rainfall_analysis",
    "air_quality_analysis",
    "district_comparison",
    "statewide_summary",
    "weather_ranking",
    "date_comparison",
    "weather_trend",
    "district_intelligence",
    "weather_report",
    "dashboard_request",
    "data_quality_inquiry",
    "monthly_patterns",
    "general_weather_question",
    "unknown_intent",
]

MetricType = Literal[
    "temperature",
    "rainfall",
    "humidity",
    "wind",
    "air_quality",
    "general",
]

AggregationType = Literal[
    "current",
    "maximum",
    "minimum",
    "average",
    "sum",
    "trend",
    "ranking",
    "comparison",
]

ChartType = Literal[
    "line",
    "bar",
    "grouped_bar",
    "area",
    "pie",
    "table",
]


class DateRangeSpecification(BaseModel):
    """Extracted or defaulted date window for weather intelligence."""
    preset: Optional[str] = Field(None, description="One of 13 supported presets e.g. today, yesterday, last_7_days")
    start_date: Optional[date] = Field(None, description="ISO Start date YYYY-MM-DD")
    end_date: Optional[date] = Field(None, description="ISO End date YYYY-MM-DD")
    is_explicit: bool = Field(False, description="True if user specifically requested a date")


class ExtractedIntent(BaseModel):
    """Structured intent and parameter extraction result."""
    intent: IntentType = Field("general_weather_question", description="Primary detected intent")
    metric: MetricType = Field("general", description="Target meteorological metric")
    aggregation: AggregationType = Field("current", description="Target aggregation type")
    district: Optional[str] = Field(None, description="Primary isolated district")
    districts: List[str] = Field(default_factory=list, description="All districts mentioned (for comparisons)")
    date_range: DateRangeSpecification = Field(default_factory=DateRangeSpecification)
    sort_order: Optional[Literal["ascending", "descending"]] = Field(None)
    ranking_limit: int = Field(5, description="Number of districts to rank")
    confidence: float = Field(0.9, ge=0.0, le=1.0)
    raw_query: str = Field("", description="Original user prompt")


class ChartSeriesSpec(BaseModel):
    """Single series in a structured chart."""
    name: str
    key: str
    color: Optional[str] = None


class ChartSpec(BaseModel):
    """Structured chart specification ready for Recharts visualization."""
    type: ChartType = Field("bar", description="Visual chart type")
    title: str = Field(..., description="Chart title")
    subtitle: Optional[str] = Field(None, description="Chart subtitle")
    x_axis: str = Field("name", description="Field to use for X-axis")
    y_axis: str = Field("value", description="Metric description for Y-axis")
    series: List[ChartSeriesSpec] = Field(default_factory=list)
    data: List[Dict[str, Any]] = Field(default_factory=list)


class AIChatRequest(BaseModel):
    """Request model for conversational AI endpoint."""
    message: Optional[str] = Field(None, description="Natural-language weather question")
    query: Optional[str] = Field(None, description="Alias for message")
    question: Optional[str] = Field(None, description="Alias for message")
    conversation_id: Optional[str] = Field(None, description="Session conversation identifier")
    context: Optional[str] = Field(None, description="Legacy context parameter")
    district: Optional[str] = Field(None, description="Optional explicit district override")
    start_date: Optional[date] = Field(None, description="Optional explicit start date override")
    end_date: Optional[date] = Field(None, description="Optional explicit end date override")
    filters: Optional[Dict[str, Any]] = Field(None, description="Active dashboard filter context")

    @property
    def prompt_text(self) -> str:
        return (self.question or self.message or self.query or "").strip()


class AIChatResponse(BaseModel):
    """Response model for conversational AI endpoint."""
    conversation_id: str = Field(..., description="Session identifier")
    answer: str = Field(..., description="Natural-language grounded explanation")
    response: str = Field(..., description="Duplicate of answer for backward compatibility")
    intent: IntentType = Field(..., description="Detected user intent")
    district: Optional[str] = Field(None, description="Primary district")
    districts: List[str] = Field(default_factory=list, description="Districts involved")
    confidence: float = Field(0.95, ge=0.0, le=1.0)
    sources: List[str] = Field(default_factory=list, description="Verified Fabric Lakehouse source tables")
    applied_filters: Dict[str, Any] = Field(default_factory=dict, description="Validated parameters applied")
    observation_timestamp: Optional[str] = Field(None, description="Timestamp of telemetry used")
    data_summary: Optional[Dict[str, Any]] = Field(None, description="Key mathematical KPIs extracted from Fabric")
    chart: Optional[ChartSpec] = Field(None, description="Structured chart specification if applicable")
    follow_up_suggestions: List[str] = Field(default_factory=list, description="Contextual follow-up suggestions")

