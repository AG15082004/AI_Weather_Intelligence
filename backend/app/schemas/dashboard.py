"""Dashboard-related Pydantic schemas.

Models for dashboard configurations, widgets, and presets.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WidgetConfig(BaseModel):
    """Configuration for a single dashboard widget."""

    type: str = Field(
        ...,
        description="Widget type: stat_card, line_chart, bar_chart, pie_chart, map, heatmap, gauge",
    )
    metric: str = Field(..., description="Data metric to display")
    label: str = Field(..., description="Display label for the widget")
    position: Optional[Dict[str, int]] = Field(
        None, description="Grid position {row, col, width, height}"
    )
    config: Optional[Dict[str, Any]] = Field(
        None, description="Additional widget-specific configuration"
    )


class DashboardConfig(BaseModel):
    """Full dashboard configuration."""

    id: Optional[str] = None
    name: str = Field(..., description="Dashboard display name")
    description: Optional[str] = None
    districts: List[str] = Field(default_factory=list, description="Included districts")
    widgets: List[WidgetConfig] = Field(default_factory=list, description="Widget list")
    generated: bool = Field(False, description="Whether AI-generated")


class DashboardPreset(BaseModel):
    """Pre-built dashboard preset."""

    id: str
    name: str
    description: str
    widgets: List[WidgetConfig]


class DashboardGenerateRequest(BaseModel):
    """Request body for AI dashboard generation."""

    prompt: str = Field(..., description="Natural-language dashboard description")
    districts: Optional[List[str]] = Field(None, description="Districts to include")


class DashboardGenerateResponse(BaseModel):
    """Response from AI dashboard generation."""

    name: str
    description: str
    districts: List[str] = Field(default_factory=list)
    widgets: List[Dict[str, Any]] = Field(default_factory=list)
    generated: bool = True
    fallback: bool = False
    error: Optional[str] = None
