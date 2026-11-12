"""Dashboard service — AI-powered dashboard generation.

Creates customizable dashboard configurations from natural-language
descriptions using the AI service.
"""

from typing import Any, Dict, List, Optional

import structlog

from app.services.ai_service import AIService

log = structlog.get_logger()


# Pre-built dashboard presets
_PRESETS: List[Dict[str, Any]] = [
    {
        "id": "overview",
        "name": "State Overview",
        "description": "High-level weather summary for all Tamil Nadu districts",
        "widgets": [
            {"type": "stat_card", "metric": "avg_temperature", "label": "Avg Temperature"},
            {"type": "stat_card", "metric": "total_rainfall", "label": "Total Rainfall"},
            {"type": "stat_card", "metric": "avg_humidity", "label": "Avg Humidity"},
            {"type": "map", "metric": "temperature", "label": "District Temperature Map"},
            {"type": "bar_chart", "metric": "rainfall_by_district", "label": "Rainfall by District"},
        ],
    },
    {
        "id": "temperature_monitor",
        "name": "Temperature Monitor",
        "description": "Temperature trends and heatmaps across districts",
        "widgets": [
            {"type": "line_chart", "metric": "temperature_trend", "label": "Temperature Trend"},
            {"type": "heatmap", "metric": "temperature_grid", "label": "District Heatmap"},
            {"type": "stat_card", "metric": "max_temperature", "label": "Highest Temp"},
            {"type": "stat_card", "metric": "min_temperature", "label": "Lowest Temp"},
        ],
    },
    {
        "id": "rainfall_tracker",
        "name": "Rainfall Tracker",
        "description": "Precipitation monitoring and cumulative analysis",
        "widgets": [
            {"type": "line_chart", "metric": "rainfall_trend", "label": "Rainfall Trend"},
            {"type": "bar_chart", "metric": "rainfall_by_district", "label": "By District"},
            {"type": "stat_card", "metric": "total_rainfall", "label": "Total Rainfall"},
            {"type": "gauge", "metric": "rainfall_departure", "label": "% Departure from Normal"},
        ],
    },
    {
        "id": "air_quality",
        "name": "Air Quality Dashboard",
        "description": "AQI monitoring and pollutant breakdown",
        "widgets": [
            {"type": "stat_card", "metric": "avg_aqi", "label": "Average AQI"},
            {"type": "bar_chart", "metric": "aqi_by_district", "label": "AQI by District"},
            {"type": "pie_chart", "metric": "pollutant_breakdown", "label": "Pollutant Share"},
        ],
    },
]


class DashboardService:
    """Generate and manage weather dashboards."""

    def __init__(self) -> None:
        self._ai_service = AIService()

    async def generate_dashboard(
        self,
        prompt: str,
        districts: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate a dashboard configuration from a natural-language prompt.

        Uses AI to interpret the user's description and select
        appropriate chart types and data bindings.

        Args:
            prompt: Natural-language dashboard description.
            districts: Optional list of districts to include.

        Returns:
            Dashboard configuration dict.
        """
        log.info("dashboard_generation_started", prompt=prompt)

        system = (
            "You are a dashboard configuration generator for a Tamil Nadu weather app. "
            "Given a user description, output a JSON array of widget objects. "
            "Each widget has: type (stat_card|line_chart|bar_chart|pie_chart|map|heatmap|gauge), "
            "metric (the data field), label (display name). "
            "Reply with ONLY the JSON array."
        )

        try:
            import json

            result = await self._ai_service._call_ollama(prompt=prompt, system=system)
            widgets = json.loads(result.strip())

            dashboard = {
                "name": f"Custom: {prompt[:50]}",
                "description": prompt,
                "districts": districts or [],
                "widgets": widgets,
                "generated": True,
            }
            log.info("dashboard_generated", widget_count=len(widgets))
            return dashboard
        except Exception as exc:
            log.error("dashboard_generation_failed", error=str(exc))
            # Fallback to overview preset
            return {
                "name": f"Custom: {prompt[:50]}",
                "description": prompt,
                "districts": districts or [],
                "widgets": _PRESETS[0]["widgets"],
                "generated": False,
                "fallback": True,
                "error": "AI generation failed, using overview preset",
            }

    async def list_presets(self) -> List[Dict[str, Any]]:
        """List available pre-built dashboard configurations.

        Returns:
            List of preset dashboard configurations.
        """
        log.info("dashboard_presets_listed", count=len(_PRESETS))
        return _PRESETS
