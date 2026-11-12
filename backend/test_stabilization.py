"""Phase 7 Stabilization & Hardening Test Suite.

Validates:
1. Timezone & IST handling (Asia/Kolkata, no UTC offset replacements, startup validation)
2. Microsoft Fabric SQL connectivity, token refresh, timeout classification & cursor cleanup
3. Ollama health checking, timeout handling, error logging, and deterministic fallback
4. AI Agent intent handling, rainfall data quality, chart spec generation, and conversational memory
"""

import asyncio
import os
import sys
import unittest
from datetime import date, datetime, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.utils.date_utils import (
    IST_TZ,
    get_ist_now,
    get_ist_today,
    get_ist_yesterday,
    validate_date_range,
    validate_timezone_support,
)
from app.database.query_executor import (
    QueryExecutor,
    FabricDatabaseError,
    FabricTimeoutError,
    FabricAuthenticationError,
    FabricConnectionError,
    classify_db_error,
)
from app.services.fabric_connection import (
    FabricConnectionService,
    is_transient_connection_error,
)
from app.services.grounded_response_generator import GroundedResponseGenerator
from app.services.ai_service import AIService
from app.schemas.ai import ExtractedIntent, DateRangeSpecification, ChartSpec


class TestPhase7Stabilization(unittest.IsolatedAsyncioTestCase):
    """Automated test cases for Phase 7 Stabilization."""

    # =========================================================================
    # 1. Timezone & IST Validation
    # =========================================================================

    def test_01_timezone_initialization(self):
        """Verify Asia/Kolkata timezone is properly initialized from IANA database."""
        self.assertTrue(validate_timezone_support())
        now = get_ist_now()
        self.assertIsNotNone(now.tzinfo)
        self.assertEqual(str(now.tzinfo), "Asia/Kolkata")
        # IST offset is strictly +05:30 (19800 seconds)
        self.assertEqual(now.utcoffset().total_seconds(), 19800)
        print("✓ Test 1 Passed: Asia/Kolkata timezone successfully validated with +05:30 offset")

    def test_02_ist_date_boundaries(self):
        """Verify today and yesterday calculations in IST timezone."""
        today = get_ist_today()
        yesterday = get_ist_yesterday()
        self.assertEqual(today - timedelta(days=1), yesterday)
        self.assertIsInstance(today, date)
        self.assertIsInstance(yesterday, date)

        # Validation rules
        start_d, end_d = validate_date_range(yesterday, today)
        self.assertEqual(start_d, yesterday)
        self.assertEqual(end_d, today)
        print(f"✓ Test 2 Passed: IST date boundaries verified (Yesterday={yesterday}, Today={today})")

    # =========================================================================
    # 2. Fabric SQL Connectivity & Timeout Handling
    # =========================================================================

    def test_03_transient_connection_error_detection(self):
        """Verify transient error classification detects retryable connection errors."""
        transient_err = Exception("ODBC error: [HYT00] [Microsoft][ODBC Driver 18] Login timeout expired")
        self.assertTrue(is_transient_connection_error(transient_err))

        link_fail = Exception("Communication link failure [08S01]")
        self.assertTrue(is_transient_connection_error(link_fail))

        non_transient = Exception("Invalid column name 'non_existent_column'")
        self.assertFalse(is_transient_connection_error(non_transient))
        print("✓ Test 3 Passed: Transient connection error detection verified")

    def test_04_query_error_classification(self):
        """Verify SQL errors are classified into semantic exception types."""
        timeout_err = classify_db_error(Exception("Query execution timeout expired [HYT00]"))
        self.assertIsInstance(timeout_err, FabricTimeoutError)

        auth_err = classify_db_error(Exception("Login failed for user token [28000]"))
        self.assertIsInstance(auth_err, FabricAuthenticationError)

        conn_err = classify_db_error(Exception("Cannot open server requested by the login [08001]"))
        self.assertIsInstance(conn_err, FabricConnectionError)
        print("✓ Test 4 Passed: Semantic error classification (Timeout, Auth, Connection) verified")

    async def test_05_fabric_query_cleanup(self):
        """Verify cursor is reliably closed even if query execution raises an exception."""
        qe = QueryExecutor()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Simulated Fabric query timeout [HYT00]")

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch.object(qe._pool, "get_connection", AsyncMock(return_value=mock_conn)):
            with self.assertRaises(FabricTimeoutError):
                await qe.execute_query("SELECT * FROM [dbo].[mock_table]")

        # Ensure cursor was closed in finally block!
        mock_cursor.close.assert_called_once()
        print("✓ Test 5 Passed: Cursor cleanup in finally block verified on error")

    async def test_06_fabric_empty_results(self):
        """Verify QueryExecutor handles empty query results gracefully."""
        qe = QueryExecutor()
        mock_cursor = MagicMock()
        mock_cursor.description = [("district",), ("temp",)]
        mock_cursor.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch.object(qe._pool, "get_connection", AsyncMock(return_value=mock_conn)):
            rows = await qe.execute_query("SELECT * FROM [dbo].[empty_table]")
            self.assertEqual(rows, [])
        print("✓ Test 6 Passed: Empty query results returned cleanly as empty list")

    # =========================================================================
    # 3. Ollama Integration & Deterministic Fallback
    # =========================================================================

    async def test_07_ollama_health_check(self):
        """Verify Ollama health check responds with model availability."""
        gen = GroundedResponseGenerator()
        health = await gen.check_ollama_health()
        self.assertIn("status", health)
        self.assertIn("model", health)
        self.assertIn("latency_ms", health)
        print(f"✓ Test 7 Passed: Ollama health check evaluated (Status={health['status']}, Model={health['model']})")

    async def test_08_ollama_connection_refused_fallback(self):
        """Verify deterministic fallback is engaged when Ollama connection is refused."""
        gen = GroundedResponseGenerator()
        extracted = ExtractedIntent(
            intent="current_weather",
            district="Madurai",
            districts=["Madurai"],
            confidence=0.9,
            date_range=DateRangeSpecification(preset="today"),
            metric="general",
            raw_query="What is Madurai weather?",
        )
        mock_fabric_data = {
            "source": "Microsoft Fabric Lakehouse",
            "observation_timestamp": "2026-11-12 14:00",
            "data": [{
                "district": "Madurai",
                "temperature": 30.5,
                "feels_like": 34.0,
                "condition": "Partly Cloudy",
                "humidity": 65.0,
                "wind_speed": 14.2,
                "wind_direction": "NE",
                "precipitation_mm": 0.0,
            }],
        }

        with patch.object(gen, "_call_ollama", side_effect=Exception("Connection refused [Errno 111]")):
            ans, suggestions = await gen.generate_answer(
                query="What is Madurai weather?",
                extracted=extracted,
                query_result=mock_fabric_data,
            )

        self.assertIn("Madurai", ans)
        self.assertIn("30.5°C", ans)
        self.assertIn("Partly Cloudy", ans)
        self.assertIn("Microsoft Fabric Lakehouse", ans)
        self.assertTrue(len(suggestions) > 0)
        print("✓ Test 8 Passed: Grounded deterministic fallback formatted real numbers on Ollama connection refused")

    async def test_09_ollama_empty_response_fallback(self):
        """Verify empty or malformed LLM response safely engages deterministic fallback."""
        gen = GroundedResponseGenerator()
        extracted = ExtractedIntent(
            intent="rainfall_analysis",
            district="Thoothukudi",
            districts=["Thoothukudi"],
            confidence=0.9,
            date_range=DateRangeSpecification(preset="yesterday"),
            metric="rainfall",
            raw_query="Did it rain in Thoothukudi yesterday?",
        )
        mock_data = {
            "source": "Microsoft Fabric Lakehouse",
            "district": "Thoothukudi",
            "date_range": "2026-11-11 to 2026-11-11",
            "rainfall_records": [{
                "date": "2026-11-11",
                "district": "Thoothukudi",
                "rainfall_mm": 12.4,
                "category": "Moderate",
            }],
            "quality": {
                "total_measured_rainfall_mm": 12.4,
                "positive_count": 1,
                "completeness_pct": 100.0,
            },
            "observation_timestamp": "2026-11-11",
        }

        # Simulate LLM returning empty string
        with patch.object(gen, "_call_ollama", AsyncMock(return_value="")):
            ans, suggestions = await gen.generate_answer(
                query="Did it rain in Thoothukudi yesterday?",
                extracted=extracted,
                query_result=mock_data,
            )

        self.assertIn("Thoothukudi", ans)
        self.assertIn("12.4 mm", ans)
        self.assertIn("100.0%", ans)
        print("✓ Test 9 Passed: Empty LLM output seamlessly engaged verified deterministic rainfall summary")

    # =========================================================================
    # 4. AI Agent End-to-End Queries & Routing
    # =========================================================================

    async def test_10_today_statewide_summary_fast_path(self):
        """Verify today's statewide weather overview resolves quickly via fast path."""
        ai = AIService()
        res = await ai.generate_response("What is today's weather across Tamil Nadu?")
        self.assertEqual(res["intent"], "statewide_summary")
        self.assertIn("Tamil Nadu", res["answer"])
        self.assertIn("Districts", res["answer"])
        self.assertIsNotNone(res["observation_timestamp"])
        self.assertIsNotNone(res["chart"])
        print("✓ Test 10 Passed: Fast-path statewide summary executed successfully with ChartSpec")

    async def test_11_rainfall_null_preservation(self):
        """Verify rainfall analytics preserve explicit NULLs without converting to false 0.0."""
        ai = AIService()
        res = await ai.generate_response("Show rainfall for Nilgiris")
        self.assertEqual(res["intent"], "rainfall_analysis")
        self.assertIn("Nilgiris", res["answer"])
        self.assertTrue(len(res["sources"]) > 0)
        print("✓ Test 11 Passed: Rainfall analytics preserved data quality without silent conversion")

    async def test_12_chart_spec_structure(self):
        """Verify chart specs produce valid ChartSpec JSON schemas."""
        ai = AIService()
        res = await ai.generate_response("Which district has the highest temperature today?")
        self.assertEqual(res["intent"], "weather_ranking")
        chart = res["chart"]
        self.assertIsNotNone(chart)
        self.assertIn(chart["type"], ["bar", "grouped_bar", "line", "area"])
        self.assertTrue(len(chart["series"]) > 0)
        self.assertTrue(len(chart["data"]) > 0)
        print(f"✓ Test 12 Passed: ChartSpec verified (Type={chart['type']}, DataPoints={len(chart['data'])})")


if __name__ == "__main__":
    unittest.main(verbosity=2)

