"""Test CORS and OPTIONS preflight requests for Render and local development."""

import unittest
from fastapi.testclient import TestClient

from app.main import app


class TestCorsAndPreflight(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_preflight_production_frontend_origin(self):
        """Exact production frontend: https://ai-weather-intelligence-1.onrender.com"""
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

    def test_preflight_localhost_origin(self):
        """Local development: http://localhost:5173"""
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
        self.assertIn("GET", response.headers.get("access-control-allow-methods", ""))

    def test_preflight_render_backend_origin(self):
        """Production backend origin: https://ai-weather-intelligence.onrender.com"""
        response = self.client.options(
            "/api/ai/chat",
            headers={
                "Origin": "https://ai-weather-intelligence.onrender.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "https://ai-weather-intelligence.onrender.com",
        )
        self.assertIn("POST", response.headers.get("access-control-allow-methods", ""))

    def test_preflight_regex_render_subdomain(self):
        """Matches CORS_ORIGIN_REGEX https://ai-weather-intelligence-2.onrender.com"""
        response = self.client.options(
            "/api/temperature",
            headers={
                "Origin": "https://ai-weather-intelligence-2.onrender.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "https://ai-weather-intelligence-2.onrender.com",
        )

    def test_unauthorized_origin_rejected(self):
        """Disallowed origin must NOT receive access-control-allow-origin."""
        response = self.client.options(
            "/api/overview",
            headers={
                "Origin": "https://malicious-weather-scraper.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        # Preflight from disallowed origin should not have allow-origin header
        self.assertIsNone(response.headers.get("access-control-allow-origin"))

    def test_direct_options_probe_without_cors(self):
        """Direct load balancer / proxy OPTIONS ping."""
        response = self.client.options("/")
        self.assertEqual(response.status_code, 200)

        response_api = self.client.options("/api/overview")
        self.assertEqual(response_api.status_code, 200)

    def test_get_request_cors_headers(self):
        """GET request from allowed origin returns proper CORS headers."""
        response = self.client.get(
            "/",
            headers={"Origin": "https://ai-weather-intelligence-1.onrender.com"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "https://ai-weather-intelligence-1.onrender.com",
        )
        # Verify credentials disabled as required by Phase 8.1
        self.assertIsNone(response.headers.get("access-control-allow-credentials"))


if __name__ == "__main__":
    unittest.main()
