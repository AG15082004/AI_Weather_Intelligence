"""Phase 8.1 API Connectivity and Schema Validation Test Suite."""

import unittest
from fastapi.testclient import TestClient

from app.main import app


class TestPhase81Connectivity(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.origin = "https://ai-weather-intelligence-1.onrender.com"

    def test_01_backend_root_endpoint(self):
        """1. Backend root endpoint / returns 200 with service metadata."""
        res = self.client.get("/", headers={"Origin": self.origin})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("service"), "TN Weather Intelligence API")
        self.assertEqual(data.get("status"), "healthy")
        self.assertIn("docs", data)
        self.assertIn("health", data)
        self.assertEqual(res.headers.get("access-control-allow-origin"), self.origin)

    def test_02_swagger_documentation(self):
        """2. Swagger documentation /docs and OpenAPI schema /openapi.json."""
        res_docs = self.client.get("/docs", headers={"Origin": self.origin})
        self.assertEqual(res_docs.status_code, 200)

        res_openapi = self.client.get("/openapi.json", headers={"Origin": self.origin})
        self.assertEqual(res_openapi.status_code, 200)
        schema = res_openapi.json()
        self.assertEqual(schema.get("info", {}).get("title"), "TN Weather Intelligence API")
        paths = schema.get("paths", {})
        self.assertTrue(any(p.startswith("/api/overview") for p in paths))
        self.assertTrue(any(p.startswith("/api/ai/chat") for p in paths))

    def test_03_health_endpoint(self):
        """3. Health endpoint /api/health."""
        res = self.client.get("/api/health", headers={"Origin": self.origin})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "healthy")

    def test_04_overview_api(self):
        """4. Overview API /api/overview."""
        res = self.client.get("/api/overview", headers={"Origin": self.origin})
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertEqual(payload.get("status"), "success")
        data = payload.get("data", {})
        self.assertIn("districts_covered", data)
        self.assertEqual(data.get("districts_covered"), 38)
        self.assertIn("avg_temperature", data)
        self.assertIn("temperature_trend", data)
        self.assertIn("rainfall_trend", data)

    def test_05_temperature_api(self):
        """5. Temperature API /api/temperature."""
        res = self.client.get("/api/temperature", headers={"Origin": self.origin})
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertEqual(payload.get("status"), "success")
        self.assertTrue(len(payload.get("data", [])) > 0)

    def test_06_rainfall_api(self):
        """6. Rainfall API /api/rainfall."""
        res = self.client.get("/api/rainfall", headers={"Origin": self.origin})
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertEqual(payload.get("status"), "success")
        self.assertTrue(len(payload.get("data", [])) > 0)
        self.assertIn("metadata", payload)

    def test_07_district_api(self):
        """7. District API /api/districts and single district lookup."""
        res = self.client.get("/api/districts", headers={"Origin": self.origin})
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertEqual(payload.get("status"), "success")
        districts = payload.get("data", [])
        self.assertEqual(len(districts), 38)

        res_single = self.client.get("/api/districts/Chennai", headers={"Origin": self.origin})
        self.assertEqual(res_single.status_code, 200)
        single_payload = res_single.json()
        raw_data = single_payload.get("data")
        chennai = raw_data[0] if isinstance(raw_data, list) else raw_data
        self.assertEqual(chennai.get("district"), "Chennai")

    def test_08_current_weather_api(self):
        """8. Current weather API /api/current-weather."""
        res = self.client.get("/api/current-weather", headers={"Origin": self.origin})
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertEqual(payload.get("status"), "success")
        districts = payload.get("data", [])
        self.assertEqual(len(districts), 38)

    def test_09_air_quality_api(self):
        """9. Air quality API /api/air-quality."""
        res = self.client.get("/api/air-quality", headers={"Origin": self.origin})
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertEqual(payload.get("status"), "success")
        districts = payload.get("data", [])
        self.assertEqual(len(districts), 38)

    def test_10_ai_chat_api(self):
        """10. AI Chat API /api/ai/chat."""
        payload = {"query": "What is the weather in Madurai?"}
        res = self.client.post("/api/ai/chat", json=payload, headers={"Origin": self.origin})
        self.assertEqual(res.status_code, 200)
        chat_data = res.json()
        self.assertIn("response", chat_data)
        self.assertIn("intent", chat_data)
        self.assertIn("sources", chat_data)
        self.assertEqual(res.headers.get("access-control-allow-origin"), self.origin)


if __name__ == "__main__":
    unittest.main()
