"""Production Health Status Consistency Automated Tests.

Verifies:
1. When Fabric authentication is deferred (Render cloud without SP credentials, missing ODBC driver, etc.):
   - Fabric dependency status is reported as "deferred" across all health & monitoring endpoints.
   - components.fabric.status == "deferred" (eliminates contradictory "healthy").
   - data_reliability.fabric_connected == False.
   - Top-level API status remains "healthy" (API health is distinguished from dependency health).
2. When Fabric is configured but connection fails:
   - Fabric dependency status is reported as "unavailable".
   - components.fabric.status == "unavailable".
   - data_reliability.fabric_connected == False.
   - components.api.status == "healthy".
3. Only report Fabric as "healthy" after a successful SQL connectivity check:
   - Before successful check/query: Fabric status is NOT "healthy".
   - After successful SQL query / connectivity check (SELECT 1 or table query): Fabric status transitions to "healthy".
4. Distinguishes API health from Fabric dependency health:
   - Overall API health does not fail simply because Fabric dependency is deferred.
5. Backward compatibility and complete response structure preserved across:
   - /api/health
   - /api/monitoring/operational-status
   - /api/monitoring/metrics
"""

import sys
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

sys.path.insert(0, ".")

from app.config import Settings
from app.main import app
from app.services.data_reliability_service import data_reliability_service, DataSourceStatus
from app.services.metrics_service import metrics_service
from app.services.fabric_connection import FabricConnectionService


class TestProductionHealthStatusConsistency(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        metrics_service.reset()
        data_reliability_service.reset()

    def tearDown(self):
        metrics_service.reset()
        data_reliability_service.reset()

    # =========================================================================
    # 1. Deferred Fabric State Tests
    # =========================================================================
    def test_01_deferred_fabric_state_reported_as_deferred(self):
        """Requirement 1 & 5: Deferred Fabric reports 'deferred' and overall API remains 'healthy'."""
        # Simulate Render environment with no SP credentials
        render_settings = Settings(
            app_env="production",
            fabric_server="test-fabric.datawarehouse.fabric.microsoft.com",
            fabric_database="lh_tn_weather_intelligence",
            fabric_auth_mode="azure_cli",
            fabric_client_id="",
            fabric_client_secret="",
            cors_origins="https://ai-weather-intelligence-1.onrender.com",
        )

        with patch("app.config.get_settings", return_value=render_settings), \
             patch.dict("os.environ", {"RENDER": "true"}):

            # Verify metrics service directly
            fabric_status = metrics_service.get_fabric_status()
            self.assertEqual(fabric_status, "deferred", "Metrics service must report 'deferred' when SP credentials absent on Render")

            # Verify /api/health endpoint
            resp = self.client.get("/api/health")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()

            # Top-level API status must be healthy (Requirement 5: do not mark unhealthy merely because deferred)
            self.assertEqual(data["status"], "healthy", "Overall API must remain 'healthy' when Fabric is deferred")

            # Component breakdown
            components = data.get("components", {})
            self.assertEqual(components["api"]["status"], "healthy", "API component status must be 'healthy'")
            self.assertEqual(components["fabric"]["status"], "deferred", "Fabric component status must be 'deferred', NOT 'healthy'")

            # Data reliability status
            dr = components.get("data_reliability", {})
            self.assertFalse(dr["fabric_connected"], "data_reliability.fabric_connected must be False")
            self.assertIn(dr["overall_status"], ["unavailable", "degraded"])

            # Verify /api/monitoring/operational-status endpoint
            op_resp = self.client.get("/api/monitoring/operational-status")
            self.assertEqual(op_resp.status_code, 200)
            op_data = op_resp.json()
            self.assertEqual(op_data["fabric"]["status"], "deferred")
            self.assertEqual(op_data["api"]["status"], "healthy")
            self.assertFalse(op_data["data_reliability"]["fabric_connected"])

    def test_02_deferred_due_to_missing_server(self):
        """When FABRIC_SERVER is empty, status is 'deferred'."""
        no_server_settings = Settings(
            fabric_server="",
            fabric_database="lh_tn_weather_intelligence",
        )
        with patch("app.config.get_settings", return_value=no_server_settings):
            fabric_status = metrics_service.get_fabric_status()
            self.assertEqual(fabric_status, "deferred")

            resp = self.client.get("/api/health")
            self.assertEqual(resp.json()["components"]["fabric"]["status"], "deferred")

    def test_03_deferred_due_to_missing_odbc_driver(self):
        """When ODBC Driver 18 is not installed on host, status is 'deferred'."""
        with patch.object(FabricConnectionService, "is_driver_available", return_value=False):
            fabric_status = metrics_service.get_fabric_status()
            self.assertEqual(fabric_status, "deferred")

            resp = self.client.get("/api/health")
            self.assertEqual(resp.json()["components"]["fabric"]["status"], "deferred")

    # =========================================================================
    # 2. Unavailable Fabric State Tests
    # =========================================================================
    def test_04_unavailable_fabric_state_when_connection_fails(self):
        """Requirement 2: Configured Fabric reports 'unavailable' when connection fails."""
        # Configure Fabric (e.g. azure_cli local mode)
        configured_settings = Settings(
            app_env="development",
            fabric_server="test-fabric.datawarehouse.fabric.microsoft.com",
            fabric_database="lh_tn_weather_intelligence",
            fabric_auth_mode="azure_cli",
        )

        with patch("app.config.get_settings", return_value=configured_settings), \
             patch.object(FabricConnectionService, "is_driver_available", return_value=True):

            # Simulate consecutive failures
            metrics_service.fabric_consecutive_failures = 3
            metrics_service.fabric_failed_queries = 3

            fabric_status = metrics_service.get_fabric_status()
            self.assertEqual(fabric_status, "unavailable", "Configured Fabric with failures must report 'unavailable'")

            resp = self.client.get("/api/health")
            data = resp.json()
            self.assertEqual(data["components"]["fabric"]["status"], "unavailable")
            self.assertEqual(data["components"]["api"]["status"], "healthy", "API component remains healthy")

            op_resp = self.client.get("/api/monitoring/operational-status")
            self.assertEqual(op_resp.json()["fabric"]["status"], "unavailable")

    def test_05_configured_but_no_sql_check_yet_reports_unavailable(self):
        """Requirement 3: Only report Fabric as 'healthy' AFTER a successful SQL connectivity check."""
        configured_settings = Settings(
            app_env="development",
            fabric_server="test-fabric.datawarehouse.fabric.microsoft.com",
            fabric_database="lh_tn_weather_intelligence",
            fabric_auth_mode="azure_cli",
        )

        with patch("app.config.get_settings", return_value=configured_settings), \
             patch.object(FabricConnectionService, "is_driver_available", return_value=True):

            # 0 queries executed, no check passed yet
            metrics_service.fabric_total_queries = 0
            metrics_service.fabric_successful_queries = 0
            metrics_service.fabric_verified_connected = False

            # MUST NOT report healthy!
            fabric_status = metrics_service.get_fabric_status()
            self.assertNotEqual(fabric_status, "healthy", "Fabric must NEVER report 'healthy' before a successful SQL check")
            self.assertEqual(fabric_status, "unavailable")

    # =========================================================================
    # 3. Healthy Fabric State Tests (Only after successful SQL check)
    # =========================================================================
    def test_06_healthy_fabric_state_after_successful_sql_check(self):
        """Requirement 3: Only report Fabric as 'healthy' after a successful SQL connectivity check."""
        configured_settings = Settings(
            app_env="development",
            fabric_server="test-fabric.datawarehouse.fabric.microsoft.com",
            fabric_database="lh_tn_weather_intelligence",
            fabric_auth_mode="azure_cli",
        )

        with patch("app.config.get_settings", return_value=configured_settings), \
             patch.object(FabricConnectionService, "is_driver_available", return_value=True):

            # Record a successful query
            metrics_service.record_fabric_query(success=True, duration_ms=18.5)
            data_reliability_service.record_connectivity_check(True)

            fabric_status = metrics_service.get_fabric_status()
            self.assertEqual(fabric_status, "healthy", "Fabric must report 'healthy' after successful SQL check")

            # Check /api/health
            resp = self.client.get("/api/health")
            data = resp.json()
            self.assertEqual(data["status"], "healthy")
            self.assertEqual(data["components"]["fabric"]["status"], "healthy")
            self.assertEqual(data["components"]["api"]["status"], "healthy")
            self.assertTrue(data["components"]["data_reliability"]["fabric_connected"])

            # Check /api/monitoring/operational-status
            op_resp = self.client.get("/api/monitoring/operational-status")
            op_data = op_resp.json()
            self.assertEqual(op_data["fabric"]["status"], "healthy")
            self.assertTrue(op_data["data_reliability"]["fabric_connected"])

    # =========================================================================
    # 4. Consistency & Contradiction Elimination Tests
    # =========================================================================
    def test_07_no_contradiction_between_components_and_data_reliability(self):
        """Verify that components.fabric.status cannot be 'healthy' when fabric_connected is False."""
        # 1. Deferred mode
        with patch.object(metrics_service, "get_fabric_status", return_value="deferred"):
            resp = self.client.get("/api/health")
            data = resp.json()
            fabric_status = data["components"]["fabric"]["status"]
            fabric_connected = data["components"]["data_reliability"]["fabric_connected"]

            self.assertEqual(fabric_status, "deferred")
            self.assertFalse(fabric_connected)
            # Not contradictory: deferred status matches fabric_connected=False

        # 2. Unavailable mode
        with patch.object(metrics_service, "get_fabric_status", return_value="unavailable"):
            resp = self.client.get("/api/health")
            data = resp.json()
            fabric_status = data["components"]["fabric"]["status"]
            fabric_connected = data["components"]["data_reliability"]["fabric_connected"]

            self.assertEqual(fabric_status, "unavailable")
            self.assertFalse(fabric_connected)
            # Not contradictory: unavailable status matches fabric_connected=False

    # =========================================================================
    # 5. Backward Compatibility & Response Schema Preservation
    # =========================================================================
    def test_08_backward_compatibility_preserved(self):
        """Requirement 6: Preserve all existing response fields and schema contracts."""
        # /api/health response schema
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        h = resp.json()

        # Top-level fields
        for field in ["status", "timestamp", "service", "version", "uptime_seconds", "components"]:
            self.assertIn(field, h, f"Missing required top-level field: {field}")

        # Components fields
        comp = h["components"]
        for field in ["api", "fabric", "ai", "data_freshness", "data_reliability"]:
            self.assertIn(field, comp, f"Missing required component: {field}")

        # fabric component fields
        for field in ["status", "total_queries", "last_query_timestamp", "avg_query_time_ms"]:
            self.assertIn(field, comp["fabric"], f"Missing fabric component field: {field}")

        # /api/monitoring/operational-status schema
        op_resp = self.client.get("/api/monitoring/operational-status")
        self.assertEqual(op_resp.status_code, 200)
        op = op_resp.json()

        for field in ["status", "service", "environment", "uptime_seconds", "api", "fabric", "ai", "cache", "data_freshness", "data_reliability"]:
            self.assertIn(field, op, f"Missing operational-status field: {field}")

        for field in ["status", "total_queries", "avg_latency_ms", "last_query_timestamp"]:
            self.assertIn(field, op["fabric"], f"Missing operational-status fabric field: {field}")

        # /api/monitoring/metrics schema
        met_resp = self.client.get("/api/monitoring/metrics")
        self.assertEqual(met_resp.status_code, 200)
        met = met_resp.json()

        for field in ["uptime_seconds", "timestamp_utc", "http_metrics", "fabric_metrics", "ai_metrics", "data_freshness"]:
            self.assertIn(field, met, f"Missing metrics field: {field}")

        for field in ["status", "total_queries", "successful_queries", "failed_queries", "consecutive_failures", "last_query_timestamp", "avg_duration_ms"]:
            self.assertIn(field, met["fabric_metrics"], f"Missing fabric_metrics field: {field}")


if __name__ == "__main__":
    unittest.main()
