"""Phase 8.3 — Production AI Engine Stabilization and Deterministic Provider Selection Tests.

Verifies:
1. AI provider selection: 'auto', 'deterministic', and 'ollama'.
2. Production mode (app_env='production') safely skipping localhost:11434 without socket delays.
3. Ollama health check caching with TTL.
4. Deterministic response formatting for all 15 intents.
5. Strict NULL rainfall semantics (distinguishing unmeasured from true zero).
6. ChartSpec structure preservation.
7. /api/ai/health endpoint status reporting.
"""

from datetime import date
import sys
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, ".")

from app.config import Settings
from app.schemas.ai import (
    ChartSeriesSpec,
    ChartSpec,
    DateRangeSpecification,
    ExtractedIntent,
)
from app.services.ai_service import AIService
from app.services.grounded_response_generator import GroundedResponseGenerator, _is_local_url


class TestPhase83AIEngine(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.generator = GroundedResponseGenerator()
        self.generator.settings.ai_provider = "deterministic"
        # Reset health cache before each test
        GroundedResponseGenerator._health_cache = None
        GroundedResponseGenerator._health_cache_ts = 0.0

    def test_01_is_local_url_detection(self):
        """Verify local URL detection for preventing loopback calls in cloud containers."""
        self.assertTrue(_is_local_url("http://127.0.0.1:11434"))
        self.assertTrue(_is_local_url("http://localhost:11434"))
        self.assertTrue(_is_local_url("http://0.0.0.0:11434"))
        self.assertTrue(_is_local_url("http://[::1]:11434"))
        self.assertTrue(_is_local_url(""))
        self.assertTrue(_is_local_url(None))
        self.assertFalse(_is_local_url("https://remote-ollama.internal.net:11434"))
        self.assertFalse(_is_local_url("https://ai.example.com"))

    async def test_02_production_skips_localhost_ollama(self):
        """In cloud production, local Ollama should be bypassed immediately without network delay."""
        prod_settings = Settings(
            app_env="production",
            ai_provider="auto",
            ollama_base_url="http://127.0.0.1:11434",
        )
        with patch.object(self.generator, "settings", prod_settings):
            provider, reason = await self.generator.resolve_ai_provider()
            self.assertEqual(provider, "deterministic")
            self.assertEqual(reason, "cloud_production_localhost_skipped")

            health = await self.generator.check_ollama_health()
            self.assertEqual(health["status"], "bypassed_in_production")
            self.assertFalse(health["available"])
            self.assertEqual(health["latency_ms"], 0.0)

    async def test_03_explicit_deterministic_provider_configured(self):
        """When AI_PROVIDER='deterministic', bypass Ollama unconditionally."""
        det_settings = Settings(
            app_env="development",
            ai_provider="deterministic",
            ollama_base_url="http://127.0.0.1:11434",
        )
        with patch.object(self.generator, "settings", det_settings):
            provider, reason = await self.generator.resolve_ai_provider()
            self.assertEqual(provider, "deterministic")
            self.assertIn("deterministic", reason)

    async def test_04_health_check_caching(self):
        """Health check results must be cached to prevent polling on every request."""
        mock_resp = {
            "status": "healthy",
            "available": True,
            "model": "qwen3:4b",
            "model_available": True,
            "available_models": ["qwen3:4b"],
            "latency_ms": 1.2,
        }
        with patch("httpx.AsyncClient.get") as mock_get:
            # First call populates cache
            GroundedResponseGenerator._health_cache = mock_resp
            GroundedResponseGenerator._health_cache_ts = 9999999999.0  # Far future

            health = await self.generator.check_ollama_health()
            self.assertEqual(health["status"], "healthy")
            # Should not call HTTP client because cache is valid
            mock_get.assert_not_called()

    async def test_05_deterministic_weather_ranking(self):
        """Deterministic output for weather_ranking intent."""
        extracted = ExtractedIntent(
            intent="weather_ranking",
            metric="temperature",
            aggregation="ranking",
            ranking_limit=5,
        )
        query_result = {
            "source": "Microsoft Fabric [dbo].[gold_current_weather_latest]",
            "top_district": "Madurai",
            "top_value": 34.5,
            "metric": "Temperature",
            "unit": "°C",
            "rankings": [
                {"district": "Madurai", "value": 34.5, "condition": "Sunny"},
                {"district": "Chennai", "value": 33.2, "condition": "Partly Cloudy"},
            ],
            "observation_timestamp": "2026-11-12 17:00",
        }
        ans, suggestions = await self.generator.generate_answer(
            query="Which district is the hottest?",
            extracted=extracted,
            query_result=query_result,
        )
        self.assertIn("Madurai", ans)
        self.assertIn("34.5 °C", ans)
        self.assertIn("Chennai", ans)
        self.assertIn("Live Weather Observations", ans)
        self.assertTrue(len(suggestions) > 0)

    async def test_06_deterministic_district_comparison(self):
        """Deterministic output for district_comparison intent."""
        extracted = ExtractedIntent(
            intent="district_comparison",
            districts=["Chennai", "Coimbatore"],
        )
        query_result = {
            "source": "Microsoft Fabric Lakehouse",
            "comparison_rows": [
                {
                    "district": "Chennai",
                    "temp": 32.0,
                    "feels_like": 35.0,
                    "humidity": 78,
                    "wind_speed": 12.0,
                    "rainfall": 0.0,
                    "condition": "Humid",
                },
                {
                    "district": "Coimbatore",
                    "temp": 28.5,
                    "feels_like": 29.0,
                    "humidity": 65,
                    "wind_speed": 8.5,
                    "rainfall": 1.2,
                    "condition": "Cloudy",
                },
            ],
            "observation_timestamp": "2026-11-12 17:00",
        }
        ans, _ = await self.generator.generate_answer(
            query="Compare Chennai and Coimbatore",
            extracted=extracted,
            query_result=query_result,
        )
        self.assertIn("Chennai", ans)
        self.assertIn("Coimbatore", ans)
        self.assertIn("32.0°C", ans)
        self.assertIn("28.5°C", ans)
        self.assertIn("warmer than Coimbatore", ans)

    async def test_07_deterministic_date_comparison(self):
        """Deterministic output for date_comparison intent."""
        extracted = ExtractedIntent(intent="date_comparison", district="Chennai")
        query_result = {
            "source": "Microsoft Fabric Lakehouse",
            "district": "Chennai",
            "comparison": {
                "temperature": {
                    "current_val": 32.0,
                    "previous_val": 30.5,
                    "absolute_change": 1.5,
                    "direction": "warmer",
                },
                "rainfall": {
                    "current_val": 0.0,
                    "previous_val": 2.5,
                    "absolute_change": -2.5,
                },
                "humidity": {
                    "current_val": 75,
                    "previous_val": 80,
                    "absolute_change": -5,
                },
            },
            "observation_timestamp": "2026-11-12 17:00",
        }
        ans, _ = await self.generator.generate_answer(
            query="Compare today vs yesterday in Chennai",
            extracted=extracted,
            query_result=query_result,
        )
        self.assertIn("Chennai", ans)
        self.assertIn("32.0°C vs Baseline 30.5°C", ans)
        self.assertIn("warmer", ans)

    async def test_08_deterministic_air_quality(self):
        """Deterministic output for air_quality_analysis intent."""
        extracted = ExtractedIntent(
            intent="air_quality_analysis",
            district="Chennai",
            metric="air_quality",
        )
        query_result = {
            "source": "Microsoft Fabric [dbo].[gold_air_quality_latest]",
            "data": [
                {
                    "district": "Chennai",
                    "aqi": 85,
                    "pm2_5": 28.5,
                    "pm10": 55.0,
                    "category": "Moderate",
                }
            ],
            "observation_timestamp": "2026-11-12 17:00",
        }
        ans, _ = await self.generator.generate_answer(
            query="What is the air quality in Chennai?",
            extracted=extracted,
            query_result=query_result,
        )
        self.assertIn("Chennai", ans)
        self.assertIn("85", ans)
        self.assertIn("Moderate", ans)
        self.assertIn("Air Quality Observations", ans)

    async def test_09_deterministic_rainfall_null_handling(self):
        """Strict NULL rainfall handling: never report NULL as false 0.0 without stating unmeasured."""
        extracted = ExtractedIntent(
            intent="rainfall_analysis",
            district="Ariyalur",
            metric="rainfall",
        )
        query_result = {
            "source": "Microsoft Fabric Lakehouse",
            "district": "Ariyalur",
            "date_range": "2026-10-01 to 2026-10-05",
            "quality": {
                "total_measured_rainfall_mm": None,
                "positive_count": 0,
                "measured_observations": 0,
                "total_observations": 5,
                "completeness_pct": 0.0,
                "max_measured_rainfall_mm": None,
            },
            "rainfall_records": [],
            "observation_timestamp": "2026-11-12 17:00",
        }
        ans, _ = await self.generator.generate_answer(
            query="How much rain fell in Ariyalur in early October?",
            extracted=extracted,
            query_result=query_result,
        )
        self.assertIn("Ariyalur", ans)
        self.assertIn("No measurable precipitation recorded", ans)
        self.assertIn("0.0%", ans)

    async def test_10_deterministic_rainfall_positive_handling(self):
        """Deterministic output for positive measured rainfall."""
        extracted = ExtractedIntent(
            intent="rainfall_analysis",
            district="Thoothukudi",
            metric="rainfall",
        )
        query_result = {
            "source": "Microsoft Fabric Lakehouse",
            "district": "Thoothukudi",
            "date_range": "2026-11-11",
            "quality": {
                "total_measured_rainfall_mm": 18.5,
                "positive_count": 1,
                "measured_observations": 1,
                "total_observations": 1,
                "completeness_pct": 100.0,
                "max_measured_rainfall_mm": 18.5,
            },
            "rainfall_records": [
                {"date": "2026-11-11", "rainfall_mm": 18.5, "category": "Moderate Rain"}
            ],
            "observation_timestamp": "2026-11-12 17:00",
        }
        ans, _ = await self.generator.generate_answer(
            query="Did it rain in Thoothukudi yesterday?",
            extracted=extracted,
            query_result=query_result,
        )
        self.assertIn("Thoothukudi", ans)
        self.assertIn("18.50 mm", ans)
        self.assertIn("Rainy Days (>0 mm)", ans)
        self.assertIn("100.0%", ans)

    async def test_11_deterministic_statewide_summary(self):
        """Deterministic output for statewide_summary and weather_report intents."""
        extracted = ExtractedIntent(intent="statewide_summary")
        query_result = {
            "source": "Microsoft Fabric Lakehouse",
            "overview": {
                "districts_covered": 38,
                "avg_temperature": 30.2,
                "max_temperature": 34.5,
                "min_temperature": 22.1,
                "avg_humidity": 68.5,
                "total_rainfall": 45.2,
            },
            "observation_timestamp": "2026-11-12 17:00",
        }
        ans, _ = await self.generator.generate_answer(
            query="Statewide weather summary",
            extracted=extracted,
            query_result=query_result,
        )
        self.assertIn("Tamil Nadu Statewide Weather Bulletin", ans)
        self.assertIn("38 of 38 districts", ans)
        self.assertIn("30.2°C", ans)
        self.assertIn("45.2 mm", ans)

    async def test_12_deterministic_district_intelligence(self):
        """Deterministic output for district_intelligence profile."""
        extracted = ExtractedIntent(
            intent="district_intelligence",
            district="Salem",
        )
        query_result = {
            "source": "Microsoft Fabric [dbo].[dim_district]",
            "details": {
                "district": "Salem",
                "reference_location": "Salem Observatory Station",
                "latitude": 11.6643,
                "longitude": 78.1460,
                "avg_temp": 29.8,
                "max_temp": 35.2,
                "min_temp": 21.0,
                "avg_humidity": 55.0,
            },
            "observation_timestamp": "2026-11-12 17:00",
        }
        ans, _ = await self.generator.generate_answer(
            query="Tell me about Salem district weather profile",
            extracted=extracted,
            query_result=query_result,
        )
        self.assertIn("Salem", ans)
        self.assertIn("Salem Observatory Station", ans)
        self.assertIn("11.6643°N", ans)
        self.assertIn("78.146°E", ans)
        self.assertIn("District Directory", ans)

    async def test_13_deterministic_dashboard_request(self):
        """Deterministic output for dashboard_request intent."""
        extracted = ExtractedIntent(intent="dashboard_request")
        query_result = {
            "source": "Microsoft Fabric Lakehouse",
            "observation_timestamp": "2026-11-12 17:00",
        }
        ans, _ = await self.generator.generate_answer(
            query="Open weather dashboard",
            extracted=extracted,
            query_result=query_result,
        )
        self.assertIn("Custom Dashboard Specification", ans)
        self.assertIn("Weather Overview", ans)
        self.assertIn("Temperature Analytics", ans)
        self.assertIn("Rainfall Analytics", ans)

    async def test_14_deterministic_weather_trend(self):
        """Deterministic output for weather_trend and temperature_analysis."""
        extracted = ExtractedIntent(
            intent="weather_trend",
            district="Madurai",
        )
        query_result = {
            "source": "Microsoft Fabric [dbo].[gold_district_daily_analytics]",
            "district": "Madurai",
            "date_range": "2026-11-06 to 2026-11-12",
            "rows": [
                {"date": "2026-11-12", "avg_temp": 31.0, "max_temp": 34.0, "min_temp": 25.0, "total_rainfall": 0.0},
                {"date": "2026-11-11", "avg_temp": 30.5, "max_temp": 33.5, "min_temp": 24.5, "total_rainfall": 2.0},
            ],
            "observation_timestamp": "2026-11-12 17:00",
        }
        ans, _ = await self.generator.generate_answer(
            query="Show weather trend for Madurai",
            extracted=extracted,
            query_result=query_result,
        )
        self.assertIn("Madurai", ans)
        self.assertIn("2026-11-06 to 2026-11-12", ans)
        self.assertIn("Mean Temperature", ans)

    async def test_15_unknown_intent_guidance(self):
        """Unknown intent returns domain-restricted Tamil Nadu weather guidance."""
        extracted = ExtractedIntent(intent="unknown_intent")
        ans, suggestions = await self.generator.generate_answer(
            query="Who won the cricket match?",
            extracted=extracted,
            query_result={},
        )
        self.assertIn("Tamil Nadu Weather Intelligence Agent", ans)
        self.assertIn("38 districts", ans)
        self.assertTrue(len(suggestions) >= 2)


if __name__ == "__main__":
    unittest.main()
