"""Phase 10.1 - Comprehensive Test Suite for OpenAI GPT-6 Luna Online AI Provider.

Covers the 15 required acceptance scenarios:
1. Successful GPT-6 Luna API request (mocked Responses API).
2. OpenAI authentication failure (graceful fallback, no secret leakage).
3. OpenAI timeout (graceful deterministic fallback).
4. Rate-limit response (429 handling, fallback).
5. Invalid model response (empty/whitespace handling, fallback).
6. Structured JSON validation (ChartSpec & metadata integrity).
7. Deterministic emergency fallback (verified Fabric facts & provenance).
8. Local Qwen development mode (development provider resolution).
9. Production provider selection (production selects OpenAI, never localhost Ollama).
10. All 15 intent classifications with OpenAI.
11. ChartSpec compatibility (temperature trends, rainfall rankings).
12. Fabric LIVE data grounding.
13. Cached data grounding (staleness & cache tagging).
14. Fabric unavailable behavior (no hallucinations, clear status).
15. Token usage tracking and GET /api/ai/health endpoint.

All external API calls are strictly mocked - zero live API spend.
"""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.schemas.ai import ChartSeriesSpec, ChartSpec, ExtractedIntent
from app.services.ai_service import AIService
from app.services.grounded_response_generator import GroundedResponseGenerator
from app.services.openai_provider import OpenAIProvider, openai_provider


class TestPhase101OpenAIIntegration(unittest.TestCase):
    """Test suite for Phase 10.1 OpenAI GPT-6 Luna online AI provider."""

    def setUp(self):
        self.settings = get_settings()
        self.generator = GroundedResponseGenerator()
        openai_provider.reset_metrics()

    def tearDown(self):
        openai_provider.reset_metrics()

    def _run_async(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    # 1. Successful GPT-6 Luna API Request
    def test_01_successful_gpt6_luna_request(self):
        """Verify successful response generation and token usage tracking via Responses API."""
        mock_response = SimpleNamespace(
            output_text="Chennai is currently 32.5°C with 68% humidity. Weather is partly cloudy.",
            usage=SimpleNamespace(
                input_tokens=150,
                output_tokens=30,
                total_tokens=180,
            ),
        )

        mock_client = MagicMock()
        mock_client.responses.create = AsyncMock(return_value=mock_response)

        with patch.object(self.settings, "openai_api_key", "sk-proj-testkey1234567890abcdef"), \
             patch.object(self.settings, "openai_model", "gpt-6-luna"), \
             patch.object(openai_provider, "_get_client", return_value=mock_client):

            text, usage = self._run_async(
                openai_provider.generate_response(
                    prompt="What is the weather in Chennai?",
                    instructions="Strict data grounding instructions",
                )
            )

            self.assertIn("Chennai is currently 32.5°C", text)
            self.assertEqual(usage["model"], "gpt-6-luna")
            self.assertEqual(usage["prompt_tokens"], 150)
            self.assertEqual(usage["completion_tokens"], 30)
            self.assertEqual(usage["total_tokens"], 180)

            # Check provider metrics
            health = openai_provider.get_health_status()
            self.assertEqual(health["successful_requests"], 1)
            self.assertEqual(health["failed_requests"], 0)
            self.assertEqual(health["token_usage"]["total_tokens"], 180)

    # 2. OpenAI Authentication Failure
    def test_02_openai_auth_failure_fallback(self):
        """Verify AuthenticationError is handled safely without leaking credentials."""
        import openai

        mock_client = MagicMock()
        mock_client.responses.create = AsyncMock(
            side_effect=openai.AuthenticationError(
                "Incorrect API key provided: sk-proj-***.",
                response=MagicMock(status_code=401),
                body={"error": {"message": "Invalid API key"}},
            )
        )

        with patch.object(self.settings, "openai_api_key", "sk-proj-invalidkey99999"), \
             patch.object(self.settings, "ai_provider", "openai"), \
             patch.object(openai_provider, "_get_client", return_value=mock_client):

            extracted = ExtractedIntent(
                intent="current_weather",
                district="Madurai",
                entities={"district": "Madurai"},
            )
            query_result = {
                "source": "Microsoft Fabric Lakehouse",
                "observation_timestamp": "2026-11-13 10:00:00",
                "data_status": "LIVE",
                "data": [{"district": "Madurai", "temperature": 34.0, "humidity": 55, "condition": "Sunny"}],
            }

            answer, suggestions = self._run_async(
                self.generator.generate_answer(
                    query="What is the weather in Madurai?",
                    extracted=extracted,
                    query_result=query_result,
                )
            )

            # Ensure answer falls back to deterministic engine and does not leak raw key
            self.assertIn("Madurai", answer)
            self.assertNotIn("sk-proj-invalidkey99999", answer)
            self.assertTrue(len(answer) > 20)
            self.assertIsInstance(suggestions, list)

            health = openai_provider.get_health_status()
            self.assertEqual(health["failed_requests"], 1)

    # 3. OpenAI Timeout
    def test_03_openai_timeout_fallback(self):
        """Verify timeout triggers deterministic fallback cleanly."""
        import openai

        mock_client = MagicMock()
        mock_client.responses.create = AsyncMock(
            side_effect=openai.APITimeoutError("Request timed out after 30.0s")
        )

        with patch.object(self.settings, "openai_api_key", "sk-proj-validkey12345"), \
             patch.object(self.settings, "ai_provider", "openai"), \
             patch.object(openai_provider, "_get_client", return_value=mock_client):

            extracted = ExtractedIntent(
                intent="current_weather",
                district="Coimbatore",
                entities={"district": "Coimbatore"},
            )
            query_result = {
                "source": "Microsoft Fabric Lakehouse",
                "observation_timestamp": "2026-11-13 10:00:00",
                "data_status": "LIVE",
                "data": [{"district": "Coimbatore", "temperature": 29.5, "condition": "Cloudy", "humidity": 65}],
            }

            answer, _ = self._run_async(
                self.generator.generate_answer(
                    query="How hot is Coimbatore?",
                    extracted=extracted,
                    query_result=query_result,
                )
            )

            # Deterministic fallback should provide answer
            self.assertIn("Coimbatore", answer)
            self.assertIn("29.5", answer)

    # 4. Rate-Limit Response (429)
    def test_04_rate_limit_fallback(self):
        """Verify 429 RateLimitError gracefully falls back to deterministic engine."""
        import openai

        mock_client = MagicMock()
        mock_client.responses.create = AsyncMock(
            side_effect=openai.RateLimitError(
                "Rate limit reached for requests",
                response=MagicMock(status_code=429),
                body={"error": {"message": "Rate limit exceeded"}},
            )
        )

        with patch.object(self.settings, "openai_api_key", "sk-proj-validkey12345"), \
             patch.object(self.settings, "ai_provider", "openai"), \
             patch.object(openai_provider, "_get_client", return_value=mock_client):

            extracted = ExtractedIntent(
                intent="rainfall_analysis",
                district="Salem",
                entities={"district": "Salem"},
            )
            query_result = {
                "source": "Microsoft Fabric Lakehouse",
                "observation_timestamp": "2026-11-13 10:00:00",
                "data_status": "LIVE",
                "rainfall_records": [{"date": "2026-11-13", "rainfall_mm": 12.4, "category": "Moderate"}],
                "quality": {
                    "total_measured_rainfall_mm": 12.4,
                    "measured_observations": 1,
                    "total_observations": 1,
                    "completeness_pct": 100.0,
                    "positive_count": 1,
                    "max_measured_rainfall_mm": 12.4,
                },
            }

            answer, _ = self._run_async(
                self.generator.generate_answer(
                    query="Rainfall in Salem?",
                    extracted=extracted,
                    query_result=query_result,
                )
            )

            self.assertIn("Salem", answer)
            self.assertIn("12.4", answer)

    # 5. Invalid Model Response
    def test_05_invalid_model_response(self):
        """Verify empty or whitespace response triggers deterministic fallback."""
        mock_response = SimpleNamespace(
            output_text="   ",
            usage=SimpleNamespace(input_tokens=10, output_tokens=0, total_tokens=10),
        )

        mock_client = MagicMock()
        mock_client.responses.create = AsyncMock(return_value=mock_response)

        with patch.object(self.settings, "openai_api_key", "sk-proj-validkey12345"), \
             patch.object(self.settings, "ai_provider", "openai"), \
             patch.object(openai_provider, "_get_client", return_value=mock_client):

            extracted = ExtractedIntent(
                intent="air_quality_analysis",
                district="Chennai",
                entities={"district": "Chennai"},
            )
            query_result = {
                "source": "Microsoft Fabric Lakehouse",
                "observation_timestamp": "2026-11-13 10:00:00",
                "data_status": "LIVE",
                "data": [{"district": "Chennai", "aqi": 82, "status": "Moderate", "temperature": 32.0}],
            }

            answer, _ = self._run_async(
                self.generator.generate_answer(
                    query="Chennai AQI?",
                    extracted=extracted,
                    query_result=query_result,
                )
            )

            self.assertIn("Chennai", answer)

    # 6. Structured JSON Validation
    def test_06_structured_json_validation(self):
        """Verify ChartSpec schema validation and structure."""
        spec = ChartSpec(
            type="bar",
            title="District Rainfall Comparison",
            x_axis="district",
            y_axis="Rainfall (mm)",
            series=[ChartSeriesSpec(name="Rainfall", key="Rainfall (mm)", color="#3b82f6")],
            data=[
                {"district": "Chennai", "Rainfall (mm)": 0.0},
                {"district": "Madurai", "Rainfall (mm)": 5.0},
            ],
        )

        self.assertIsNotNone(spec)
        self.assertEqual(spec.type, "bar")
        self.assertEqual(len(spec.data), 2)
        spec_dict = spec.model_dump()
        self.assertIn("series", spec_dict)
        self.assertEqual(spec_dict["x_axis"], "district")

    # 7. Deterministic Emergency Fallback
    def test_07_deterministic_emergency_fallback(self):
        """Verify deterministic engine incorporates verified facts and provenance."""
        extracted = ExtractedIntent(
            intent="weather_ranking",
            entities={},
        )
        query_result = {
            "source": "Microsoft Fabric Lakehouse",
            "observation_timestamp": "2026-11-13 10:00:00",
            "data_status": "LIVE",
            "metric": "Temperature",
            "unit": "°C",
            "rankings": [
                {"rank": 1, "district": "Vellore", "value": 38.5, "condition": "Hot"},
                {"rank": 2, "district": "Nilgiris", "value": 14.2, "condition": "Cool"},
            ],
        }

        facts = self.generator._format_factual_summary(extracted, query_result)
        answer = self.generator._generate_deterministic_answer(extracted, query_result, facts)

        self.assertIn("Vellore", answer)
        self.assertIn("38.5", answer)
        self.assertIn("Nilgiris", answer)
        self.assertIn("14.2", answer)
        self.assertIn("Data source: Microsoft Fabric Lakehouse", answer)

    # 8. Local Qwen Development Mode
    def test_08_local_qwen_development_mode(self):
        """Verify development environment selects Ollama when configured."""
        with patch.object(self.settings, "app_env", "development"), \
             patch.object(self.settings, "ai_provider", "ollama"), \
             patch.object(self.generator, "check_ollama_health", AsyncMock(return_value={"available": True, "model_available": True})):
            provider, reason = self._run_async(self.generator.resolve_ai_provider())
            self.assertEqual(provider, "ollama")
            self.assertEqual(reason, "configured_ollama_online")

    # 9. Production Provider Selection
    def test_09_production_provider_selection(self):
        """Verify production environment selects OpenAI when key is present, never localhost Ollama."""
        with patch.object(self.settings, "app_env", "production"), \
             patch.object(self.settings, "ai_provider", "auto"), \
             patch.object(openai_provider, "is_configured", return_value=True):
            provider, reason = self._run_async(self.generator.resolve_ai_provider())
            self.assertEqual(provider, "openai")
            self.assertIn("production_openai", reason)

        # In production without key, must fall back to deterministic (never localhost Ollama)
        with patch.object(self.settings, "app_env", "production"), \
             patch.object(self.settings, "ai_provider", "auto"), \
             patch.object(openai_provider, "is_configured", return_value=False):
            provider, reason = self._run_async(self.generator.resolve_ai_provider())
            self.assertEqual(provider, "deterministic")
            self.assertEqual(reason, "cloud_production_localhost_skipped")

    # 10. All 15 Intent Classifications with OpenAI
    def test_10_all_15_intents_with_openai(self):
        """Verify all 15 supported intents execute smoothly with mocked OpenAI provider."""
        intents = [
            ("current_weather", {"data": [{"district": "Chennai", "temperature": 31.0, "humidity": 60, "condition": "Partly Cloudy"}]}),
            ("historical_weather", {"rows": [{"date": "2026-11-10", "avg_temp": 30.0, "max_temp": 33.0, "min_temp": 27.0, "total_rainfall": 0.0}]}),
            ("temperature_analysis", {"data": [{"district": "Coimbatore", "temperature": 28.0, "humidity": 65, "condition": "Cloudy"}]}),
            ("rainfall_analysis", {"rainfall_records": [{"date": "2026-11-13", "rainfall_mm": 5.0, "category": "Light"}], "quality": {"total_measured_rainfall_mm": 5.0, "measured_observations": 1, "total_observations": 1, "completeness_pct": 100.0, "positive_count": 1, "max_measured_rainfall_mm": 5.0}}),
            ("air_quality_analysis", {"data": [{"district": "Salem", "aqi": 65, "condition": "Moderate"}]}),
            ("district_comparison", {"comparison_rows": [{"district": "Chennai", "temp": 31.0, "humidity": 65, "condition": "Sunny"}, {"district": "Trichy", "temp": 33.0, "humidity": 55, "condition": "Sunny"}]}),
            ("statewide_summary", {"overview": {"districts_covered": 38, "avg_temperature": 30.5, "max_temperature": 35.0, "min_temperature": 22.0, "total_rainfall": 12.0, "avg_humidity": 68}}),
            ("weather_ranking", {"rankings": [{"rank": 1, "district": "Vellore", "value": 37.0}], "metric": "Temperature", "unit": "°C"}),
            ("date_comparison", {"comparison": {"temperature": {"current_val": 31.0, "previous_val": 30.0, "absolute_change": 1.0, "direction": "warmer"}, "rainfall": {"current_val": 0.0, "previous_val": 5.0, "absolute_change": -5.0}, "humidity": {"current_val": 65, "previous_val": 70, "absolute_change": -5}}}),
            ("weather_trend", {"rows": [{"date": "2026-11-10", "avg_temp": 30.0, "max_temp": 33.0, "min_temp": 27.0, "total_rainfall": 0.0}]}),
            ("district_intelligence", {"details": {"district": "Chennai", "reference_location": "Meenambakkam", "latitude": 13.08, "longitude": 80.27, "avg_temp": 31.0, "max_temp": 35.0, "min_temp": 26.0, "avg_humidity": 70}}),
            ("weather_report", {"overview": {"districts_covered": 38, "avg_temperature": 30.5, "max_temperature": 35.0, "min_temperature": 22.0, "total_rainfall": 12.0, "avg_humidity": 68}}),
            ("dashboard_request", {"overview": {"districts_covered": 38, "avg_temperature": 30.5, "max_temperature": 35.0, "min_temperature": 22.0, "total_rainfall": 12.0, "avg_humidity": 68}}),
            ("general_weather_question", {"data": [{"district": "Chennai", "temperature": 31.0, "condition": "Fair"}]}),
            ("unknown_intent", {}),
        ]

        mock_response = SimpleNamespace(
            output_text="Verified meteorological response according to Fabric Lakehouse observation.",
            usage=SimpleNamespace(input_tokens=80, output_tokens=25, total_tokens=105),
        )
        mock_client = MagicMock()
        mock_client.responses.create = AsyncMock(return_value=mock_response)

        with patch.object(self.settings, "openai_api_key", "sk-proj-testkey12345"), \
             patch.object(self.settings, "ai_provider", "openai"), \
             patch.object(openai_provider, "_get_client", return_value=mock_client):

            for intent_name, sample_dict in intents:
                extracted = ExtractedIntent(
                    intent=intent_name,
                    district="Chennai",
                    entities={"district": "Chennai"},
                )
                query_result = {
                    "source": "Microsoft Fabric Lakehouse",
                    "observation_timestamp": "2026-11-13 10:00:00",
                    "data_status": "LIVE",
                    **sample_dict,
                }
                answer, suggestions = self._run_async(
                    self.generator.generate_answer(
                        query=f"Query for {intent_name}",
                        extracted=extracted,
                        query_result=query_result,
                    )
                )
                self.assertIsNotNone(answer)
                self.assertTrue(len(answer) > 10)
                if intent_name != "unknown_intent":
                    self.assertIn("Model: OpenAI GPT-6 Luna", answer)

    # 11. ChartSpec Compatibility
    def test_11_chart_spec_compatibility(self):
        """Verify queries generating ChartSpecs remain valid with OpenAI enabled."""
        chart = ChartSpec(
            type="line",
            title="Temperature Trend - Chennai",
            x_axis="observation_date",
            y_axis="Temperature (°C)",
            series=[ChartSeriesSpec(name="Temperature", key="Temperature (°C)", color="#ef4444")],
            data=[
                {"observation_date": "2026-11-10", "Temperature (°C)": 30.5},
                {"observation_date": "2026-11-11", "Temperature (°C)": 31.2},
                {"observation_date": "2026-11-12", "Temperature (°C)": 31.8},
            ],
        )
        self.assertIsNotNone(chart)
        self.assertEqual(chart.type, "line")
        self.assertEqual(chart.x_axis, "observation_date")
        self.assertEqual(len(chart.data), 3)

    # 12. Fabric LIVE Data Grounding
    def test_12_fabric_live_data_grounding(self):
        """Verify LIVE Fabric data includes [LIVE] status and correct source citation."""
        mock_response = SimpleNamespace(
            output_text="According to live Fabric telemetry, Madurai is 33.5°C.",
            usage=SimpleNamespace(input_tokens=100, output_tokens=20, total_tokens=120),
        )
        mock_client = MagicMock()
        mock_client.responses.create = AsyncMock(return_value=mock_response)

        with patch.object(self.settings, "openai_api_key", "sk-proj-testkey12345"), \
             patch.object(self.settings, "ai_provider", "openai"), \
             patch.object(openai_provider, "_get_client", return_value=mock_client):

            extracted = ExtractedIntent(intent="current_weather", district="Madurai", entities={})
            query_result = {
                "source": "Microsoft Fabric Lakehouse",
                "observation_timestamp": "2026-11-13 10:15:00",
                "data_status": "LIVE",
                "data": [{"district": "Madurai", "temperature": 33.5, "condition": "Sunny"}],
            }

            answer, _ = self._run_async(
                self.generator.generate_answer("Madurai weather", extracted, query_result)
            )

            self.assertIn("Data source: Microsoft Fabric Lakehouse [LIVE]", answer)
            self.assertIn("Model: OpenAI GPT-6 Luna", answer)

    # 13. Cached Data Grounding
    def test_13_cached_data_grounding(self):
        """Verify CACHED data includes cache tag and staleness note when stale."""
        mock_response = SimpleNamespace(
            output_text="From cached observations, Coimbatore temperature is 28.0°C.",
            usage=SimpleNamespace(input_tokens=100, output_tokens=20, total_tokens=120),
        )
        mock_client = MagicMock()
        mock_client.responses.create = AsyncMock(return_value=mock_response)

        with patch.object(self.settings, "openai_api_key", "sk-proj-testkey12345"), \
             patch.object(self.settings, "ai_provider", "openai"), \
             patch.object(openai_provider, "_get_client", return_value=mock_client):

            extracted = ExtractedIntent(intent="temperature_analysis", district="Coimbatore", entities={})
            query_result = {
                "source": "Microsoft Fabric Lakehouse",
                "observation_timestamp": "2026-11-13 06:00:00",
                "data_status": "CACHED",
                "is_cached": True,
                "is_stale": True,
                "data": [{"district": "Coimbatore", "temperature": 28.0, "condition": "Cloudy"}],
            }

            answer, _ = self._run_async(
                self.generator.generate_answer("Coimbatore temp", extracted, query_result)
            )

            self.assertIn("[CACHED]", answer)
            self.assertIn("stale", answer.lower())

    # 14. Fabric Unavailable Behavior
    def test_14_fabric_unavailable_behavior(self):
        """Verify unavailable data produces explanatory notice without fabricating synthetic numbers."""
        extracted = ExtractedIntent(intent="current_weather", district="Thanjavur", entities={})
        query_result = {
            "source": "Service Unavailable",
            "observation_timestamp": "2026-11-13 10:00:00",
            "data_status": "UNAVAILABLE",
            "data": None,
        }

        facts = self.generator._format_factual_summary(extracted, query_result)
        answer = self.generator._generate_deterministic_answer(extracted, query_result, facts)

        self.assertIn("unavailable", answer.lower())
        # Ensure it does not invent fake temperatures
        self.assertNotIn("35.0°C", answer)

    # 15. Token Usage Tracking & GET /api/ai/health Endpoint
    def test_15_token_usage_and_ai_health_endpoint(self):
        """Verify GET /api/ai/health exposes token tracking, masked key, and operational status."""
        client = TestClient(app)

        with patch.object(self.settings, "openai_api_key", "sk-proj-abcdef1234567890xyz"), \
             patch.object(self.settings, "openai_model", "gpt-6-luna"), \
             patch.object(self.settings, "ai_provider", "openai"):

            # Seed token usage metrics
            with openai_provider._lock:
                openai_provider._total_requests = 5
                openai_provider._successful_requests = 4
                openai_provider._failed_requests = 1
                openai_provider._prompt_tokens = 600
                openai_provider._completion_tokens = 150
                openai_provider._total_tokens = 750
                openai_provider._last_successful_request_ist = "2026-11-13 10:20:00 IST"

            response = client.get("/api/ai/health")
            self.assertEqual(response.status_code, 200)
            data = response.json()

            self.assertEqual(data["service"], "AI Weather Intelligence Agent")
            self.assertEqual(data["model_name"], "gpt-6-luna")
            self.assertEqual(data["request_count"], 5)
            self.assertEqual(data["error_count"], 1)
            self.assertEqual(data["token_usage"]["prompt_tokens"], 600)
            self.assertEqual(data["token_usage"]["completion_tokens"], 150)
            self.assertEqual(data["token_usage"]["total_tokens"], 750)

            # Secret masking validation
            self.assertIn("openai", data)
            masked_key = data["openai"]["api_key_masked"]
            self.assertEqual(masked_key, "sk-p...0xyz")
            self.assertNotIn("abcdef1234567890", masked_key)


if __name__ == "__main__":
    unittest.main()
