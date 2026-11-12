"""Weather data service connecting directly to Microsoft Fabric Lakehouse.

Queries the verified Gold and Silver tables:
  - [dbo].[gold_district_daily_analytics]
  - [dbo].[gold_district_monthly_analytics]
  - [dbo].[gold_district_rainfall_analytics]
  - [dbo].[gold_current_weather_latest]
  - [dbo].[silver_weather_current]
  - [dbo].[gold_air_quality_latest]
  - [dbo].[dim_district]
"""

import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import structlog

from app.database.query_executor import QueryExecutor
from app.utils.date_utils import (
    get_ist_today,
    get_ist_yesterday,
    validate_date_range,
)

log = structlog.get_logger()


def _to_date_str(val: Any) -> Optional[str]:
    """Safely convert date/datetime or string to YYYY-MM-DD string."""
    if val is None:
        return None
    if isinstance(val, (date, datetime)):
        return val.strftime("%Y-%m-%d")
    return str(val)


def _to_float(val: Any, default: Optional[float] = None) -> Optional[float]:
    """Safely cast numeric value to float."""
    if val is None:
        return default
    try:
        return round(float(val), 2)
    except (ValueError, TypeError):
        return default


def _calculate_pct_change(curr: Optional[float], prev: Optional[float]) -> Optional[float]:
    """Safely calculate percentage change avoiding division by zero."""
    if curr is None or prev is None:
        return None
    if prev == 0:
        return 100.0 if curr > 0 else 0.0 if curr == 0 else -100.0
    return round(((curr - prev) / abs(prev)) * 100.0, 1)


class WeatherService:
    """Live Microsoft Fabric Weather Analytics Service."""

    def __init__(self, executor: Optional[QueryExecutor] = None) -> None:
        self._executor = executor or QueryExecutor()
        # In-memory TTL cache: key -> (timestamp, data)
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._cache_ttl = 300  # 5 minutes default

    def _get_from_cache(self, key: str) -> Optional[Any]:
        if key in self._cache:
            ts, data = self._cache[key]
            if time.time() - ts < self._cache_ttl:
                return data
            del self._cache[key]
        return None

    def _set_in_cache(self, key: str, data: Any) -> None:
        self._cache[key] = (time.time(), data)

    async def get_overview(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Get statewide weather overview aggregated from Fabric Lakehouse."""
        # 1. Enforce strict date range rules (IST, no future dates, start <= end)
        validate_date_range(start_date, end_date)

        cache_key = f"overview:{start_date}:{end_date}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        log.info("fetch_fabric_weather_overview", start_date=str(start_date), end_date=str(end_date))
        agg_params = (start_date, start_date, end_date, end_date)

        # 1. State-level temperature and humidity aggregate stats
        # Union gold daily analytics and silver current telemetry for seamless date coverage
        agg_sql = """
            SELECT 
                COUNT(DISTINCT district) as districts_covered,
                ROUND(AVG(avg_temp), 1) as avg_temperature,
                ROUND(MAX(max_temp), 1) as max_temperature,
                ROUND(MIN(min_temp), 1) as min_temperature,
                ROUND(AVG(avg_humidity), 1) as avg_humidity
            FROM (
                SELECT 
                    district_name as district,
                    weather_date as [date],
                    temperature_2m_mean as avg_temp,
                    temperature_2m_max as max_temp,
                    temperature_2m_min as min_temp,
                    relative_humidity_2m_mean as avg_humidity
                FROM [dbo].[gold_district_daily_analytics]
                UNION ALL
                SELECT 
                    district_name as district,
                    CAST(last_updated AS DATE) as [date],
                    AVG(temperature_c) as avg_temp,
                    MAX(temperature_c) as max_temp,
                    MIN(temperature_c) as min_temp,
                    AVG(humidity) as avg_humidity
                FROM [dbo].[silver_weather_current]
                GROUP BY district_name, CAST(last_updated AS DATE)
            ) combined
            WHERE (? IS NULL OR [date] >= ?)
              AND (? IS NULL OR [date] <= ?)
        """
        agg_rows = await self._executor.execute_query(agg_sql, agg_params)
        agg = agg_rows[0] if agg_rows else {}

        # 2. Get latest observation timestamp from current weather
        latest_sql = "SELECT MAX(last_updated) as latest_observation FROM [dbo].[gold_current_weather_latest]"
        latest_rows = await self._executor.execute_query(latest_sql)
        latest_obs = latest_rows[0].get("latest_observation") if latest_rows else None

        # 3. Daily temperature trend (chronological within filter)
        temp_trend_sql = """
            SELECT TOP 30
                [date],
                ROUND(AVG(avg_temp), 1) as avg_temp,
                ROUND(MAX(max_temp), 1) as max_temp,
                ROUND(MIN(min_temp), 1) as min_temp
            FROM (
                SELECT 
                    weather_date as [date],
                    temperature_2m_mean as avg_temp,
                    temperature_2m_max as max_temp,
                    temperature_2m_min as min_temp
                FROM [dbo].[gold_district_daily_analytics]
                UNION ALL
                SELECT 
                    CAST(last_updated AS DATE) as [date],
                    AVG(temperature_c) as avg_temp,
                    MAX(temperature_c) as max_temp,
                    MIN(temperature_c) as min_temp
                FROM [dbo].[silver_weather_current]
                GROUP BY CAST(last_updated AS DATE)
            ) t
            WHERE (? IS NULL OR [date] >= ?)
              AND (? IS NULL OR [date] <= ?)
            GROUP BY [date]
            ORDER BY [date] DESC
        """
        temp_trend_rows = await self._executor.execute_query(temp_trend_sql, agg_params)
        temp_trend = [
            {
                "date": _to_date_str(r["date"]),
                "avg_temp": _to_float(r["avg_temp"]),
                "max_temp": _to_float(r["max_temp"]),
                "min_temp": _to_float(r["min_temp"]),
            }
            for r in reversed(temp_trend_rows)
        ]

        # 4. Daily rainfall trend & Data Quality Analytics (No silent ISNULL conversions!)
        # silver_weather_current holds actual measured rainfall (2026-11-10 to present)
        # gold_district_daily_analytics holds historical unmeasured rainfall (NULL)
        rain_trend_sql = """
            SELECT TOP 30
                [date],
                SUM(rainfall_mm) as raw_rainfall,
                COUNT(rainfall_mm) as measured_count,
                COUNT(*) as total_readings,
                MAX(rainfall_mm) as peak_single_reading
            FROM (
                SELECT 
                    CAST(last_updated AS DATE) as [date],
                    district_name,
                    SUM(precipitation_mm) as rainfall_mm
                FROM [dbo].[silver_weather_current]
                GROUP BY CAST(last_updated AS DATE), district_name
                UNION ALL
                SELECT 
                    weather_date as [date],
                    district_name,
                    precipitation_sum as rainfall_mm
                FROM [dbo].[gold_district_daily_analytics]
            ) r
            WHERE (? IS NULL OR [date] >= ?)
              AND (? IS NULL OR [date] <= ?)
            GROUP BY [date]
            ORDER BY [date] DESC
        """
        rain_trend_rows = await self._executor.execute_query(rain_trend_sql, agg_params)

        rain_trend = []
        total_measured_days = 0
        total_missing_days = 0
        total_measured_rainfall = 0.0
        measured_zero_days = 0
        positive_rainfall_days = 0

        for r in reversed(rain_trend_rows):
            m_count = int(r.get("measured_count") or 0)
            raw_val = r.get("raw_rainfall")

            if m_count > 0 and raw_val is not None:
                val = round(float(raw_val), 2)
                total_measured_days += 1
                total_measured_rainfall += val
                if val > 0:
                    positive_rainfall_days += 1
                    status = "measured_positive"
                    category = "Heavy" if val >= 64.5 else "Moderate" if val >= 15.6 else "Light"
                else:
                    measured_zero_days += 1
                    status = "measured_zero"
                    category = "Dry"
                rain_trend.append({
                    "date": _to_date_str(r["date"]),
                    "rainfall_mm": val,
                    "category": category,
                    "status": status,
                    "is_rainy_day": val >= 2.5,
                })
            else:
                total_missing_days += 1
                rain_trend.append({
                    "date": _to_date_str(r["date"]),
                    "rainfall_mm": None,  # Explicit NULL! Never 0.0
                    "category": "Unmeasured",
                    "status": "missing",
                    "is_rainy_day": None,
                })

        total_days = total_measured_days + total_missing_days
        completeness_pct = round((total_measured_days / total_days * 100.0), 1) if total_days > 0 else 0.0

        rainfall_quality = {
            "total_days": total_days,
            "measured_days": total_measured_days,
            "missing_days": total_missing_days,
            "measured_zero_days": measured_zero_days,
            "positive_rainfall_days": positive_rainfall_days,
            "completeness_pct": completeness_pct,
            "status": "complete" if total_missing_days == 0 else "partial" if total_measured_days > 0 else "unmeasured",
            "has_positive_rain": positive_rainfall_days > 0,
        }

        final_total_rainfall = round(total_measured_rainfall, 1) if total_measured_days > 0 else None

        # 5. District-wise comparison (all 38 districts)
        dist_comp_sql = """
            SELECT 
                d.district_name as district,
                ROUND(AVG(d.temperature_2m_mean), 1) as avg_temp,
                ROUND(MAX(d.temperature_2m_max), 1) as max_temp,
                ROUND(MIN(d.temperature_2m_min), 1) as min_temp,
                SUM(d.precipitation_sum) as total_rainfall,
                ROUND(AVG(d.relative_humidity_2m_mean), 1) as avg_humidity
            FROM [dbo].[gold_district_daily_analytics] d
            WHERE (? IS NULL OR d.weather_date >= ?)
              AND (? IS NULL OR d.weather_date <= ?)
            GROUP BY d.district_name
            ORDER BY d.district_name ASC
        """
        dist_rows = await self._executor.execute_query(dist_comp_sql, agg_params)

        # Merge with current weather for live condition and real-time precipitation
        cw_sql = "SELECT district_name, temperature_c, condition_text, wind_kph, precipitation_mm FROM [dbo].[gold_current_weather_latest]"
        cw_map = {r["district_name"]: r for r in await self._executor.execute_query(cw_sql)}

        district_comparison = []
        for r in dist_rows:
            d_name = r["district"]
            cw = cw_map.get(d_name, {})
            # If historical rainfall is NULL for this window, fall back to current measured rainfall if looking at today/yesterday
            rf_val = _to_float(r["total_rainfall"])
            if rf_val is None and cw.get("precipitation_mm") is not None:
                rf_val = _to_float(cw.get("precipitation_mm"))

            district_comparison.append({
                "district": d_name,
                "avg_temp": _to_float(r["avg_temp"]),
                "max_temp": _to_float(r["max_temp"]),
                "min_temp": _to_float(r["min_temp"]),
                "total_rainfall": rf_val,
                "avg_humidity": _to_float(r["avg_humidity"]),
                "current_temp": _to_float(cw.get("temperature_c")),
                "current_condition": cw.get("condition_text"),
                "wind_speed": _to_float(cw.get("wind_kph")),
            })

        response_payload = {
            "status": "success",
            "rainfall_quality": rainfall_quality,
            "data": {
                "districts_covered": int(agg.get("districts_covered") or 38),
                "avg_temperature": _to_float(agg.get("avg_temperature")),
                "max_temperature": _to_float(agg.get("max_temperature")),
                "min_temperature": _to_float(agg.get("min_temperature")),
                "total_rainfall": final_total_rainfall,
                "avg_humidity": _to_float(agg.get("avg_humidity")),
                "active_alerts": 0,
                "latest_observation": latest_obs,
                "rainfall_quality": rainfall_quality,
                "temperature_trend": temp_trend,
                "rainfall_trend": rain_trend,
                "district_comparison": district_comparison,
            },
            "filters": {
                "start_date": _to_date_str(start_date),
                "end_date": _to_date_str(end_date),
            },
            "metadata": {
                "source": "Microsoft Fabric Lakehouse (lh_tn_weather_intelligence)",
                "tables": [
                    "[dbo].[gold_district_daily_analytics]",
                    "[dbo].[silver_weather_current]",
                    "[dbo].[gold_current_weather_latest]",
                ],
            }
        }

        self._set_in_cache(cache_key, response_payload)
        return response_payload

    async def get_temperature_data(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        district: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get daily and monthly temperature data from Fabric Lakehouse."""
        validate_date_range(start_date, end_date)
        log.info("fetch_fabric_temperature", start_date=str(start_date), end_date=str(end_date), district=district)
        clean_dist = district.strip() if district else None

        cache_key = f"temp:{clean_dist}:{start_date}:{end_date}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        # 1. Fetch daily records combining gold historical + silver current
        daily_sql = """
            SELECT TOP 300
                [date],
                district,
                ROUND(AVG(avg_temp), 1) as avg_temp,
                ROUND(MAX(max_temp), 1) as max_temp,
                ROUND(MIN(min_temp), 1) as min_temp
            FROM (
                SELECT 
                    weather_date as [date],
                    district_name as district,
                    temperature_2m_mean as avg_temp,
                    temperature_2m_max as max_temp,
                    temperature_2m_min as min_temp
                FROM [dbo].[gold_district_daily_analytics]
                UNION ALL
                SELECT 
                    CAST(last_updated AS DATE) as [date],
                    district_name as district,
                    AVG(temperature_c) as avg_temp,
                    MAX(temperature_c) as max_temp,
                    MIN(temperature_c) as min_temp
                FROM [dbo].[silver_weather_current]
                GROUP BY CAST(last_updated AS DATE), district_name
            ) combined
            WHERE (? IS NULL OR [date] >= ?)
              AND (? IS NULL OR [date] <= ?)
              AND (? IS NULL OR district = ? OR district LIKE ?)
            GROUP BY [date], district
            ORDER BY [date] DESC, district ASC
        """
        daily_params = (
            start_date, start_date,
            end_date, end_date,
            clean_dist, clean_dist,
            f"%{clean_dist}%" if clean_dist else None,
        )
        daily_rows = await self._executor.execute_query(daily_sql, daily_params)

        results = [
            {
                "date": _to_date_str(r["date"]),
                "district": r["district"],
                "avg_temp": _to_float(r["avg_temp"]),
                "max_temp": _to_float(r["max_temp"]),
                "min_temp": _to_float(r["min_temp"]),
            }
            for r in daily_rows
        ]

        # 2. Monthly summary from gold_district_monthly_analytics
        monthly_sql = """
            SELECT 
                district_name as district,
                year, month,
                month_start_date as [date],
                avg_temperature_c,
                min_temperature_c,
                max_temperature_c,
                observed_days
            FROM [dbo].[gold_district_monthly_analytics]
            WHERE (? IS NULL OR district_name = ? OR district_name LIKE ?)
            ORDER BY month_start_date DESC, district_name ASC
        """
        m_params = (clean_dist, clean_dist, f"%{clean_dist}%" if clean_dist else None)
        monthly_rows = await self._executor.execute_query(monthly_sql, m_params)

        monthly_summary = [
            {
                "district": r["district"],
                "year_month": f"{r['year']}-{int(r['month']):02d}",
                "avg_temp_celsius": _to_float(r["avg_temperature_c"]),
                "min_temp_celsius": _to_float(r["min_temperature_c"]),
                "max_temp_celsius": _to_float(r["max_temperature_c"]),
                "observed_days": int(r["observed_days"] or 0),
            }
            for r in monthly_rows
        ]

        # 3. Distribution calculation
        distribution = {
            "cold_days": len([r for r in results if (r["avg_temp"] or 0) < 20.0]),
            "mild_days": len([r for r in results if 20.0 <= (r["avg_temp"] or 0) < 25.0]),
            "warm_days": len([r for r in results if 25.0 <= (r["avg_temp"] or 0) < 30.0]),
            "hot_days": len([r for r in results if 30.0 <= (r["avg_temp"] or 0) < 35.0]),
            "extreme_days": len([r for r in results if (r["avg_temp"] or 0) >= 35.0]),
        }

        response_payload = {
            "status": "success",
            "data": results,
            "distribution": distribution,
            "filters": {
                "start_date": _to_date_str(start_date),
                "end_date": _to_date_str(end_date),
                "district": clean_dist,
            },
            "metadata": {
                "source": "Microsoft Fabric Lakehouse ([dbo].[gold_district_daily_analytics], [dbo].[silver_weather_current])",
                "total_records_returned": len(results),
                "monthly_summary": monthly_summary[:20],
            },
        }

        self._set_in_cache(cache_key, response_payload)
        return response_payload

    async def get_rainfall_data(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        district: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get precipitation and rainfall analytics from Fabric Lakehouse.
        
        Strictly preserves measured values vs explicit NULLs (no silent conversions!).
        """
        validate_date_range(start_date, end_date)
        log.info("fetch_fabric_rainfall", start_date=str(start_date), end_date=str(end_date), district=district)
        clean_dist = district.strip() if district else None

        cache_key = f"rain:{clean_dist}:{start_date}:{end_date}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        # 1. Fetch monthly rainfall metrics (418 records)
        monthly_sql = """
            SELECT 
                district_name as district,
                year, month,
                month_start_date as [date],
                total_rainfall_mm as rainfall_mm,
                avg_daily_rainfall_mm,
                max_daily_rainfall_mm,
                rainy_days, observed_days
            FROM [dbo].[gold_district_rainfall_analytics]
            WHERE (? IS NULL OR district_name = ? OR district_name LIKE ?)
            ORDER BY month_start_date DESC, district_name ASC
        """
        m_params = (clean_dist, clean_dist, f"%{clean_dist}%" if clean_dist else None)
        monthly_rows = await self._executor.execute_query(monthly_sql, m_params)

        monthly_data = [
            {
                "district": r["district"],
                "date": _to_date_str(r["date"]),
                "year": r["year"],
                "month": r["month"],
                "rainfall_mm": _to_float(r["rainfall_mm"]),  # None if missing!
                "avg_daily_rainfall_mm": _to_float(r["avg_daily_rainfall_mm"]),
                "max_daily_rainfall_mm": _to_float(r["max_daily_rainfall_mm"]),
                "rainy_days": int(r["rainy_days"] or 0),
                "observed_days": int(r["observed_days"] or 0),
            }
            for r in monthly_rows
        ]

        # 2. Fetch daily rainfall observations (Union silver measured + gold historical unmeasured)
        daily_sql = """
            SELECT TOP 300
                [date],
                district,
                rainfall_mm,
                CASE 
                    WHEN rainfall_mm IS NULL THEN 'Unmeasured'
                    WHEN rainfall_mm >= 64.5 THEN 'Heavy'
                    WHEN rainfall_mm >= 15.6 THEN 'Moderate'
                    WHEN rainfall_mm > 0 THEN 'Light'
                    ELSE 'Dry' 
                END as category,
                CASE 
                    WHEN rainfall_mm IS NULL THEN 'missing'
                    WHEN rainfall_mm > 0 THEN 'measured_positive'
                    ELSE 'measured_zero'
                END as reporting_status,
                CASE WHEN rainfall_mm >= 2.5 THEN 1 ELSE 0 END as is_rainy_day
            FROM (
                SELECT 
                    CAST(last_updated AS DATE) as [date],
                    district_name as district,
                    ROUND(SUM(precipitation_mm), 2) as rainfall_mm
                FROM [dbo].[silver_weather_current]
                GROUP BY CAST(last_updated AS DATE), district_name
                UNION ALL
                SELECT 
                    weather_date as [date],
                    district_name as district,
                    precipitation_sum as rainfall_mm
                FROM [dbo].[gold_district_daily_analytics]
            ) r
            WHERE (? IS NULL OR [date] >= ?)
              AND (? IS NULL OR [date] <= ?)
              AND (? IS NULL OR district = ? OR district LIKE ?)
            ORDER BY [date] DESC, district ASC
        """
        d_params = (
            start_date, start_date,
            end_date, end_date,
            clean_dist, clean_dist,
            f"%{clean_dist}%" if clean_dist else None,
        )
        daily_rows = await self._executor.execute_query(daily_sql, d_params)

        daily_data = []
        measured_count = 0
        missing_count = 0
        measured_zero_count = 0
        positive_count = 0
        total_measured_val = 0.0
        max_measured_val = 0.0

        for r in daily_rows:
            raw_val = r["rainfall_mm"]
            if raw_val is not None:
                val = round(float(raw_val), 2)
                measured_count += 1
                total_measured_val += val
                if val > max_measured_val:
                    max_measured_val = val
                if val > 0:
                    positive_count += 1
                else:
                    measured_zero_count += 1
                daily_data.append({
                    "date": _to_date_str(r["date"]),
                    "district": r["district"],
                    "rainfall_mm": val,
                    "category": r["category"],
                    "status": r["reporting_status"],
                    "is_rainy_day": bool(r["is_rainy_day"]),
                })
            else:
                missing_count += 1
                daily_data.append({
                    "date": _to_date_str(r["date"]),
                    "district": r["district"],
                    "rainfall_mm": None,  # Explicit NULL!
                    "category": "Unmeasured",
                    "status": "missing",
                    "is_rainy_day": None,
                })

        total_obs = measured_count + missing_count
        completeness_pct = round((measured_count / total_obs * 100.0), 1) if total_obs > 0 else 0.0

        rainfall_quality = {
            "total_observations": total_obs,
            "measured_observations": measured_count,
            "missing_observations": missing_count,
            "measured_zero_count": measured_zero_count,
            "positive_count": positive_count,
            "completeness_pct": completeness_pct,
            "status": "complete" if missing_count == 0 else "partial" if measured_count > 0 else "unmeasured",
            "total_measured_rainfall_mm": round(total_measured_val, 2) if measured_count > 0 else None,
            "avg_measured_rainfall_mm": round(total_measured_val / measured_count, 2) if measured_count > 0 else None,
            "max_measured_rainfall_mm": round(max_measured_val, 2) if measured_count > 0 else None,
        }

        response_payload = {
            "status": "success",
            "data": daily_data,
            "rainfall_quality": rainfall_quality,
            "filters": {
                "start_date": _to_date_str(start_date),
                "end_date": _to_date_str(end_date),
                "district": clean_dist,
            },
            "metadata": {
                "source": "Microsoft Fabric Lakehouse ([dbo].[silver_weather_current], [dbo].[gold_district_rainfall_analytics])",
                "monthly_trends": monthly_data[:50],
                "heavy_rainfall_threshold_mm": 64.5,
                "moderate_rainfall_threshold_mm": 15.6,
            }
        }

        self._set_in_cache(cache_key, response_payload)
        return response_payload

    async def get_district_data(
        self,
        district_name: Optional[str] = None,
        district: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Get district-level intelligence for all 38 districts or a selected district."""
        validate_date_range(start_date, end_date)
        clean_dist = (district_name or district or "").strip() or None
        log.info("fetch_fabric_districts", district=clean_dist, start_date=str(start_date), end_date=str(end_date))

        cache_key = f"districts:{clean_dist}:{start_date}:{end_date}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        # Fetch dim_district master + aggregated weather metrics
        sql = """
            SELECT 
                d.district_id,
                d.district_name as district,
                d.latitude,
                d.longitude,
                d.reference_location,
                ROUND(AVG(w.avg_temp), 1) as avg_temp,
                ROUND(MAX(w.max_temp), 1) as max_temp,
                ROUND(MIN(w.min_temp), 1) as min_temp,
                SUM(w.rainfall_mm) as total_rainfall,
                ROUND(AVG(w.avg_humidity), 1) as avg_humidity
            FROM [dbo].[dim_district] d
            LEFT JOIN (
                SELECT 
                    district_name,
                    weather_date as [date],
                    temperature_2m_mean as avg_temp,
                    temperature_2m_max as max_temp,
                    temperature_2m_min as min_temp,
                    precipitation_sum as rainfall_mm,
                    relative_humidity_2m_mean as avg_humidity
                FROM [dbo].[gold_district_daily_analytics]
                UNION ALL
                SELECT 
                    district_name,
                    CAST(last_updated AS DATE) as [date],
                    AVG(temperature_c) as avg_temp,
                    MAX(temperature_c) as max_temp,
                    MIN(temperature_c) as min_temp,
                    SUM(precipitation_mm) as rainfall_mm,
                    AVG(humidity) as avg_humidity
                FROM [dbo].[silver_weather_current]
                GROUP BY district_name, CAST(last_updated AS DATE)
            ) w ON d.district_name = w.district_name
            WHERE (? IS NULL OR d.district_name = ? OR d.district_name LIKE ?)
              AND (? IS NULL OR w.[date] >= ?)
              AND (? IS NULL OR w.[date] <= ?)
            GROUP BY d.district_id, d.district_name, d.latitude, d.longitude, d.reference_location
            ORDER BY d.district_name ASC
        """
        params = (
            clean_dist, clean_dist, f"%{clean_dist}%" if clean_dist else None,
            start_date, start_date, end_date, end_date
        )
        rows = await self._executor.execute_query(sql, params)

        # Merge with live current weather conditions
        cw_sql = "SELECT district_name, temperature_c, feels_like_c, humidity, wind_kph, condition_text, last_updated, precipitation_mm FROM [dbo].[gold_current_weather_latest]"
        cw_map = {r["district_name"]: r for r in await self._executor.execute_query(cw_sql)}

        results = []
        for r in rows:
            name = r["district"]
            cw = cw_map.get(name, {})
            # If historical rainfall is NULL, use current measured rainfall when looking at recent intervals
            rf = _to_float(r["total_rainfall"])
            if rf is None and (end_date is None or end_date >= get_ist_today() - timedelta(days=2)):
                rf = _to_float(cw.get("precipitation_mm"))

            results.append({
                "district_id": r["district_id"],
                "district": name,
                "latitude": _to_float(r["latitude"]),
                "longitude": _to_float(r["longitude"]),
                "reference_location": r["reference_location"],
                "avg_temp": _to_float(r["avg_temp"]),
                "max_temp": _to_float(r["max_temp"]),
                "min_temp": _to_float(r["min_temp"]),
                "total_rainfall": rf,
                "avg_humidity": _to_float(r["avg_humidity"]),
                "wind_speed": _to_float(cw.get("wind_kph")),
                "current_temp": _to_float(cw.get("temperature_c")),
                "feels_like": _to_float(cw.get("feels_like_c")),
                "current_condition": cw.get("condition_text"),
                "last_updated": cw.get("last_updated"),
            })

        response_payload = {
            "status": "success",
            "data": results,
            "filters": {
                "district": clean_dist,
                "start_date": _to_date_str(start_date),
                "end_date": _to_date_str(end_date),
            },
            "metadata": {
                "source": "Microsoft Fabric Lakehouse ([dbo].[dim_district], [dbo].[gold_district_daily_analytics], [dbo].[silver_weather_current])",
                "total_districts": len(results),
            }
        }

        self._set_in_cache(cache_key, response_payload)
        return response_payload

    async def get_current_weather(
        self,
        district: Optional[str] = None,
        date_param: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Get live current weather or timestamped historical day observations.
        
        TODAY: Latest live snapshot from gold_current_weather_latest.
        YESTERDAY or other previous dates: Actual timestamped observations from silver_weather_current.
        """
        today_ist = get_ist_today()
        if date_param:
            validate_date_range(end_date=date_param)

        clean_dist = district.strip() if district else None
        target_date = date_param or today_ist
        is_today = (target_date == today_ist)

        cache_key = f"cw:{clean_dist}:{target_date}:{is_today}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        log.info("fetch_fabric_current_weather", district=clean_dist, target_date=str(target_date), is_today=is_today)

        if is_today:
            # Latest snapshot for Today
            sql = """
                SELECT 
                    district_name as district,
                    temperature_c as temperature,
                    feels_like_c as feels_like,
                    humidity,
                    wind_kph as wind_speed,
                    wind_direction,
                    pressure_mb as pressure,
                    condition_text as condition,
                    precipitation_mm,
                    uv_index,
                    cloud_cover,
                    visibility_km,
                    last_updated
                FROM [dbo].[gold_current_weather_latest]
                WHERE (? IS NULL OR district_name = ? OR district_name LIKE ?)
                ORDER BY district_name ASC
            """
            params = (clean_dist, clean_dist, f"%{clean_dist}%" if clean_dist else None)
            rows = await self._executor.execute_query(sql, params)
            source_tag = "Microsoft Fabric [dbo].[gold_current_weather_latest] (Live Ingestion)"
        else:
            # Query silver_weather_current for timestamped historical telemetry
            sql = """
                SELECT 
                    district_name as district,
                    ROUND(AVG(temperature_c), 1) as temperature,
                    ROUND(AVG(feels_like_c), 1) as feels_like,
                    ROUND(AVG(humidity), 0) as humidity,
                    ROUND(AVG(wind_kph), 1) as wind_speed,
                    MAX(wind_direction) as wind_direction,
                    ROUND(AVG(pressure_mb), 0) as pressure,
                    MAX(condition_text) as condition,
                    ROUND(SUM(precipitation_mm), 2) as precipitation_mm,
                    ROUND(AVG(uv_index), 1) as uv_index,
                    ROUND(AVG(cloud_cover), 0) as cloud_cover,
                    ROUND(AVG(visibility_km), 1) as visibility_km,
                    MAX(last_updated) as last_updated
                FROM [dbo].[silver_weather_current]
                WHERE CAST(last_updated AS DATE) = ?
                  AND (? IS NULL OR district_name = ? OR district_name LIKE ?)
                GROUP BY district_name
                ORDER BY district_name ASC
            """
            params = (target_date, clean_dist, clean_dist, f"%{clean_dist}%" if clean_dist else None)
            rows = await self._executor.execute_query(sql, params)
            source_tag = f"Microsoft Fabric [dbo].[silver_weather_current] (Historical Runs for {target_date})"

            # If no silver telemetry exists for that historical date, check gold_district_daily_analytics
            if not rows:
                gold_sql = """
                    SELECT 
                        district_name as district,
                        temperature_2m_mean as temperature,
                        temperature_2m_mean as feels_like,
                        relative_humidity_2m_mean as humidity,
                        wind_speed_10m_max as wind_speed,
                        'N' as wind_direction,
                        1012.0 as pressure,
                        'Historical Reanalysis' as condition,
                        precipitation_sum as precipitation_mm,
                        NULL as uv_index,
                        NULL as cloud_cover,
                        NULL as visibility_km,
                        CAST(weather_date AS VARCHAR) + ' 23:59' as last_updated
                    FROM [dbo].[gold_district_daily_analytics]
                    WHERE weather_date = ?
                      AND (? IS NULL OR district_name = ? OR district_name LIKE ?)
                    ORDER BY district_name ASC
                """
                rows = await self._executor.execute_query(gold_sql, (target_date, clean_dist, clean_dist, f"%{clean_dist}%" if clean_dist else None))
                source_tag = f"Microsoft Fabric [dbo].[gold_district_daily_analytics] ({target_date})"

        if not rows:
            return {
                "status": "unavailable",
                "data": [],
                "message": f"Historical weather observations for {target_date} are not available in the Lakehouse.",
                "filters": {
                    "district": clean_dist,
                    "date": _to_date_str(target_date),
                },
                "metadata": {
                    "source": source_tag,
                    "count": 0,
                    "target_date": _to_date_str(target_date),
                }
            }

        results = [
            {
                "district": r["district"],
                "temperature": _to_float(r["temperature"]),
                "feels_like": _to_float(r["feels_like"]),
                "humidity": _to_float(r["humidity"]),
                "wind_speed": _to_float(r["wind_speed"]),
                "wind_direction": r["wind_direction"] or "N",
                "pressure": _to_float(r["pressure"]),
                "condition": r["condition"] or "Clear",
                "precipitation_mm": _to_float(r["precipitation_mm"]),  # None if missing!
                "uv_index": _to_float(r["uv_index"]),
                "cloud_cover": _to_float(r["cloud_cover"]),
                "visibility_km": _to_float(r["visibility_km"]),
                "last_updated": r["last_updated"],
                "observation_date": _to_date_str(target_date),
                "source": source_tag,
            }
            for r in rows
        ]

        response_payload = {
            "status": "success",
            "source": source_tag,
            "data": results,
            "filters": {
                "district": clean_dist,
                "date": _to_date_str(target_date),
                "observation_date": _to_date_str(target_date),
            },
            "metadata": {
                "source": source_tag,
                "count": len(results),
                "is_today": is_today,
                "target_date": _to_date_str(target_date),
            }
        }

        self._set_in_cache(cache_key, response_payload)
        return response_payload

    async def get_air_quality(
        self,
        district: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Get air quality metrics and pollutant classifications from gold_air_quality_latest."""
        validate_date_range(start_date, end_date)
        log.info("fetch_fabric_air_quality", district=district)
        clean_dist = district.strip() if district else None

        cache_key = f"aq:{clean_dist}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        sql = """
            SELECT 
                district_name as district,
                us_epa_index as aqi,
                us_epa_category as category,
                aqi_pm2_5 as pm25,
                aqi_pm10 as pm10,
                aqi_co as co,
                aqi_no2 as no2,
                aqi_so2 as so2,
                aqi_o3 as o3,
                us_epa_index,
                us_epa_category,
                gb_defra_index,
                gb_defra_category,
                last_updated
            FROM [dbo].[gold_air_quality_latest]
            WHERE (? IS NULL OR district_name = ? OR district_name LIKE ?)
            ORDER BY us_epa_index DESC, aqi_pm2_5 DESC
        """
        params = (clean_dist, clean_dist, f"%{clean_dist}%" if clean_dist else None)
        rows = await self._executor.execute_query(sql, params)

        results = []
        for r in rows:
            pm25 = _to_float(r["pm25"], 0.0)
            pm10 = _to_float(r["pm10"], 0.0)
            o3 = _to_float(r["o3"], 0.0)
            dominant = "PM2.5" if pm25 >= 35.0 else "PM10" if pm10 >= 50.0 else "O3" if o3 >= 100.0 else "PM2.5"

            results.append({
                "district": r["district"],
                "aqi": int(r["aqi"] or 1),
                "category": r["category"] or "Good",
                "dominant_pollutant": dominant,
                "pm25": pm25,
                "pm10": pm10,
                "co": _to_float(r["co"], 0.0),
                "no2": _to_float(r["no2"], 0.0),
                "so2": _to_float(r["so2"], 0.0),
                "o3": _to_float(r["o3"], 0.0),
                "us_epa_index": int(r["us_epa_index"] or 1),
                "us_epa_category": r["us_epa_category"] or "Good",
                "gb_defra_index": int(r["gb_defra_index"] or 1),
                "gb_defra_category": r["gb_defra_category"] or "Low",
                "last_updated": r["last_updated"],
            })

        response_payload = {
            "status": "success",
            "data": results,
            "filters": {"district": clean_dist},
            "metadata": {
                "source": "Microsoft Fabric Lakehouse [dbo].[gold_air_quality_latest]",
                "standard": "US EPA Air Quality Index (1-6) & UK DEFRA Index (1-10)",
                "count": len(results),
            }
        }

        self._set_in_cache(cache_key, response_payload)
        return response_payload

    async def compare_periods(
        self,
        period_a_start: date,
        period_a_end: date,
        period_b_start: date,
        period_b_end: date,
        district: Optional[str] = None,
        period_a_label: str = "Current Period",
        period_b_label: str = "Previous Period",
    ) -> Dict[str, Any]:
        """Perform comparative meteorological analysis between two periods."""
        validate_date_range(period_a_start, period_a_end)
        validate_date_range(period_b_start, period_b_end)

        clean_dist = district.strip() if district else None

        # Fetch overview aggregates for both periods
        res_a = await self.get_overview(start_date=period_a_start, end_date=period_a_end)
        res_b = await self.get_overview(start_date=period_b_start, end_date=period_b_end)

        d_a = res_a["data"]
        d_b = res_b["data"]

        temp_a = d_a.get("avg_temperature")
        temp_b = d_b.get("avg_temperature")
        temp_diff = round(temp_a - temp_b, 2) if temp_a is not None and temp_b is not None else None
        temp_pct = _calculate_pct_change(temp_a, temp_b)

        rain_a = d_a.get("total_rainfall")
        rain_b = d_b.get("total_rainfall")
        rain_diff = round(rain_a - rain_b, 2) if rain_a is not None and rain_b is not None else None
        rain_pct = _calculate_pct_change(rain_a, rain_b)

        hum_a = d_a.get("avg_humidity")
        hum_b = d_b.get("avg_humidity")
        hum_diff = round(hum_a - hum_b, 1) if hum_a is not None and hum_b is not None else None
        hum_pct = _calculate_pct_change(hum_a, hum_b)

        return {
            "status": "success",
            "data": {
                "period_a_label": period_a_label,
                "period_b_label": period_b_label,
                "period_a_range": {"start": _to_date_str(period_a_start), "end": _to_date_str(period_a_end)},
                "period_b_range": {"start": _to_date_str(period_b_start), "end": _to_date_str(period_b_end)},
                "district": clean_dist or "Statewide",
                "temperature": {
                    "current_val": temp_a,
                    "previous_val": temp_b,
                    "absolute_change": temp_diff,
                    "percentage_change": temp_pct,
                    "direction": "up" if (temp_diff or 0) > 0 else "down" if (temp_diff or 0) < 0 else "neutral",
                    "unit": "°C",
                },
                "rainfall": {
                    "current_val": rain_a,
                    "previous_val": rain_b,
                    "absolute_change": rain_diff,
                    "percentage_change": rain_pct,
                    "direction": "up" if (rain_diff or 0) > 0 else "down" if (rain_diff or 0) < 0 else "neutral",
                    "unit": "mm",
                },
                "humidity": {
                    "current_val": hum_a,
                    "previous_val": hum_b,
                    "absolute_change": hum_diff,
                    "percentage_change": hum_pct,
                    "direction": "up" if (hum_diff or 0) > 0 else "down" if (hum_diff or 0) < 0 else "neutral",
                    "unit": "%",
                },
            }
        }

    async def get_historical_data(
        self,
        district: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Get unified historical weather observations for analytics."""
        validate_date_range(start_date, end_date)
        clean_dist = district.strip() if district else None

        cache_key = f"historical:{clean_dist}:{start_date}:{end_date}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        sql = """
            SELECT TOP 500
                [date],
                district,
                ROUND(AVG(avg_temp), 1) as avg_temp,
                ROUND(MAX(max_temp), 1) as max_temp,
                ROUND(MIN(min_temp), 1) as min_temp,
                ROUND(SUM(rainfall_mm), 2) as rainfall_mm,
                ROUND(AVG(humidity), 1) as avg_humidity
            FROM (
                SELECT 
                    weather_date as [date],
                    district_name as district,
                    temperature_2m_mean as avg_temp,
                    temperature_2m_max as max_temp,
                    temperature_2m_min as min_temp,
                    precipitation_sum as rainfall_mm,
                    relative_humidity_2m_mean as humidity
                FROM [dbo].[gold_district_daily_analytics]
                UNION ALL
                SELECT 
                    CAST(last_updated AS DATE) as [date],
                    district_name as district,
                    AVG(temperature_c) as avg_temp,
                    MAX(temperature_c) as max_temp,
                    MIN(temperature_c) as min_temp,
                    SUM(precipitation_mm) as rainfall_mm,
                    AVG(humidity) as humidity
                FROM [dbo].[silver_weather_current]
                GROUP BY district_name, CAST(last_updated AS DATE)
            ) unified
            WHERE 1=1
        """
        params = []
        if clean_dist:
            sql += " AND district = ?"
            params.append(clean_dist)
        if start_date:
            sql += " AND [date] >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND [date] <= ?"
            params.append(end_date)

        sql += " GROUP BY [date], district ORDER BY [date] DESC, district ASC"

        rows = await self.qe.execute_query(sql, params)
        res = {
            "status": "success",
            "count": len(rows),
            "data": rows,
            "filters": {
                "district": clean_dist,
                "start_date": str(start_date) if start_date else None,
                "end_date": str(end_date) if end_date else None,
            },
            "source": "microsoft_fabric_lakehouse",
        }
        self._set_cache(cache_key, res)
        return res

