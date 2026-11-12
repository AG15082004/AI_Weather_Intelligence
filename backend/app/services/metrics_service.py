"""Operational Performance & Health Metrics Tracker.

Thread-safe, lightweight, in-memory metrics aggregation for APIs,
Microsoft Fabric queries, AI provider distribution, and data freshness.
No external time-series DB required (preserves zero-cost deployment).
"""

from collections import deque
from datetime import datetime, timezone
import threading
import time
from typing import Any, Dict, List, Optional
import structlog

log = structlog.get_logger()


class MetricsService:
    """Aggregates real-time performance and operational metrics."""

    _instance: Optional["MetricsService"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "MetricsService":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_metrics()
            return cls._instance

    def _init_metrics(self) -> None:
        self.start_time = time.time()
        self._lock_state = threading.Lock()

        # HTTP Requests
        self.total_requests = 0
        self.status_2xx = 0
        self.status_4xx = 0
        self.status_5xx = 0
        self._recent_durations: deque = deque(maxlen=200)

        # Fabric Lakehouse SQL
        self.fabric_total_queries = 0
        self.fabric_successful_queries = 0
        self.fabric_failed_queries = 0
        self.fabric_last_query_ts: Optional[str] = None
        self.fabric_consecutive_failures = 0
        self._recent_fabric_durations: deque = deque(maxlen=100)

        # AI Engine Telemetry
        self.ai_total_queries = 0
        self.ai_ollama_queries = 0
        self.ai_deterministic_queries = 0
        self.ai_failed_queries = 0
        self._recent_ai_durations: deque = deque(maxlen=100)

        # Data Freshness & Quality
        self.latest_observation_timestamp: Optional[str] = "2026-11-12 15:30"
        self.districts_reporting_count: int = 38
        self.total_districts_count: int = 38

    def record_request(
        self, path: str, method: str, status_code: int, duration_ms: float
    ) -> None:
        """Record an incoming HTTP request execution."""
        with self._lock_state:
            self.total_requests += 1
            if 200 <= status_code < 400:
                self.status_2xx += 1
            elif 400 <= status_code < 500:
                self.status_4xx += 1
            else:
                self.status_5xx += 1
            self._recent_durations.append(duration_ms)

    def record_fabric_query(self, success: bool, duration_ms: float) -> None:
        """Record a Microsoft Fabric SQL query execution."""
        with self._lock_state:
            self.fabric_total_queries += 1
            self.fabric_last_query_ts = datetime.now(timezone.utc).isoformat()
            if success:
                self.fabric_successful_queries += 1
                self.fabric_consecutive_failures = 0
                self._recent_fabric_durations.append(duration_ms)
            else:
                self.fabric_failed_queries += 1
                self.fabric_consecutive_failures += 1

    def record_ai_query(self, provider: str, duration_ms: float, success: bool) -> None:
        """Record an AI agent natural language query execution."""
        with self._lock_state:
            self.ai_total_queries += 1
            if provider == "ollama":
                self.ai_ollama_queries += 1
            else:
                self.ai_deterministic_queries += 1

            if not success:
                self.ai_failed_queries += 1
            else:
                self._recent_ai_durations.append(duration_ms)

    def record_data_freshness(
        self, latest_observation: Optional[str], districts_reporting: int = 38
    ) -> None:
        """Update telemetry data freshness status."""
        with self._lock_state:
            if latest_observation:
                self.latest_observation_timestamp = latest_observation
            self.districts_reporting_count = districts_reporting

    def get_summary(self) -> Dict[str, Any]:
        """Produce comprehensive operational metrics snapshot."""
        with self._lock_state:
            uptime = round(time.time() - self.start_time, 1)

            # Average response times
            avg_req_latency = (
                round(sum(self._recent_durations) / len(self._recent_durations), 1)
                if self._recent_durations
                else 0.0
            )
            avg_fabric_latency = (
                round(sum(self._recent_fabric_durations) / len(self._recent_fabric_durations), 1)
                if self._recent_fabric_durations
                else 0.0
            )
            avg_ai_latency = (
                round(sum(self._recent_ai_durations) / len(self._recent_ai_durations), 1)
                if self._recent_ai_durations
                else 0.0
            )

            # Fabric health status determination
            if self.fabric_consecutive_failures >= 3:
                fabric_status = "unavailable"
            elif self.fabric_consecutive_failures > 0 or self.fabric_total_queries == 0:
                fabric_status = "degraded" if self.fabric_consecutive_failures > 0 else "healthy"
            else:
                fabric_status = "healthy"

            coverage_pct = round(
                (self.districts_reporting_count / max(1, self.total_districts_count)) * 100.0, 1
            )

            return {
                "uptime_seconds": uptime,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "http_metrics": {
                    "total_requests": self.total_requests,
                    "status_2xx": self.status_2xx,
                    "status_4xx": self.status_4xx,
                    "status_5xx": self.status_5xx,
                    "avg_duration_ms": avg_req_latency,
                },
                "fabric_metrics": {
                    "status": fabric_status,
                    "total_queries": self.fabric_total_queries,
                    "successful_queries": self.fabric_successful_queries,
                    "failed_queries": self.fabric_failed_queries,
                    "consecutive_failures": self.fabric_consecutive_failures,
                    "avg_duration_ms": avg_fabric_latency,
                    "last_query_timestamp": self.fabric_last_query_ts,
                },
                "ai_metrics": {
                    "total_queries": self.ai_total_queries,
                    "ollama_queries": self.ai_ollama_queries,
                    "deterministic_queries": self.ai_deterministic_queries,
                    "failed_queries": self.ai_failed_queries,
                    "avg_duration_ms": avg_ai_latency,
                },
                "cache_metrics": self._get_cache_stats(),
                "data_freshness": {
                    "status": "healthy" if coverage_pct >= 95.0 else "degraded",
                    "latest_observation": self.latest_observation_timestamp,
                    "districts_reporting": self.districts_reporting_count,
                    "total_districts": self.total_districts_count,
                    "coverage_pct": coverage_pct,
                },
            }


    def _get_cache_stats(self) -> Dict[str, Any]:
        """Safely extract cache hit/miss statistics without circular import."""
        try:
            from app.utils.cache import shared_cache
            return shared_cache.get_stats()
        except Exception:
            return {"hits": 0, "misses": 0, "size": 0}


metrics_service = MetricsService()

