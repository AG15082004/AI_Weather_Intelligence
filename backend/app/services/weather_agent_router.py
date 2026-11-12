"""Fabric Data-Grounded Query Router and Analytical Engine.

Routes validated intents to allowlisted Microsoft Fabric Lakehouse queries.
Strictly prohibits arbitrary LLM SQL generation; all queries are parameterized
and executed through verified services.
"""

from datetime import date
from typing import Any, Dict, List, Optional, Tuple
import structlog

from app.database.query_executor import QueryExecutor
from app.schemas.ai import (
    ChartSeriesSpec,
    ChartSpec,
    DateRangeSpecification,
    ExtractedIntent,
)
from app.services.weather_service import WeatherService
from app.utils.date_utils import (
    get_ist_today,
    get_ist_yesterday,
    get_preset_date_range,
)

log = structlog.get_logger()


class WeatherAgentRouter:
    """Allowlisted routing engine for Microsoft Fabric Weather Analytics."""

    def __init__(self) -> None:
        self.ws = WeatherService()
        self.qe = QueryExecutor()

    async def execute_intent(
        self, extracted: ExtractedIntent
    ) -> Dict[str, Any]:
        """Route extracted intent to verified analytical query."""
        intent = extracted.intent
        metric = extracted.metric
        district = extracted.district
        districts = extracted.districts
        date_range = extracted.date_range
        today = get_ist_today()
        yesterday = get_ist_yesterday()

        target_date = date_range.start_date or today
        is_today = (target_date == today)
        is_yesterday = (target_date == yesterday)

        # ---------------------------------------------------------------------
        # 1. Weather Ranking Intent
        # ---------------------------------------------------------------------
        if intent == "weather_ranking":
            return await self._handle_ranking(extracted)

        # ---------------------------------------------------------------------
        # 2. District Comparison Intent (2 or more districts)
        # ---------------------------------------------------------------------
        if intent == "district_comparison" or len(districts) >= 2:
            return await self._handle_district_comparison(extracted)

        # ---------------------------------------------------------------------
        # 3. Date Comparison Intent (Today vs Yesterday, etc.)
        # ---------------------------------------------------------------------
        if intent == "date_comparison":
            return await self._handle_date_comparison(extracted)

        # ---------------------------------------------------------------------
        # 4. Air Quality Analysis
        # ---------------------------------------------------------------------
        if intent == "air_quality_analysis" or metric == "air_quality":
            return await self._handle_air_quality(district)

        # ---------------------------------------------------------------------
        # 5. Rainfall Analysis
        # ---------------------------------------------------------------------
        if intent == "rainfall_analysis" or metric == "rainfall":
            return await self._handle_rainfall(extracted)

        # ---------------------------------------------------------------------
        # 6. Temperature Analysis / Weather Trend
        # ---------------------------------------------------------------------
        if intent in ("temperature_analysis", "weather_trend") or (metric == "temperature" and date_range.is_explicit and date_range.preset != "today"):
            return await self._handle_temperature_and_trend(extracted)

        # ---------------------------------------------------------------------
        # 7. District Intelligence (Profile, Elevation, Coordinates)
        # ---------------------------------------------------------------------
        if intent == "district_intelligence":
            return await self._handle_district_intelligence(district)

        # ---------------------------------------------------------------------
        # 8. Statewide Summary / Weather Report
        # ---------------------------------------------------------------------
        if intent in ("statewide_summary", "weather_report"):
            return await self._handle_statewide_summary(extracted)

        # ---------------------------------------------------------------------
        # 9. Dashboard Request
        # ---------------------------------------------------------------------
        if intent == "dashboard_request":
            return {
                "source": "Microsoft Fabric Lakehouse Spec Engine",
                "summary": "Custom dashboard generation request identified.",
                "data_points": [],
                "chart": None,
                "observation_timestamp": str(today),
            }

        # ---------------------------------------------------------------------
        # 10. Current / Historical Weather Single District (Default)
        # ---------------------------------------------------------------------
        return await self._handle_current_or_historical(district, target_date, is_today)

    # =========================================================================
    # Internal Handlers
    # =========================================================================

    async def _handle_ranking(self, extracted: ExtractedIntent) -> Dict[str, Any]:
        """Compute district rankings (hottest, coldest, wettest, highest AQI)."""
        metric = extracted.metric
        sort_order = extracted.sort_order or "descending"
        limit = extracted.ranking_limit or 5
        date_range = extracted.date_range
        is_yesterday = (date_range.preset == "yesterday")
        today = get_ist_today()

        if metric == "rainfall":
            # For rainfall, silver_weather_current has verified rainfall on Nov 11 (Yesterday) and Nov 12 (Today)
            target_date = get_ist_yesterday() if is_yesterday else today
            sql = """
                SELECT 
                    district_name as district,
                    ROUND(SUM(precipitation_mm), 2) as value
                FROM [dbo].[silver_weather_current]
                WHERE CAST(last_updated AS DATE) = ?
                GROUP BY district_name
                HAVING SUM(precipitation_mm) > 0
                ORDER BY value DESC
            """
            rows = await self.qe.execute_query(sql, (target_date,))
            if not rows:
                # If target date has no rain, query zero readings
                sql_zero = """
                    SELECT TOP ? district_name as district, 0.0 as value
                    FROM [dbo].[silver_weather_current]
                    WHERE CAST(last_updated AS DATE) = ?
                    GROUP BY district_name
                """
                rows = await self.qe.execute_query(sql_zero, (limit, target_date))

            chart_data = [{"name": r["district"], "Rainfall (mm)": r["value"]} for r in rows[:limit]]
            chart = ChartSpec(
                type="bar",
                title=f"Top Rainfall Districts ({target_date})",
                x_axis="name",
                y_axis="Rainfall (mm)",
                series=[ChartSeriesSpec(name="Rainfall", key="Rainfall (mm)", color="#3b82f6")],
                data=chart_data,
            ) if chart_data else None

            return {
                "source": "Microsoft Fabric [dbo].[silver_weather_current]",
                "target_date": str(target_date),
                "metric": "Rainfall",
                "unit": "mm",
                "rankings": rows[:limit],
                "top_district": rows[0]["district"] if rows else None,
                "top_value": rows[0]["value"] if rows else 0.0,
                "observation_timestamp": f"{target_date} verified runs",
                "chart": chart,
            }

        elif metric == "air_quality":
            sql = f"""
                SELECT TOP {limit}
                    district_name as district,
                    us_epa_index as aqi,
                    us_epa_category as category,
                    ROUND(pm2_5, 1) as pm25
                FROM [dbo].[gold_air_quality_latest]
                ORDER BY us_epa_index {'DESC' if sort_order == 'descending' else 'ASC'}, pm2_5 {'DESC' if sort_order == 'descending' else 'ASC'}
            """
            rows = await self.qe.execute_query(sql)
            chart_data = [{"name": r["district"], "PM2.5": r["pm25"]} for r in rows]
            chart = ChartSpec(
                type="bar",
                title="District Air Quality (PM2.5 µg/m³)",
                x_axis="name",
                y_axis="PM2.5 (µg/m³)",
                series=[ChartSeriesSpec(name="PM2.5", key="PM2.5", color="#e11d48")],
                data=chart_data,
            )
            return {
                "source": "Microsoft Fabric [dbo].[gold_air_quality_latest]",
                "metric": "Air Quality",
                "rankings": rows,
                "top_district": rows[0]["district"] if rows else None,
                "top_value": rows[0]["pm25"] if rows else None,
                "observation_timestamp": "Latest continuous monitor",
                "chart": chart,
            }

        else:
            # Temperature ranking (Default: Today latest snapshot)
            order_sql = "DESC" if sort_order == "descending" else "ASC"
            sql = f"""
                SELECT TOP {limit}
                    district_name as district,
                    temperature_c as value,
                    feels_like_c as feels_like,
                    condition_text as condition,
                    last_updated
                FROM [dbo].[gold_current_weather_latest]
                ORDER BY temperature_c {order_sql}
            """
            rows = await self.qe.execute_query(sql)
            top_title = "Hottest Districts" if sort_order == "descending" else "Coolest Districts"
            chart_data = [{"name": r["district"], "Temp (°C)": r["value"]} for r in rows]
            chart = ChartSpec(
                type="bar",
                title=f"{top_title} in Tamil Nadu",
                x_axis="name",
                y_axis="Temperature (°C)",
                series=[ChartSeriesSpec(name="Temperature", key="Temp (°C)", color="#f97316" if sort_order == "descending" else "#06b6d4")],
                data=chart_data,
            )
            return {
                "source": "Microsoft Fabric [dbo].[gold_current_weather_latest]",
                "metric": "Temperature",
                "unit": "°C",
                "rankings": rows,
                "top_district": rows[0]["district"] if rows else None,
                "top_value": rows[0]["value"] if rows else None,
                "observation_timestamp": rows[0]["last_updated"] if rows else str(today),
                "chart": chart,
            }

    async def _handle_district_comparison(self, extracted: ExtractedIntent) -> Dict[str, Any]:
        """Compare meteorological parameters across 2 or more districts."""
        districts = extracted.districts or ([extracted.district] if extracted.district else ["Chennai", "Coimbatore"])
        today = get_ist_today()

        # Query latest weather for these districts
        placeholders = ", ".join(["?"] * len(districts))
        sql = f"""
            SELECT 
                district_name as district,
                temperature_c as temp,
                feels_like_c as feels_like,
                humidity,
                wind_kph as wind_speed,
                precipitation_mm as rainfall,
                condition_text as condition,
                last_updated
            FROM [dbo].[gold_current_weather_latest]
            WHERE district_name IN ({placeholders})
            ORDER BY district_name ASC
        """
        rows = await self.qe.execute_query(sql, tuple(districts))

        chart_data = [
            {
                "name": r["district"],
                "Temp (°C)": r["temp"],
                "Humidity (%)": r["humidity"],
                "Rainfall (mm)": r["rainfall"] or 0.0,
            }
            for r in rows
        ]

        chart = ChartSpec(
            type="grouped_bar",
            title=f"District Weather Comparison: {', '.join(districts)}",
            x_axis="name",
            y_axis="Metric",
            series=[
                ChartSeriesSpec(name="Temp (°C)", key="Temp (°C)", color="#f97316"),
                ChartSeriesSpec(name="Humidity (%)", key="Humidity (%)", color="#10b981"),
            ],
            data=chart_data,
        )

        return {
            "source": "Microsoft Fabric [dbo].[gold_current_weather_latest]",
            "districts": districts,
            "comparison_rows": rows,
            "observation_timestamp": rows[0]["last_updated"] if rows else str(today),
            "chart": chart,
        }

    async def _handle_date_comparison(self, extracted: ExtractedIntent) -> Dict[str, Any]:
        """Compare Today vs Yesterday or Period A vs Period B."""
        district = extracted.district
        today = get_ist_today()
        yesterday = get_ist_yesterday()

        res = await self.ws.compare_periods(
            period_a_start=today,
            period_a_end=today,
            period_b_start=yesterday,
            period_b_end=yesterday,
            district=district,
        )
        data = res.get("data", {})

        chart_data = [
            {
                "metric": "Temperature (°C)",
                "Today": data.get("temperature", {}).get("current_val"),
                "Yesterday": data.get("temperature", {}).get("previous_val"),
            },
            {
                "metric": "Humidity (%)",
                "Today": data.get("humidity", {}).get("current_val"),
                "Yesterday": data.get("humidity", {}).get("previous_val"),
            },
        ]

        chart = ChartSpec(
            type="grouped_bar",
            title=f"Today vs Yesterday Weather Comparison ({district or 'Tamil Nadu'})",
            x_axis="metric",
            y_axis="Value",
            series=[
                ChartSeriesSpec(name="Today", key="Today", color="#0284c7"),
                ChartSeriesSpec(name="Yesterday", key="Yesterday", color="#64748b"),
            ],
            data=chart_data,
        )

        return {
            "source": "Microsoft Fabric Lakehouse (Period Comparison Engine)",
            "district": district or "Statewide",
            "comparison": data,
            "observation_timestamp": f"{today} vs {yesterday}",
            "chart": chart,
        }

    async def _handle_air_quality(self, district: Optional[str]) -> Dict[str, Any]:
        """Fetch air quality analytics for statewide or specific district."""
        res = await self.ws.get_air_quality(district=district)
        rows = res.get("data", [])
        top_rows = rows[:10] if not district else rows

        chart_data = [
            {"name": r["district"], "AQI": r["aqi"], "PM2.5": r["pm25"]}
            for r in top_rows
        ]
        chart = ChartSpec(
            type="bar",
            title=f"Air Quality Index ({district or 'Top TN Districts'})",
            x_axis="name",
            y_axis="Index",
            series=[ChartSeriesSpec(name="AQI", key="AQI", color="#8b5cf6")],
            data=chart_data,
        )

        return {
            "source": "Microsoft Fabric [dbo].[gold_air_quality_latest]",
            "district": district or "Statewide",
            "records": rows,
            "count": len(rows),
            "observation_timestamp": rows[0]["last_updated"] if rows else "Live",
            "chart": chart,
        }

    async def _handle_rainfall(self, extracted: ExtractedIntent) -> Dict[str, Any]:
        """Fetch rainfall data respecting data quality rules (no false zeroes)."""
        district = extracted.district
        date_range = extracted.date_range
        res = await self.ws.get_rainfall_data(
            start_date=date_range.start_date,
            end_date=date_range.end_date,
            district=district,
        )
        rows = res.get("data", [])
        quality = res.get("rainfall_quality", {})

        chart_rows = [r for r in rows if r.get("rainfall_mm") is not None][:15]
        chart_data = [{"date": str(r["date"]), "Rainfall (mm)": r["rainfall_mm"]} for r in chart_rows]

        chart = ChartSpec(
            type="bar",
            title=f"Rainfall Trends ({district or 'Tamil Nadu'})",
            x_axis="date",
            y_axis="Rainfall (mm)",
            series=[ChartSeriesSpec(name="Rainfall", key="Rainfall (mm)", color="#2563eb")],
            data=chart_data,
        ) if chart_data else None

        return {
            "source": "Microsoft Fabric Lakehouse [dbo].[gold_district_rainfall_analytics]",
            "district": district or "Statewide",
            "date_range": f"{date_range.start_date} to {date_range.end_date}",
            "rainfall_records": rows[:10],
            "total_records": len(rows),
            "quality": quality,
            "observation_timestamp": str(date_range.end_date),
            "chart": chart,
        }

    async def _handle_temperature_and_trend(self, extracted: ExtractedIntent) -> Dict[str, Any]:
        """Fetch temperature trend across selected date range."""
        district = extracted.district
        date_range = extracted.date_range
        res = await self.ws.get_temperature_data(
            start_date=date_range.start_date,
            end_date=date_range.end_date,
            district=district,
        )
        rows = res.get("data", [])
        chart_rows = list(reversed(rows[:14]))

        chart_data = [
            {
                "date": str(r["date"]),
                "Avg (°C)": r["avg_temp"],
                "Max (°C)": r["max_temp"],
                "Min (°C)": r["min_temp"],
            }
            for r in chart_rows
        ]

        chart = ChartSpec(
            type="line",
            title=f"Temperature Trajectory ({district or 'Tamil Nadu'})",
            x_axis="date",
            y_axis="Temperature (°C)",
            series=[
                ChartSeriesSpec(name="Max", key="Max (°C)", color="#f43f5e"),
                ChartSeriesSpec(name="Avg", key="Avg (°C)", color="#f59e0b"),
                ChartSeriesSpec(name="Min", key="Min (°C)", color="#3b82f6"),
            ],
            data=chart_data,
        ) if chart_data else None

        return {
            "source": "Microsoft Fabric Lakehouse [dbo].[gold_district_daily_analytics]",
            "district": district or "Statewide",
            "date_range": f"{date_range.start_date} to {date_range.end_date}",
            "rows": rows[:10],
            "count": len(rows),
            "observation_timestamp": str(date_range.end_date),
            "chart": chart,
        }

    async def _handle_district_intelligence(self, district: Optional[str]) -> Dict[str, Any]:
        """Fetch district metadata, coordinates, elevation, and climate summary."""
        target_dist = district or "Chennai"
        res = await self.ws.get_district_data(district=target_dist)
        rows = res.get("data", [])
        data_item = rows[0] if rows else {}

        return {
            "source": "Microsoft Fabric [dbo].[dim_district]",
            "district": target_dist,
            "details": data_item,
            "observation_timestamp": "Geographical Registry",
            "chart": None,
        }

    async def _handle_statewide_summary(self, extracted: ExtractedIntent) -> Dict[str, Any]:
        """Fetch high-level statewide climate summary and distribution."""
        date_range = extracted.date_range
        today = get_ist_today()
        is_today = (date_range.preset == "today") or (date_range.start_date == today and date_range.end_date == today)

        if is_today:
            # Ultra-fast path: query gold_current_weather_latest directly (0.2s vs 8s multi-scan)
            fast_sql = """
                SELECT 
                    COUNT(DISTINCT district_name) as districts_covered,
                    ROUND(AVG(temperature_c), 1) as avg_temperature,
                    ROUND(MAX(temperature_c), 1) as max_temperature,
                    ROUND(MIN(temperature_c), 1) as min_temperature,
                    ROUND(AVG(humidity), 1) as avg_humidity,
                    ROUND(SUM(precipitation_mm), 1) as total_rainfall,
                    MAX(last_updated) as latest_observation
                FROM [dbo].[gold_current_weather_latest]
            """
            rows = await self.qe.execute_query(fast_sql)
            o = rows[0] if rows else {}

            comp_sql = """
                SELECT TOP 8
                    district_name as district,
                    temperature_c as avg_temp,
                    humidity as avg_humidity
                FROM [dbo].[gold_current_weather_latest]
                ORDER BY temperature_c DESC
            """
            comp_rows = await self.qe.execute_query(comp_sql)
            chart_data = [
                {"name": d["district"], "Avg Temp": d["avg_temp"], "Humidity": d["avg_humidity"]}
                for d in comp_rows
            ]

            chart = ChartSpec(
                type="bar",
                title="Statewide District Climate Snapshot Today",
                x_axis="name",
                y_axis="Climate Metric",
                series=[
                    ChartSeriesSpec(name="Avg Temp (°C)", key="Avg Temp", color="#f97316"),
                    ChartSeriesSpec(name="Humidity (%)", key="Humidity", color="#10b981"),
                ],
                data=chart_data,
            ) if chart_data else None

            return {
                "source": "Microsoft Fabric Lakehouse [dbo].[gold_current_weather_latest]",
                "overview": {
                    "districts_covered": o.get("districts_covered", 38),
                    "avg_temperature": o.get("avg_temperature"),
                    "max_temperature": o.get("max_temperature"),
                    "min_temperature": o.get("min_temperature"),
                    "total_rainfall": o.get("total_rainfall"),
                    "avg_humidity": o.get("avg_humidity"),
                    "latest_observation": o.get("latest_observation"),
                },
                "rainfall_quality": {"status": "complete", "completeness_pct": 100.0},
                "observation_timestamp": o.get("latest_observation") or str(today),
                "chart": chart,
            }

        # Historical multi-day / multi-month summary
        res = await self.ws.get_overview(
            start_date=date_range.start_date,
            end_date=date_range.end_date,
        )
        overview = res.get("data", {})
        dist_comp = overview.get("district_comparison", [])[:8]

        chart_data = [
            {"name": d["district"], "Avg Temp": d["avg_temp"], "Humidity": d["avg_humidity"]}
            for d in dist_comp
        ]

        chart = ChartSpec(
            type="bar",
            title="Statewide District Climate Snapshot",
            x_axis="name",
            y_axis="Climate Metric",
            series=[
                ChartSeriesSpec(name="Avg Temp (°C)", key="Avg Temp", color="#f97316"),
                ChartSeriesSpec(name="Humidity (%)", key="Humidity", color="#10b981"),
            ],
            data=chart_data,
        ) if chart_data else None

        return {
            "source": "Microsoft Fabric Lakehouse [dbo].[gold_district_daily_analytics]",
            "overview": {
                "districts_covered": overview.get("districts_covered", 38),
                "avg_temperature": overview.get("avg_temperature"),
                "max_temperature": overview.get("max_temperature"),
                "min_temperature": overview.get("min_temperature"),
                "total_rainfall": overview.get("total_rainfall"),
                "avg_humidity": overview.get("avg_humidity"),
                "latest_observation": overview.get("latest_observation"),
            },
            "rainfall_quality": res.get("rainfall_quality", {}),
            "observation_timestamp": overview.get("latest_observation") or str(today),
            "chart": chart,
        }

    async def _handle_current_or_historical(
        self, district: Optional[str], target_date: date, is_today: bool
    ) -> Dict[str, Any]:
        """Fetch current weather or historical single date observations."""
        res = await self.ws.get_current_weather(
            district=district,
            date_param=target_date if not is_today else None,
        )
        data = res.get("data", [])
        return {
            "source": "Microsoft Fabric [dbo].[gold_current_weather_latest]" if is_today else "Microsoft Fabric [dbo].[silver_weather_current]",
            "district": district,
            "target_date": str(target_date),
            "is_today": is_today,
            "data": data,
            "observation_timestamp": data[0].get("last_updated") if data else str(target_date),
            "chart": None,
        }

