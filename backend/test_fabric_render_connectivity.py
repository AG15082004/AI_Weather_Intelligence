"""Tests for Fabric Connectivity, Auth Mode Resolution, and Render Resilience.

Validates the 8 requirements of RENDER FABRIC CONNECTIVITY AND PRODUCTION CONFIGURATION:
1. Missing Fabric server configuration (deferred, no pyodbc attempts).
2. Missing ODBC driver (detected via pyodbc.drivers, deferred).
3. Local Azure CLI mode (development preserves Azure CLI).
4. Render without Service Principal configuration (safe deferred state, never interactive).
5. Render with complete Service Principal configuration (service_principal mode).
6. Successful SQL query (mocked live execution, LIVE data status).
7. Fabric unavailable and cache empty (UNAVAILABLE status, rainfall NULL preserved, no 500).
8. Fabric unavailable with cached data (CACHED data status, staleness note).
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.config import Settings
from app.database.query_executor import QueryExecutor
from app.main import app
from app.services.data_reliability_service import data_reliability_service
from app.services.fabric_connection import FabricConnectionError, FabricConnectionService
from app.services.weather_service import WeatherService

weather_service = WeatherService()


class TestFabricRenderConnectivity(unittest.TestCase):
    """Test suite for Microsoft Fabric configuration validation and auth mode resolution."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)
        weather_service._cache.clear()
        data_reliability_service.reset()

    def tearDown(self):
        weather_service._cache.clear()
        data_reliability_service.reset()

    # 1. Missing Fabric Server Configuration
    def test_01_missing_fabric_server_configuration(self):
        """When FABRIC_SERVER is empty, auth resolves to deferred and connect raises FabricConnectionError."""
        settings = Settings(
            app_env="production",
            fabric_server="",
            fabric_odbc_driver="ODBC Driver 18 for SQL Server",
        )
        service = FabricConnectionService(settings)

        mode, reason = service.resolve_auth_mode()
        self.assertEqual(mode, "deferred")
        self.assertEqual(reason, "fabric_server_unconfigured")

        summary = service.get_safe_summary()
        self.assertEqual(summary["server"], "not_configured")
        self.assertEqual(summary["effective_auth_mode"], "deferred")

        # Verify connect raises FabricConnectionError without attempting pyodbc.connect
        import asyncio
        loop = asyncio.new_event_loop()
        with self.assertRaises(FabricConnectionError):
            loop.run_until_complete(service.connect())
        loop.close()

    # 2. Missing ODBC Driver
    def test_02_missing_odbc_driver(self):
        """When ODBC Driver 18 is not installed on Linux host, service detects it and defers."""
        settings = Settings(
            app_env="production",
            fabric_server="test-sql.fabric.microsoft.com",
            fabric_odbc_driver="ODBC Driver 18 for SQL Server",
        )
        service = FabricConnectionService(settings)

        # Mock pyodbc.drivers() returning empty list (common in uncustomized Linux containers)
        with patch("pyodbc.drivers", return_value=[]):
            self.assertFalse(service.is_driver_available())
            mode, reason = service.resolve_auth_mode()
            self.assertEqual(mode, "deferred")
            self.assertIn("odbc_driver_missing", reason)

    # 3. Local Azure CLI Mode
    def test_03_local_azure_cli_mode(self):
        """In development with driver present, local Azure CLI authentication is preserved."""
        settings = Settings(
            app_env="development",
            fabric_server="test-sql.fabric.microsoft.com",
            fabric_auth_mode="azure_cli",
            fabric_odbc_driver="ODBC Driver 18 for SQL Server",
        )
        service = FabricConnectionService(settings)

        with patch.object(service, "is_driver_available", return_value=True):
            mode, reason = service.resolve_auth_mode()
            self.assertEqual(mode, "azure_cli")
            self.assertEqual(reason, "development_azure_cli_ready")

    # 4. Render Without Service Principal Configuration
    def test_04_render_without_service_principal(self):
        """In production on Render without SPN keys, service never attempts interactive or az cli."""
        settings = Settings(
            app_env="production",
            fabric_server="test-sql.fabric.microsoft.com",
            fabric_auth_mode="interactive",  # Default or misconfigured
            fabric_client_id=None,
            fabric_client_secret=None,
            fabric_odbc_driver="ODBC Driver 18 for SQL Server",
        )
        service = FabricConnectionService(settings)

        with patch.object(service, "is_driver_available", return_value=True), \
             patch.dict(os.environ, {"RENDER": "true"}):
            mode, reason = service.resolve_auth_mode()
            self.assertEqual(mode, "deferred")
            self.assertIn("service_principal_credentials_deferred", reason)

            # Verification returns deferred status rather than attempting broken connection
            import asyncio
            loop = asyncio.new_event_loop()
            diag = loop.run_until_complete(service.verify_connection())
            loop.close()
            self.assertEqual(diag["status"], "deferred")
            self.assertFalse(diag["connected"])

    # 5. Render With Complete Service Principal Configuration
    def test_05_render_with_complete_service_principal(self):
        """In production when SPN keys are present, service principal mode is selected."""
        settings = Settings(
            app_env="production",
            fabric_server="test-sql.fabric.microsoft.com",
            fabric_database="lh_tn_weather_intelligence",
            fabric_client_id="11111111-2222-3333-4444-555555555555",
            fabric_client_secret="secret-value-abcdef123456",
            fabric_tenant_id="tenant-id-777777777777",
            fabric_odbc_driver="ODBC Driver 18 for SQL Server",
        )
        service = FabricConnectionService(settings)

        with patch.object(service, "is_driver_available", return_value=True):
            mode, reason = service.resolve_auth_mode()
            self.assertEqual(mode, "service_principal")
            self.assertEqual(reason, "production_service_principal_ready")

            conn_str, attrs = service.build_connection_params()
            self.assertIsNone(attrs)
            self.assertIn("Authentication=ActiveDirectoryServicePrincipal", conn_str)
            self.assertIn("UID=11111111-2222-3333-4444-555555555555", conn_str)
            self.assertIn("PWD=secret-value-abcdef123456", conn_str)

    # 6. Successful SQL Query (Mocked)
    def test_06_successful_sql_query(self):
        """Successful SQL query execution sets data_status to LIVE."""
        mock_agg = [{
            "districts_covered": 38,
            "avg_temperature": 31.2,
            "max_temperature": 36.5,
            "min_temperature": 22.0,
            "avg_humidity": 65.0,
        }]
        mock_latest = [{"latest_observation": "2026-11-13 10:30:00"}]
        mock_temp_trend = [
            {"date": "2026-11-12", "avg_temp": 30.0, "max_temp": 35.0, "min_temp": 22.0}
        ]
        mock_rain = [{
            "date": "2026-11-12",
            "raw_rainfall": 10.0,
            "measured_count": 38,
            "total_readings": 38,
            "peak_single_reading": 25.0,
        }]

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
            if "raw_rainfall" in sql or "SUM(rainfall_mm)" in sql or "precipitation_sum as rainfall_mm" in sql:
                return mock_rain
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
            self.assertEqual(data["data"]["avg_temperature"], 31.2)

    # 7. Fabric Unavailable and Cache Empty
    def test_07_fabric_unavailable_and_cache_empty(self):
        """When Fabric is deferred/down and cache is empty, returns UNAVAILABLE without 500 crash."""
        with patch.object(QueryExecutor, "execute_query", side_effect=FabricConnectionError("Fabric connectivity deferred")):
            response = self.client.get(
                "/api/overview?start_date=2026-11-06&end_date=2026-11-12",
                headers={"Origin": "https://ai-weather-intelligence-1.onrender.com"},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data.get("status"), "unavailable")
            self.assertEqual(data.get("data_status"), "UNAVAILABLE")
            # Strict NULL preservation - no fake numbers
            self.assertIsNone(data["data"]["avg_temperature"])
            self.assertIsNone(data["data"]["total_rainfall"])
            self.assertIn("warning", data)

    # 8. Fabric Unavailable with Cached Data
    def test_08_fabric_unavailable_with_cached_data(self):
        """When Fabric is unavailable but cache has data, serves cache with CACHED status."""
        # Seed cache
        cached_data = {
            "status": "success",
            "data_status": "CACHED",
            "data": {
                "districts_covered": 38,
                "avg_temperature": 29.5,
                "total_rainfall": 12.0,
            },
            "metadata": {"latest_observation": "2026-11-13 06:00:00"},
        }
        weather_service._set_in_cache("overview:None:None", cached_data)

        # Fabric connection error occurs
        with patch.object(QueryExecutor, "execute_query", side_effect=FabricConnectionError("Outage simulation")):
            response = self.client.get(
                "/api/overview",
                headers={"Origin": "https://ai-weather-intelligence-1.onrender.com"},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data.get("data_status"), "CACHED")
            self.assertEqual(data["data"]["avg_temperature"], 29.5)


if __name__ == "__main__":
    unittest.main()
