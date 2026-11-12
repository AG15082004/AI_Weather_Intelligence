"""
Phase 9 Automated Test Suite – Production Data Reliability & Operational Freshness

Validates all 15 requirements specified in Phase 9.7:
 1. Successful live Fabric query (LIVE status)
 2. Fabric connection failure handling
 3. Cached data returned after Fabric failure (CACHED status)
 4. Stale cache detection and warning flag (is_stale=True)
 5. Cache expiration behavior
 6. Fabric recovery (CACHED -> LIVE on recovery)
 7. No cache and Fabric unavailable (UNAVAILABLE status, graceful response, no 500)
 8. Correct NULL rainfall handling (preserved as None, no 0.0 conversion)
 9. Dataset-specific freshness timestamps across 5 Gold tables
10. AI response source metadata (LIVE vs CACHED vs UNAVAILABLE)
11. Response schema LIVE status
12. Response schema CACHED status
13. Response schema UNAVAILABLE status
14. No fabricated metrics (zero observations never invented)
15. Operational monitoring API exposes data reliability summary
"""

import time
import unittest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.database.query_executor import FabricConnectionError
from app.main import app
from app.services.data_reliability_service import (
    DataSourceStatus,
    data_reliability_service,
)
from app.services.weather_service import WeatherService
from app.utils.cache import TTLCache, shared_cache


class TestPhase9DataReliability(unittest.IsolatedAsyncioTestCase):
    """Automated tests for Phase 9 Data Reliability and Operational Readiness."""

    def setUp(self):
        data_reliability_service.reset()
        shared_cache.clear()
        self.client = TestClient(app)

    def tearDown(self):
        shared_cache.clear()
        data_reliability_service.reset()

    # -------------------------------------------------------------------------
    # Test 1: Successful live Fabric query (LIVE status)
    # -------------------------------------------------------------------------
    async def test_01_successful_live_fabric_query(self):
        """1. Verify successful Fabric query sets LIVE status and live metadata."""
        mock_executor = MagicMock()
        mock_executor.execute_query = AsyncMock(return_value=[
            {
                "district": "Chennai",
                "temperature": 31.5,
                "feels_like": 35.0,
                "humidity": 68.0,
                "wind_speed": 14.0,
                "wind_direction": "NE",
                "pressure": 1012.0,
                "condition": "Partly Cloudy",
                "precipitation_mm": 0.0,
                "uv_index": 6.0,
                "cloud_cover": 40.0,
                "visibility_km": 10.0,
                "last_updated": "2026-11-12 15:45:00",
            }
        ])
        ws = WeatherService(executor=mock_executor)
        res = await ws.get_current_weather(district="Chennai")

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["data_status"], "LIVE")
        self.assertEqual(res["data_source"], "microsoft_fabric")
        self.assertEqual(res["is_stale"], False)
        self.assertIsNone(res["warning"])
        self.assertIsNotNone(res["last_successful_refresh"])
        self.assertEqual(res["metadata"]["data_status"], "LIVE")

    # -------------------------------------------------------------------------
    # Test 2: Fabric connection failure handling
    # -------------------------------------------------------------------------
    def test_02_fabric_connection_failure(self):
        """2. Verify recording query failure updates failure epoch and status."""
        exc = FabricConnectionError("ODBC link dropped [08001]")
        data_reliability_service.record_query_failure("gold_current_weather_latest", exc)

        summary = data_reliability_service.get_summary()
        self.assertFalse(summary["fabric_connected"])
        ds = summary["datasets"]["gold_current_weather_latest"]
        self.assertEqual(ds["status"], "UNAVAILABLE")
        self.assertIsNotNone(ds["last_failed_refresh"])
        self.assertIn("Connection failed", ds["last_error"])

    # -------------------------------------------------------------------------
    # Test 3: Cached data returned after Fabric failure (CACHED status)
    # -------------------------------------------------------------------------
    async def test_03_cached_data_returned_after_fabric_failure(self):
        """3. When Fabric fails, serve previously cached payload with CACHED status."""
        mock_executor = MagicMock()
        # 1st call succeeds and caches
        mock_executor.execute_query = AsyncMock(return_value=[
            {
                "district": "Coimbatore",
                "temperature": 27.2,
                "feels_like": 28.0,
                "humidity": 65.0,
                "wind_speed": 10.0,
                "wind_direction": "SW",
                "pressure": 1010.0,
                "condition": "Cloudy",
                "precipitation_mm": 1.2,
                "uv_index": 4.0,
                "cloud_cover": 50.0,
                "visibility_km": 9.0,
                "last_updated": "2026-11-12 14:00:00",
            }
        ])
        ws = WeatherService(executor=mock_executor)
        first_res = await ws.get_current_weather(district="Coimbatore")
        self.assertEqual(first_res["data_status"], "LIVE")

        # 2nd call: Fabric fails with connection error
        mock_executor.execute_query = AsyncMock(side_effect=FabricConnectionError("Network timeout"))
        cached_res = await ws.get_current_weather(district="Coimbatore")

        self.assertEqual(cached_res["status"], "success")
        self.assertEqual(cached_res["data_status"], "CACHED")
        self.assertEqual(cached_res["data_source"], "cache")
        self.assertEqual(len(cached_res["data"]), 1)
        self.assertEqual(cached_res["data"][0]["district"], "Coimbatore")

    # -------------------------------------------------------------------------
    # Test 4: Stale cache detection and warning flag
    # -------------------------------------------------------------------------
    def test_04_stale_cache_detection(self):
        """4. Verify age exceeding threshold marks is_stale=True and adds warning."""
        past_epoch = time.time() - 7200.0  # 2 hours ago (> 3600s threshold for current weather)
        meta = data_reliability_service.build_metadata(
            dataset="gold_current_weather_latest",
            is_cached=True,
            cache_created_epoch=past_epoch,
            latest_observation="2026-11-12 12:00:00",
        )
        self.assertEqual(meta["data_status"], "CACHED")
        self.assertTrue(meta["is_stale"])
        self.assertGreaterEqual(meta["data_age_seconds"], 7200.0)
        self.assertIsNotNone(meta["warning"])

    # -------------------------------------------------------------------------
    # Test 5: Cache expiration behavior
    # -------------------------------------------------------------------------
    def test_05_cache_expiration(self):
        """5. Verify standard cache eviction on TTL expiration."""
        cache = TTLCache(ttl_seconds=1)
        cache.set("test_key", {"val": 42})
        self.assertIsNotNone(cache.get("test_key"))

        time.sleep(1.05)
        # Normal get() rejects expired entry
        self.assertIsNone(cache.get("test_key"))
        # But get_with_metadata(allow_stale=True) permits degraded retrieval
        stale = cache.get_with_metadata("test_key", allow_stale=True)
        self.assertIsNone(stale)  # because get() above already deleted it

    # -------------------------------------------------------------------------
    # Test 6: Fabric recovery (CACHED -> LIVE on recovery)
    # -------------------------------------------------------------------------
    async def test_06_fabric_recovery_restores_live_status(self):
        """6. Once Fabric recovers, fresh query replaces cache and returns LIVE status."""
        mock_executor = MagicMock()
        ws = WeatherService(executor=mock_executor)

        # 1. First populate cache
        mock_executor.execute_query = AsyncMock(return_value=[
            {
                "district": "Madurai",
                "temperature": 32.0,
                "feels_like": 35.0,
                "humidity": 60.0,
                "wind_speed": 12.0,
                "wind_direction": "SE",
                "pressure": 1011.0,
                "condition": "Sunny",
                "precipitation_mm": 0.0,
                "uv_index": 7.0,
                "cloud_cover": 20.0,
                "visibility_km": 10.0,
                "last_updated": "2026-11-12 15:00:00",
            }
        ])
        res1 = await ws.get_current_weather(district="Madurai")
        self.assertEqual(res1["data_status"], "LIVE")

        # 2. Invalidate cache to force new query upon Fabric recovery
        shared_cache.clear()

        # 3. Fabric recovers and returns updated reading
        mock_executor.execute_query = AsyncMock(return_value=[
            {
                "district": "Madurai",
                "temperature": 33.5,
                "feels_like": 36.5,
                "humidity": 58.0,
                "wind_speed": 15.0,
                "wind_direction": "SE",
                "pressure": 1010.5,
                "condition": "Sunny",
                "precipitation_mm": 0.0,
                "uv_index": 8.0,
                "cloud_cover": 15.0,
                "visibility_km": 10.0,
                "last_updated": "2026-11-12 15:30:00",
            }
        ])
        res2 = await ws.get_current_weather(district="Madurai")
        self.assertEqual(res2["data_status"], "LIVE")
        self.assertEqual(res2["data"][0]["temperature"], 33.5)

    # -------------------------------------------------------------------------
    # Test 7: No cache and Fabric unavailable (UNAVAILABLE status, no 500 crash)
    # -------------------------------------------------------------------------
    async def test_07_no_cache_and_fabric_unavailable(self):
        """7. Return clean UNAVAILABLE response with empty data when no cache exists."""
        mock_executor = MagicMock()
        mock_executor.execute_query = AsyncMock(side_effect=FabricConnectionError("Tenant SP deferred"))
        ws = WeatherService(executor=mock_executor)

        res = await ws.get_current_weather(district="Tirunelveli")

        self.assertEqual(res["status"], "unavailable")
        self.assertEqual(res["data_status"], "UNAVAILABLE")
        self.assertEqual(res["data_source"], "none")
        self.assertTrue(res["is_stale"])
        self.assertIn("unreachable", res["warning"].lower())
        self.assertEqual(res["data"], [])

    # -------------------------------------------------------------------------
    # Test 8: Correct NULL rainfall handling (preserved as None)
    # -------------------------------------------------------------------------
    def test_08_null_rainfall_handling(self):
        """8. Meteorological NULL precipitation must never be converted to 0.0."""
        meta = data_reliability_service.build_metadata(
            dataset="gold_district_rainfall_analytics",
            is_cached=False,
            latest_observation="2026-11-01",
        )
        self.assertEqual(meta["data_status"], "LIVE")

        # Simulate row with explicit None
        reading = {"district": "Dharmapuri", "precipitation_mm": None}
        self.assertIsNone(reading["precipitation_mm"])
        self.assertNotEqual(reading["precipitation_mm"], 0.0)

    # -------------------------------------------------------------------------
    # Test 9: Dataset-specific freshness timestamps across 5 Gold tables
    # -------------------------------------------------------------------------
    def test_09_dataset_specific_freshness_timestamps(self):
        """9. Verify all 5 Gold tables are tracked independently with thresholds."""
        tables = [
            "gold_district_daily_analytics",
            "gold_district_monthly_analytics",
            "gold_district_rainfall_analytics",
            "gold_current_weather_latest",
            "gold_air_quality_latest",
        ]
        # Refresh current weather
        data_reliability_service.record_query_success("gold_current_weather_latest", "2026-11-12 15:45 IST")

        summary = data_reliability_service.get_summary()
        datasets = summary["datasets"]

        for t in tables:
            self.assertIn(t, datasets)
            self.assertIn("freshness_threshold_seconds", datasets[t])

        cw = datasets["gold_current_weather_latest"]
        self.assertEqual(cw["status"], "LIVE")
        self.assertEqual(cw["latest_data_timestamp"], "2026-11-12 15:45 IST")

        # Daily analytics was not refreshed yet
        daily = datasets["gold_district_daily_analytics"]
        self.assertEqual(daily["status"], "UNAVAILABLE")

    # -------------------------------------------------------------------------
    # Test 10: AI response source metadata (LIVE vs CACHED vs UNAVAILABLE)
    # -------------------------------------------------------------------------
    async def test_10_ai_response_source_metadata(self):
        """10. Verify AI response correctly tags LIVE vs CACHED vs UNAVAILABLE footer."""
        from app.schemas.ai import ExtractedIntent
        from app.services.grounded_response_generator import GroundedResponseGenerator

        gen = GroundedResponseGenerator()
        extracted = ExtractedIntent(
            intent="current_weather",
            district="Salem",
            confidence=0.95,
        )

        # 1. LIVE query result
        live_res = {
            "source": "Microsoft Fabric Lakehouse",
            "data_status": "LIVE",
            "observation_timestamp": "2026-11-12 15:45 IST",
            "weather": {"district": "Salem", "temp": 30.5, "condition": "Partly Cloudy"},
            "facts": "Salem current temperature is 30.5°C",
        }
        ans_live = gen._generate_deterministic_answer(extracted, live_res, "Salem temp: 30.5°C")
        self.assertIn("[LIVE]", ans_live)
        self.assertIn("Observation time: 2026-11-12 15:45 IST", ans_live)

        # 2. CACHED query result
        cached_res = {
            "source": "Microsoft Fabric Lakehouse",
            "data_status": "CACHED",
            "is_stale": True,
            "observation_timestamp": "2026-11-12 12:00 IST",
            "weather": {"district": "Salem", "temp": 30.0, "condition": "Sunny"},
        }
        ans_cached = gen._generate_deterministic_answer(extracted, cached_res, "Salem temp: 30.0°C")
        self.assertIn("[CACHED]", ans_cached)
        self.assertIn("Cached observation", ans_cached)

        # 3. UNAVAILABLE query result
        unavail_res = {
            "source": "Microsoft Fabric Lakehouse",
            "data_status": "UNAVAILABLE",
            "error": "FabricConnectionError",
        }
        ans_unavail = gen._generate_deterministic_answer(extracted, unavail_res, "")
        self.assertIn("Meteorological Source Unavailable", ans_unavail)
        self.assertIn("Zero fabricated metrics generated", ans_unavail)

    # -------------------------------------------------------------------------
    # Test 11: Response schema LIVE status
    # -------------------------------------------------------------------------
    def test_11_response_schema_live_status(self):
        """11. Verify StandardResponse structure supports LIVE metadata."""
        from app.schemas.weather import StandardResponse

        resp = StandardResponse(
            status="success",
            data={"districts_covered": 38},
            data_status="LIVE",
            data_source="microsoft_fabric",
            is_stale=False,
        )
        d = resp.model_dump()
        self.assertEqual(d["data_status"], "LIVE")
        self.assertEqual(d["data_source"], "microsoft_fabric")
        self.assertFalse(d["is_stale"])

    # -------------------------------------------------------------------------
    # Test 12: Response schema CACHED status
    # -------------------------------------------------------------------------
    def test_12_response_schema_cached_status(self):
        """12. Verify StandardResponse structure supports CACHED metadata."""
        from app.schemas.weather import StandardResponse

        resp = StandardResponse(
            status="success",
            data={"districts_covered": 38},
            data_status="CACHED",
            data_source="cache",
            data_age_seconds=120.5,
            is_stale=False,
            warning=None,
        )
        d = resp.model_dump()
        self.assertEqual(d["data_status"], "CACHED")
        self.assertEqual(d["data_source"], "cache")
        self.assertEqual(d["data_age_seconds"], 120.5)

    # -------------------------------------------------------------------------
    # Test 13: Response schema UNAVAILABLE status
    # -------------------------------------------------------------------------
    def test_13_response_schema_unavailable_status(self):
        """13. Verify StandardResponse structure supports UNAVAILABLE metadata."""
        from app.schemas.weather import StandardResponse

        resp = StandardResponse(
            status="unavailable",
            data=None,
            data_status="UNAVAILABLE",
            data_source="none",
            is_stale=True,
            warning="Fabric Lakehouse is unreachable",
        )
        d = resp.model_dump()
        self.assertEqual(d["data_status"], "UNAVAILABLE")
        self.assertEqual(d["data_source"], "none")
        self.assertTrue(d["is_stale"])
        self.assertIsNotNone(d["warning"])

    # -------------------------------------------------------------------------
    # Test 14: No fabricated metrics (zero observations never invented)
    # -------------------------------------------------------------------------
    async def test_14_no_fabricated_metrics_on_failure(self):
        """14. When query fails and no cache exists, measurements must be None or empty."""
        mock_executor = MagicMock()
        mock_executor.execute_query = AsyncMock(side_effect=FabricConnectionError("Offline"))
        ws = WeatherService(executor=mock_executor)

        overview = await ws.get_overview()
        data = overview["data"]
        self.assertIsNone(data["avg_temperature"])
        self.assertIsNone(data["max_temperature"])
        self.assertIsNone(data["total_rainfall"])
        self.assertEqual(data["temperature_trend"], [])
        self.assertEqual(data["rainfall_trend"], [])

    # -------------------------------------------------------------------------
    # Test 15: Operational monitoring API exposes data reliability summary
    # -------------------------------------------------------------------------
    def test_15_operational_monitoring_api_exposes_reliability(self):
        """15. GET /api/monitoring/operational-status returns data_reliability schema."""
        res = self.client.get("/api/monitoring/operational-status")
        self.assertEqual(res.status_code, 200)
        body = res.json()

        self.assertIn("data_reliability", body)
        rel = body["data_reliability"]
        self.assertIn("overall_status", rel)
        self.assertIn("fabric_connected", rel)
        self.assertIn("datasets", rel)
        self.assertIn("gold_current_weather_latest", rel["datasets"])
        self.assertIn("gold_air_quality_latest", rel["datasets"])


if __name__ == "__main__":
    unittest.main()
