"""Analytics service — aggregation and statistical helpers.

Provides helper functions for weather data aggregation,
trend analysis, and statistical computations.
"""

from typing import Any, Dict, List, Optional
import structlog

log = structlog.get_logger()


class AnalyticsService:
    """Weather data aggregation and analytics helpers."""

    def compute_temperature_distribution(
        self, temperatures: List[float]
    ) -> Dict[str, int]:
        """Compute distribution bins for temperature readings.

        Bins:
          - Under 20°C
          - 20°C - 25°C
          - 25°C - 30°C
          - 30°C - 35°C
          - Above 35°C
        """
        bins = {
            "under_20": 0,
            "20_to_25": 0,
            "25_to_30": 0,
            "30_to_35": 0,
            "above_35": 0,
        }
        for t in temperatures:
            if t is None:
                continue
            if t < 20.0:
                bins["under_20"] += 1
            elif t < 25.0:
                bins["20_to_25"] += 1
            elif t < 30.0:
                bins["25_to_30"] += 1
            elif t < 35.0:
                bins["30_to_35"] += 1
            else:
                bins["above_35"] += 1
        return bins

    def analyze_rainfall_categories(
        self, records: List[Dict[str, Any]], rainfall_key: str = "rainfall_mm"
    ) -> Dict[str, Any]:
        """Classify rainfall records into IMD standard categories.

        - Dry: 0.0 mm
        - Light: 0.1 - 15.5 mm
        - Moderate: 15.6 - 64.4 mm
        - Heavy: 64.5 - 115.5 mm
        - Very Heavy: > 115.5 mm
        """
        counts = {
            "dry_days": 0,
            "light_rain_days": 0,
            "moderate_rain_days": 0,
            "heavy_rain_days": 0,
            "very_heavy_rain_days": 0,
            "total_rainfall_mm": 0.0,
            "max_single_day_rainfall_mm": 0.0,
        }

        for r in records:
            rf = float(r.get(rainfall_key) or 0.0)
            counts["total_rainfall_mm"] += rf
            if rf > counts["max_single_day_rainfall_mm"]:
                counts["max_single_day_rainfall_mm"] = round(rf, 2)

            if rf <= 0.0:
                counts["dry_days"] += 1
            elif rf < 15.6:
                counts["light_rain_days"] += 1
            elif rf < 64.5:
                counts["moderate_rain_days"] += 1
            elif rf < 115.6:
                counts["heavy_rain_days"] += 1
            else:
                counts["very_heavy_rain_days"] += 1

        counts["total_rainfall_mm"] = round(counts["total_rainfall_mm"], 2)
        return counts

    def compute_average(self, values: List[float]) -> Optional[float]:
        """Compute the average of a list of numeric values."""
        clean = [v for v in values if v is not None]
        if not clean:
            return None
        return round(sum(clean) / len(clean), 2)

    def compute_min_max(self, values: List[float]) -> Dict[str, Optional[float]]:
        """Compute min and max from a list of numeric values."""
        clean = [v for v in values if v is not None]
        if not clean:
            return {"min": None, "max": None}
        return {"min": round(min(clean), 2), "max": round(max(clean), 2)}
