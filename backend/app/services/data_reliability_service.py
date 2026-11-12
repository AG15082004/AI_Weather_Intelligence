"""Data Reliability and Freshness Tracking Service.

Centralized status model and operational telemetry for Microsoft Fabric data sources:
- LIVE: Successful direct Fabric SQL query.
- CACHED: Previously retrieved data served from application cache.
- FALLBACK: Explicit fallback or static demonstration data.
- UNAVAILABLE: No usable data source is available.

Strictly manages independent freshness monitoring for the five Gold tables:
- gold_district_daily_analytics
- gold_district_monthly_analytics
- gold_district_rainfall_analytics
- gold_current_weather_latest
- gold_air_quality_latest

All timestamps are formatted and localized to Asia/Kolkata (IST).
"""

from datetime import datetime, timezone
from enum import Enum
import threading
import time
from typing import Any, Dict, List, Optional
import structlog

from app.utils.date_utils import IST_TZ, get_ist_now

log = structlog.get_logger()


class DataSourceStatus(str, Enum):
    """Centralized data source status classifications."""
    LIVE = "LIVE"
    CACHED = "CACHED"
    FALLBACK = "FALLBACK"
    UNAVAILABLE = "UNAVAILABLE"


# Default staleness thresholds in seconds per dataset
DATASET_FRESHNESS_THRESHOLDS: Dict[str, float] = {
    "gold_current_weather_latest": 3600.0,       # 1 hour
    "gold_air_quality_latest": 3600.0,           # 1 hour
    "gold_district_daily_analytics": 86400.0,    # 24 hours
    "gold_district_monthly_analytics": 2592000.0,# 30 days
    "gold_district_rainfall_analytics": 2592000.0,# 30 days
}

# Human-readable aliases
DATASET_ALIASES: Dict[str, str] = {
    "current_weather": "gold_current_weather_latest",
    "air_quality": "gold_air_quality_latest",
    "daily_analytics": "gold_district_daily_analytics",
    "temperature": "gold_district_daily_analytics",
    "rainfall": "gold_district_rainfall_analytics",
    "rainfall_analytics": "gold_district_rainfall_analytics",
    "monthly_analytics": "gold_district_monthly_analytics",
    "districts": "gold_district_daily_analytics",
    "overview": "gold_district_daily_analytics",
}


def format_ist_timestamp(dt: Optional[datetime] = None) -> str:
    """Format datetime into standard ISO representation in Asia/Kolkata."""
    if dt is None:
        dt = get_ist_now()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc).astimezone(IST_TZ)
    else:
        dt = dt.astimezone(IST_TZ)
    return dt.strftime("%Y-%m-%d %H:%M:%S IST")


class DataReliabilityService:
    """Centralized thread-safe registry tracking dataset status and freshness."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # Internal dataset state dictionary
        self._datasets: Dict[str, Dict[str, Any]] = {
            table: {
                "dataset_name": table,
                "status": DataSourceStatus.UNAVAILABLE.value,
                "last_successful_query_epoch": None,
                "last_successful_refresh": None,
                "latest_data_timestamp": None,
                "last_failed_query_epoch": None,
                "last_failed_refresh": None,
                "last_error": None,
                "total_successes": 0,
                "total_failures": 0,
                "source_available": False,
            }
            for table in DATASET_FRESHNESS_THRESHOLDS
        }
        self._fabric_is_connected = False
        self._last_connectivity_check = time.time()

    def _normalize_name(self, dataset: str) -> str:
        """Resolve dataset name to canonical Gold table name."""
        clean = dataset.strip().lower()
        clean = clean.replace("[dbo].", "").replace("[", "").replace("]", "")
        return DATASET_ALIASES.get(clean, clean)

    def record_query_success(
        self,
        dataset: str,
        latest_observation: Optional[str] = None,
    ) -> None:
        """Record successful direct Microsoft Fabric SQL execution.
        
        Args:
            dataset: Target dataset or table name.
            latest_observation: Optional underlying meteorological observation timestamp.
        """
        canonical = self._normalize_name(dataset)
        now_epoch = time.time()
        now_ist = format_ist_timestamp()

        with self._lock:
            self._fabric_is_connected = True
            self._last_connectivity_check = now_epoch

            if canonical not in self._datasets:
                self._datasets[canonical] = {
                    "dataset_name": canonical,
                    "total_successes": 0,
                    "total_failures": 0,
                }

            entry = self._datasets[canonical]
            entry["status"] = DataSourceStatus.LIVE.value
            entry["last_successful_query_epoch"] = now_epoch
            entry["last_successful_refresh"] = now_ist
            if latest_observation:
                entry["latest_data_timestamp"] = latest_observation
            entry["last_error"] = None
            entry["total_successes"] = entry.get("total_successes", 0) + 1
            entry["source_available"] = True

        log.debug("data_reliability_query_success", dataset=canonical, time=now_ist)

    def record_query_failure(
        self,
        dataset: str,
        error: Exception,
    ) -> None:
        """Record failed Microsoft Fabric SQL query.
        
        Args:
            dataset: Target dataset or table name.
            error: Raised exception.
        """
        canonical = self._normalize_name(dataset)
        now_epoch = time.time()
        now_ist = format_ist_timestamp()

        # Sanitize error message to prevent credential/connection string leakage
        raw_err = str(error)
        clean_err = "Connection failed or service unavailable"
        if "timeout" in raw_err.lower():
            clean_err = "Query timed out"
        elif "authentication" in raw_err.lower() or "login" in raw_err.lower():
            clean_err = "Authentication required or deferred"

        with self._lock:
            self._fabric_is_connected = False
            self._last_connectivity_check = now_epoch

            if canonical not in self._datasets:
                self._datasets[canonical] = {
                    "dataset_name": canonical,
                    "total_successes": 0,
                    "total_failures": 0,
                }

            entry = self._datasets[canonical]
            entry["last_failed_query_epoch"] = now_epoch
            entry["last_failed_refresh"] = now_ist
            entry["last_error"] = clean_err
            entry["total_failures"] = entry.get("total_failures", 0) + 1
            entry["source_available"] = False
            # If no previous success, mark UNAVAILABLE
            if not entry.get("last_successful_query_epoch"):
                entry["status"] = DataSourceStatus.UNAVAILABLE.value

        log.warning("data_reliability_query_failed", dataset=canonical, error=clean_err)

    def build_metadata(
        self,
        dataset: str,
        is_cached: bool = False,
        cache_created_epoch: Optional[float] = None,
        latest_observation: Optional[str] = None,
        is_fallback: bool = False,
        is_unavailable: bool = False,
    ) -> Dict[str, Any]:
        """Construct standard data reliability metadata for API responses."""
        canonical = self._normalize_name(dataset)
        now = time.time()

        with self._lock:
            entry = self._datasets.get(canonical, {})
            last_refresh = entry.get("last_successful_refresh")
            last_epoch = entry.get("last_successful_query_epoch")
            latest_obs = latest_observation or entry.get("latest_data_timestamp")

        if is_unavailable:
            return {
                "data_source": "none",
                "data_status": DataSourceStatus.UNAVAILABLE.value,
                "last_successful_refresh": last_refresh,
                "latest_observation_timestamp": latest_obs,
                "data_age_seconds": None,
                "is_stale": True,
                "warning": "Microsoft Fabric Lakehouse is currently unreachable and no cached data is available.",
            }

        if is_fallback:
            return {
                "data_source": "fallback",
                "data_status": DataSourceStatus.FALLBACK.value,
                "last_successful_refresh": last_refresh,
                "latest_observation_timestamp": latest_obs,
                "data_age_seconds": round(now - last_epoch, 1) if last_epoch else None,
                "is_stale": True,
                "warning": "Using static baseline fallback data.",
            }

        if is_cached:
            ref_epoch = cache_created_epoch or last_epoch or now
            age_sec = max(0.0, round(now - ref_epoch, 1))
            threshold = DATASET_FRESHNESS_THRESHOLDS.get(canonical, 3600.0)
            is_stale = age_sec > threshold

            warning_msg = None
            if not self._fabric_is_connected:
                warning_msg = "Microsoft Fabric is currently unreachable. Serving previously cached data."
            elif is_stale:
                warning_msg = f"Data was cached {int(age_sec)} seconds ago and may be stale."

            return {
                "data_source": "cache",
                "data_status": DataSourceStatus.CACHED.value,
                "last_successful_refresh": last_refresh or format_ist_timestamp(datetime.fromtimestamp(ref_epoch, tz=timezone.utc)),
                "latest_observation_timestamp": latest_obs,
                "data_age_seconds": age_sec,
                "is_stale": is_stale,
                "warning": warning_msg,
            }

        # Direct LIVE query
        return {
            "data_source": "microsoft_fabric",
            "data_status": DataSourceStatus.LIVE.value,
            "last_successful_refresh": format_ist_timestamp(),
            "latest_observation_timestamp": latest_obs,
            "data_age_seconds": 0.0,
            "is_stale": False,
            "warning": None,
        }

    def get_summary(self) -> Dict[str, Any]:
        """Generate comprehensive operational reliability summary across all 5 Gold datasets."""
        now = time.time()
        with self._lock:
            datasets_summary = {}
            total_active = 0
            any_live = False

            for name, threshold in DATASET_FRESHNESS_THRESHOLDS.items():
                entry = self._datasets.get(name, {})
                last_epoch = entry.get("last_successful_query_epoch")
                status = entry.get("status", DataSourceStatus.UNAVAILABLE.value)

                age_sec = round(now - last_epoch, 1) if last_epoch else None
                is_stale = (age_sec > threshold) if age_sec is not None else True

                if status == DataSourceStatus.LIVE.value:
                    any_live = True
                    total_active += 1
                elif status == DataSourceStatus.CACHED.value or last_epoch is not None:
                    total_active += 1

                datasets_summary[name] = {
                    "dataset_name": name,
                    "status": status,
                    "last_successful_refresh": entry.get("last_successful_refresh"),
                    "latest_data_timestamp": entry.get("latest_data_timestamp"),
                    "last_failed_refresh": entry.get("last_failed_refresh"),
                    "data_age_seconds": age_sec,
                    "is_stale": is_stale,
                    "source_available": entry.get("source_available", False),
                    "freshness_threshold_seconds": threshold,
                    "last_error": entry.get("last_error"),
                }

            overall_status = "healthy" if any_live and self._fabric_is_connected else "degraded" if total_active > 0 else "unavailable"

            return {
                "overall_status": overall_status,
                "fabric_connected": self._fabric_is_connected,
                "timezone": "Asia/Kolkata",
                "timestamp_ist": format_ist_timestamp(),
                "active_datasets_count": total_active,
                "total_datasets_count": len(DATASET_FRESHNESS_THRESHOLDS),
                "datasets": datasets_summary,
            }

    def reset(self) -> None:
        """Reset service state for testing."""
        with self._lock:
            self.__init__()


# Global singleton instance
data_reliability_service = DataReliabilityService()

