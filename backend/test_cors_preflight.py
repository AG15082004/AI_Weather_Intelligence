"""Test CORS and OPTIONS preflight requests for Render and local development."""

import unittest
from fastapi.testclient import TestClient

from app.main import app


class TestCorsAndPreflight(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_preflight_localhost_origin(self):
        response = self.client.options(
            "/api/overview",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:5173")
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")
        self.assertIn("GET", response.headers.get("access-control-allow-methods", ""))

    def test_preflight_render_backend_origin(self):
        response = self.client.options(
            "/api/overview",
            headers={
                "Origin": "https://ai-weather-intelligence.onrender.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "https://ai-weather-intelligence.onrender.com",
        )
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")

    def test_preflight_render_frontend_subdomain_origin(self):
        # Matches CORS_ORIGIN_REGEX https://.*\.onrender\.com
        response = self.client.options(
            "/api/ai/chat",
            headers={
                "Origin": "https://ai-weather-intelligence-frontend.onrender.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "https://ai-weather-intelligence-frontend.onrender.com",
        )
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")
        self.assertIn("POST", response.headers.get("access-control-allow-methods", ""))

    def test_direct_options_probe_without_cors(self):
        response = self.client.options("/")
        self.assertEqual(response.status_code, 200)

        response_api = self.client.options("/api/overview")
        self.assertEqual(response_api.status_code, 200)

    def test_get_request_cors_headers(self):
        response = self.client.get(
            "/",
            headers={"Origin": "https://ai-weather-intelligence.onrender.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "https://ai-weather-intelligence.onrender.com",
        )
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")


if __name__ == "__main__":
    unittest.main()
