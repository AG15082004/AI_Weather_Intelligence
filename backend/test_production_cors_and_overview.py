"""Production Acceptance Tests for CORS, Error Resilience, and Weather APIs.

Addresses the requirements of Phase 10 Production Bug Fix:
1. CORS allowed frontend origin (https://ai-weather-intelligence-1.onrender.com).
2. CORS rejected unauthorized origin.
3. OPTIONS preflight validation.
4. CORS headers on HTTP 500 internal server error.
5. /api/overview successful response structure.
6. Fabric connection failure resilience (graceful handling, no 500).
7. Cached data response with data reliability metadata.
8. Empty cache and unavailable response (zero fabricated metrics).
9. Correct rainfall NULL preservation (strict NULL semantics).
10. All weather API response schemas (/overview, /temperature, /rainfall, /districts, /current, /air-quality, /health, /ai/health, /monitoring/operational-status).
"""

import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.database.query_executor import QueryExecutor
from app.main import app
from app.services.data_reliability_service import data_reliability_service
from app.services.weather_service import WeatherService

weather_service = WeatherService()


class TestProductionCorsAndOverview(unittest.TestCase):
    """Test suite validating CORS and weather endpoint resilience."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)
        weather_service._cache.clear()
        data_reliability_service.reset()

    def tearDown(self):
        weather_service._cache.clear()
        data_reliability_service.reset()

    # 1. CORS Allowed Frontend Origin
    def test_01_cors_allowed_frontend_origin(self):
        """GET request from deployed frontend origin receives Access-Control-Allow-Origin."""
        response = self.client.get(
            "/api/health",
            headers={"Origin": "https://ai-weather-intelligence-1.onrender.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "https://ai-weather-intelligence-1.onrender.com",
        )
        self.assertIsNone(response.headers.get("access-control-allow-credentials"))

    # 2. CORS Rejected Unauthorized Origin
    def test_02_cors_rejected_unauthorized_origin(self):
        """Request from unauthorized origin must NOT receive access-control-allow-origin."""
        response = self.client.get(
            "/api/health",
            headers={"Origin": "https://malicious-site.example.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.headers.get("access-control-allow-origin"))

    # 3. OPTIONS Preflight
    def test_03_options_preflight(self):
        """OPTIONS preflight from production frontend succeeds with correct CORS headers."""
        response = self.client.options(
            "/api/overview",
            headers={
                "Origin": "https://ai-weather-intelligence-1.onrender.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "https://ai-weather-intelligence-1.onrender.com",
        )
        self.assertIn("GET", response.headers.get("access-control-allow-methods", ""))

    # 4. CORS Headers on HTTP 500
    def test_04_cors_headers_on_http_500(self):
        """Even if an internal server error occurs, CORS headers MUST be attached."""
        with patch.object(WeatherService, "get_overview", side_effect=RuntimeError("Simulated server crash")):
            response = self.client.get(
                "/api/overview",
                headers={"Origin": "https://ai-weather-intelligence-1.onrender.com"},
            )
            self.assertEqual(response.status_code, 500)
            self.assertEqual(
                response.headers.get("access-control-allow-origin"),
                "https://ai-weather-intelligence-1.onrender.com",
            )
            data = response.json()
            self.assertEqual(data.get("status"), "error")
            self.assertIn("internal server error", data.get("message", "").lower())

    # 5. /api/overview Successful Response
    def test_05_api_overview_successful_response(self):
        """Successful /api/overview response includes required structure and trends."""
        mock_agg = [{
            "districts_covered": 38,
            "avg_temperature": 30.5,
            "max_temperature": 36.2,
            "min_temperature": 21.0,
            "avg_humidity": 68.0,
        }]
        mock_latest = [{"latest_observation": "2026-11-13 10:00:00"}]
        mock_temp_trend = [
            {"date": "2026-11-12", "avg_temp": 30.0, "max_temp": 35.0, "min_temp": 22.0}
        ]
        mock_rain_trend = [
            {
                "date": "2026-11-12",
                "raw_rainfall": 15.4,
                "measured_count": 38,
                "total_readings": 38,
                "peak_single_reading": 30.0,
            }
        ]
        mock_dist_comp = [
            {"district": "Chennai", "avg_temp": 31.0, "max_temp": 34.0, "min_temp": 26.0, "total_rainfall": 5.0, "avg_humidity": 70.0}
        ]
        mock_cw = [
            {"district_name": "Chennai", "temperature_c": 31.5, "condition_text": "Sunny", "wind_kph": 12.0, "precipitation_mm": 0.0}
        ]

        async def mock_execute(sql, params=None):
            if "COUNT(DISTINCT district)" in sql:
                return mock_agg
            if "MAX(last_updated)" in sql:
                return mock_latest
            if "t.avg_temp" in sql or "temperature_2m_mean as avg_temp" in sql:
                return mock_temp_trend
            if "SUM(rainfall_mm)" in sql or "precipitation_sum as rainfall_mm" in sql:
                return mock_rain_trend
            if "gold_current_weather_latest" in sql:
                return mock_cw
            return mock_dist_comp

        with patch.object(QueryExecutor, "execute_query", side_effect=mock_execute):
            response = self.client.get(
                "/api/overview",
                headers={"Origin": "https://ai-weather-intelligence-1.onrender.com"},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data.get("status"), "success")
            self.assertEqual(data.get("data_status"), "LIVE")
            self.assertIn("data", data)
            self.assertEqual(data["data"]["districts_covered"], 38)
            self.assertEqual(data["data"]["avg_temperature"], 30.5)

    # 6. Fabric Connection Failure (Resilience)
    def test_06_fabric_connection_failure_resilience(self):
        """When Fabric is unreachable, /api/overview returns 200 with UNAVAILABLE status, not 500."""
        with patch.object(QueryExecutor, "execute_query", side_effect=Exception("Fabric SQL login failed")):
            response = self.client.get(
                "/api/overview",
                headers={"Origin": "https://ai-weather-intelligence-1.onrender.com"},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data.get("status"), "unavailable")
            self.assertEqual(data.get("data_status"), "UNAVAILABLE")
            self.assertIn("warning", data)
            self.assertIn("unreachable", data["warning"].lower())

    # 7. Cached Data Response
    def test_07_cached_data_response(self):
        """Cached data is returned with [CACHED] data status and cache metadata."""
        # Seed cache
        cached_payload = {
            "status": "success",
            "data_status": "CACHED",
            "data": {"districts_covered": 38, "avg_temperature": 29.8},
            "metadata": {"latest_observation": "2026-11-13 06:00:00"},
        }
        weather_service._set_in_cache("overview:None:None", cached_payload)

        response = self.client.get(
            "/api/overview",
            headers={"Origin": "https://ai-weather-intelligence-1.onrender.com"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("data_status"), "CACHED")
        self.assertEqual(data["data"]["avg_temperature"], 29.8)

    # 8. Empty Cache and Unavailable Response
    def test_08_empty_cache_and_unavailable_response(self):
        """When cache is empty and Fabric is down, returns UNAVAILABLE without fabricated data."""
        with patch.object(QueryExecutor, "execute_query", side_effect=ConnectionError("Azure CLI not found")):
            response = self.client.get(
                "/api/overview?start_date=2026-11-06&end_date=2026-11-12",
                headers={"Origin": "https://ai-weather-intelligence-1.onrender.com"},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data.get("status"), "unavailable")
            self.assertEqual(data.get("data_status"), "UNAVAILABLE")
            self.assertIsNone(data["data"]["avg_temperature"])
            self.assertIsNone(data["data"]["total_rainfall"])

    # 9. Correct Rainfall NULL Preservation
    def test_09_rainfall_null_preservation(self):
        """Unmeasured historical rainfall must be preserved as NULL, never coerced to 0.0."""
        mock_rain_trend = [
            {
                "date": "2026-11-08",
                "raw_rainfall": None,
                "measured_count": 0,
                "total_readings": 38,
                "peak_single_reading": None,
            }
        ]

        async def mock_execute(sql, params=None):
            if "SUM(rainfall_mm)" in sql or "precipitation_sum as rainfall_mm" in sql:
                return mock_rain_trend
            if "MAX(last_updated)" in sql:
                return [{"latest_observation": "2026-11-13 10:00:00"}]
            if "COUNT(DISTINCT district)" in sql:
                return [{"districts_covered": 38, "avg_temperature": 30.0, "max_temperature": 35.0, "min_temperature": 25.0, "avg_humidity": 65.0}]
            return []

        with patch.object(QueryExecutor, "execute_query", side_effect=mock_execute):
            response = self.client.get(
                "/api/overview",
                headers={"Origin": "https://ai-weather-intelligence-1.onrender.com"},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            trend = data["data"]["rainfall_trend"]
            self.assertTrue(len(trend) > 0)
            # Must be None / null
            self.assertIsNone(trend[0]["rainfall_mm"])
            self.assertEqual(trend[0]["status"], "missing")
            self.assertEqual(trend[0]["category"], "Unmeasured")

    # 10. All Weather API Response Schemas
    def test_10_all_weather_api_response_schemas(self):
        """Verify schema consistency across all primary weather and operational endpoints."""
        endpoints = [
            ("/api/health", 200),
            ("/api/overview", 200),
            ("/api/temperature", 200),
            ("/api/rainfall", 200),
            ("/api/districts", 200),
            ("/api/weather/current", 200),
            ("/api/air-quality", 200),
            ("/api/ai/health", 200),
            ("/api/monitoring/operational-status", 200),
            ("/api/monitoring/metrics", 200),
        ]

        # Use graceful offline mock for Fabric to test schema resilience
        with patch.object(QueryExecutor, "execute_query", side_effect=Exception("Fabric offline simulation")):
            for path, expected_status in endpoints:
                res = self.client.get(
                    path,
                    headers={"Origin": "https://ai-weather-intelligence-1.onrender.com"},
                )
                self.assertEqual(
                    res.status_code,
                    expected_status,
                    f"Endpoint {path} failed with {res.status_code}: {res.text}",
                )
                self.assertEqual(
                    res.headers.get("access-control-allow-origin"),
                    "https://ai-weather-intelligence-1.onrender.com",
                    f"Endpoint {path} missing CORS allow-origin header",
                )
                # Verify JSON structure
                body = res.json()
                self.assertIsInstance(body, dict)


if __name__ == "__main__":
    unittest.main()
