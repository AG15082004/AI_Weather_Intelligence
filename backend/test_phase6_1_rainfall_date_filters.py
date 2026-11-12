"""Automated Test Suite for Phase 6.1 — Rainfall Data Quality & Advanced Date Intelligence.

Covers 20 required test scenarios:
1. Today's IST date calculation.
2. Yesterday's date calculation.
3. Last 7 Days boundaries.
4. Last 30 Days boundaries.
5. This Week boundaries.
6. Last Week boundaries.
7. This Month boundaries.
8. Last Month boundaries.
9. Custom date range.
10. All Available Data.
11. Invalid date ranges.
12. Future date rejection.
13. District filtering.
14. Rainfall NULL handling.
15. Measured zero rainfall handling.
16. Rainfall positive values.
17. Missing historical rainfall handling.
18. Today current weather availability.
19. Yesterday historical data availability.
20. SQL injection protection.
"""

import asyncio
from datetime import date, timedelta
import sys
import unittest
from fastapi import HTTPException

# Ensure backend directory is in python path
sys.path.insert(0, ".")

from app.utils.date_utils import (
    get_ist_today,
    get_ist_yesterday,
    get_preset_boundaries,
    validate_date_range,
    IST_TZ,
)
from app.services.weather_service import WeatherService
from app.database.query_executor import QueryExecutor


class TestPhase61RainfallAndDateFilters(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.ws = WeatherService()
        self.qe = QueryExecutor()
        self.today = get_ist_today()
        self.yesterday = get_ist_yesterday()

    # -------------------------------------------------------------------------
    # 1. Today's IST date calculation
    # -------------------------------------------------------------------------
    def test_01_today_ist_date(self):
        today = get_ist_today()
        self.assertIsInstance(today, date)
        self.assertEqual(today, date(2026, 11, 12))
        print("✓ Test 1 Passed: Today's IST date correctly computed as 2026-11-12")

    # -------------------------------------------------------------------------
    # 2. Yesterday's date calculation
    # -------------------------------------------------------------------------
    def test_02_yesterday_ist_date(self):
        yesterday = get_ist_yesterday()
        self.assertIsInstance(yesterday, date)
        self.assertEqual(yesterday, self.today - timedelta(days=1))
        self.assertEqual(yesterday, date(2026, 11, 11))
        print("✓ Test 2 Passed: Yesterday's IST date correctly computed as 2026-11-11")

    # -------------------------------------------------------------------------
    # 3. Last 7 Days boundaries
    # -------------------------------------------------------------------------
    def test_03_last_7_days_boundaries(self):
        start, end = get_preset_boundaries("last_7_days")
        self.assertEqual(end, self.today)
        self.assertEqual(start, self.today - timedelta(days=6))
        self.assertEqual((end - start).days + 1, 7)
        self.assertEqual(start, date(2026, 11, 6))
        print(f"✓ Test 3 Passed: Last 7 Days span {start} to {end} (7 days inclusive)")

    # -------------------------------------------------------------------------
    # 4. Last 30 Days boundaries
    # -------------------------------------------------------------------------
    def test_04_last_30_days_boundaries(self):
        start, end = get_preset_boundaries("last_30_days")
        self.assertEqual(end, self.today)
        self.assertEqual(start, self.today - timedelta(days=29))
        self.assertEqual((end - start).days + 1, 30)
        self.assertEqual(start, date(2026, 10, 14))
        print(f"✓ Test 4 Passed: Last 30 Days span {start} to {end} (30 days inclusive)")

    # -------------------------------------------------------------------------
    # 5. This Week boundaries
    # -------------------------------------------------------------------------
    def test_05_this_week_boundaries(self):
        start, end = get_preset_boundaries("this_week")
        self.assertEqual(end, self.today)
        self.assertEqual(start.weekday(), 0)  # Monday
        self.assertTrue(start <= end)
        self.assertEqual(start, date(2026, 11, 9))
        print(f"✓ Test 5 Passed: This Week starts on Monday {start} through today {end}")

    # -------------------------------------------------------------------------
    # 6. Last Week boundaries
    # -------------------------------------------------------------------------
    def test_06_last_week_boundaries(self):
        start, end = get_preset_boundaries("last_week")
        self.assertEqual(start.weekday(), 0)  # Monday
        self.assertEqual(end.weekday(), 6)    # Sunday
        self.assertEqual((end - start).days + 1, 7)
        self.assertEqual(start, date(2026, 11, 2))
        self.assertEqual(end, date(2026, 11, 8))
        print(f"✓ Test 6 Passed: Last Week spans Monday {start} to Sunday {end}")

    # -------------------------------------------------------------------------
    # 7. This Month boundaries
    # -------------------------------------------------------------------------
    def test_07_this_month_boundaries(self):
        start, end = get_preset_boundaries("this_month")
        self.assertEqual(start, date(self.today.year, self.today.month, 1))
        self.assertEqual(end, self.today)
        self.assertEqual(start, date(2026, 11, 1))
        print(f"✓ Test 7 Passed: This Month spans {start} through {end}")

    # -------------------------------------------------------------------------
    # 8. Last Month boundaries
    # -------------------------------------------------------------------------
    def test_08_last_month_boundaries(self):
        start, end = get_preset_boundaries("last_month")
        self.assertEqual(start, date(2026, 10, 1))
        self.assertEqual(end, date(2026, 10, 31))
        print(f"✓ Test 8 Passed: Last Month spans full month {start} to {end}")

    # -------------------------------------------------------------------------
    # 9. Custom date range
    # -------------------------------------------------------------------------
    def test_09_custom_date_range(self):
        custom_start = date(2026, 11, 1)
        custom_end = date(2026, 11, 10)
        # Should not raise exception
        validate_date_range(custom_start, custom_end)
        print(f"✓ Test 9 Passed: Custom range {custom_start} to {custom_end} successfully validated")

    # -------------------------------------------------------------------------
    # 10. All Available Data
    # -------------------------------------------------------------------------
    def test_10_all_available_data_boundaries(self):
        start, end = get_preset_boundaries("all_available")
        self.assertEqual(start, date(2026, 1, 1))
        self.assertEqual(end, self.today)
        print(f"✓ Test 10 Passed: All Available Data spans {start} to {end}")

    # -------------------------------------------------------------------------
    # 11. Invalid date ranges
    # -------------------------------------------------------------------------
    def test_11_invalid_date_ranges(self):
        invalid_start = date(2026, 11, 10)
        invalid_end = date(2026, 11, 5)
        with self.assertRaises(HTTPException) as ctx:
            validate_date_range(invalid_start, invalid_end)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("cannot be greater than end_date", ctx.exception.detail)
        print(f"✓ Test 11 Passed: start_date > end_date correctly rejected with HTTP 400: '{ctx.exception.detail}'")

    # -------------------------------------------------------------------------
    # 12. Future date rejection
    # -------------------------------------------------------------------------
    def test_12_future_date_rejection(self):
        future_date = date(2026, 12, 1)
        with self.assertRaises(HTTPException) as ctx:
            validate_date_range(end_date=future_date)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("cannot be in the future", ctx.exception.detail)
        print(f"✓ Test 12 Passed: Future date {future_date} correctly rejected with HTTP 400: '{ctx.exception.detail}'")

    # -------------------------------------------------------------------------
    # 13. District filtering
    # -------------------------------------------------------------------------
    async def test_13_district_filtering(self):
        res = await self.ws.get_current_weather(district="Chennai")
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["district"], "Chennai")
        print(f"✓ Test 13 Passed: District filter successfully isolated district Chennai (temp: {res['data'][0]['temperature']}°C)")

    # -------------------------------------------------------------------------
    # 14. Rainfall NULL handling
    # -------------------------------------------------------------------------
    async def test_14_rainfall_null_handling(self):
        # Query gold_district_daily_analytics directly to verify raw column contains NULLs
        sql = """
            SELECT TOP 5 weather_date, district_name, precipitation_sum
            FROM [dbo].[gold_district_daily_analytics]
            WHERE precipitation_sum IS NULL
        """
        rows = await self.qe.execute_query(sql)
        self.assertTrue(len(rows) > 0)
        for r in rows:
            self.assertIsNone(r["precipitation_sum"])
        print(f"✓ Test 14 Passed: Verified Fabric gold_district_daily_analytics has explicit NULL precipitation without silent ISNULL conversions")

    # -------------------------------------------------------------------------
    # 15. Measured zero rainfall handling
    # -------------------------------------------------------------------------
    async def test_15_measured_zero_rainfall(self):
        # In silver_weather_current, there are measured zero readings where precipitation_mm = 0.0
        sql = """
            SELECT TOP 5 district_name, precipitation_mm, last_updated
            FROM [dbo].[silver_weather_current]
            WHERE precipitation_mm = 0.0
        """
        rows = await self.qe.execute_query(sql)
        self.assertTrue(len(rows) > 0)
        self.assertEqual(rows[0]["precipitation_mm"], 0.0)
        print(f"✓ Test 15 Passed: Verified measured zero precipitation (0.0 mm) exists and is preserved for {rows[0]['district_name']}")

    # -------------------------------------------------------------------------
    # 16. Rainfall positive values
    # -------------------------------------------------------------------------
    async def test_16_rainfall_positive_values(self):
        # Verified positive rain exists in silver_weather_current for 2026-11-11
        sql = """
            SELECT district_name, ROUND(SUM(precipitation_mm), 2) as total_rain
            FROM [dbo].[silver_weather_current]
            WHERE CAST(last_updated AS DATE) = '2026-11-11' AND precipitation_mm > 0
            GROUP BY district_name
            ORDER BY total_rain DESC
        """
        rows = await self.qe.execute_query(sql)
        self.assertTrue(len(rows) > 0)
        top_district = rows[0]
        self.assertGreater(top_district["total_rain"], 0.0)
        print(f"✓ Test 16 Passed: Verified real positive rainfall observations on 2026-11-11 for {len(rows)} districts (Top: {top_district['district_name']} with {top_district['total_rain']} mm)")

    # -------------------------------------------------------------------------
    # 17. Missing historical rainfall handling
    # -------------------------------------------------------------------------
    async def test_17_missing_historical_rainfall_handling(self):
        # When querying historical dates only where era5_land data has NULLs
        res = await self.ws.get_overview(start_date=date(2026, 10, 1), end_date=date(2026, 10, 7))
        self.assertEqual(res["status"], "success")
        quality = res["rainfall_quality"]
        self.assertIn(quality["status"], ["unmeasured", "sparse"])
        self.assertIsNone(res["data"]["total_rainfall"])
        print(f"✓ Test 17 Passed: Missing historical rainfall properly returns total_rainfall=None and quality status='{quality['status']}'")

    # -------------------------------------------------------------------------
    # 18. Today current weather availability
    # -------------------------------------------------------------------------
    async def test_18_today_current_weather(self):
        res = await self.ws.get_current_weather(date_param=self.today)
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["data"]), 38)
        first_d = res["data"][0]
        self.assertIn("temperature", first_d)
        self.assertIn("humidity", first_d)
        self.assertIn("condition", first_d)
        print(f"✓ Test 18 Passed: Today's live snapshot retrieved for all 38 districts ({res['source']})")

    # -------------------------------------------------------------------------
    # 19. Yesterday historical data availability
    # -------------------------------------------------------------------------
    async def test_19_yesterday_data_availability(self):
        res = await self.ws.get_current_weather(date_param=self.yesterday)
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["data"]), 38)
        self.assertEqual(res["filters"]["observation_date"], "2026-11-11")
        self.assertIn("silver_weather_current", res["source"])
        print(f"✓ Test 19 Passed: Yesterday's observations retrieved for all 38 districts from {res['source']}")

    # -------------------------------------------------------------------------
    # 20. SQL injection protection
    # -------------------------------------------------------------------------
    async def test_20_sql_injection_protection(self):
        malicious_input = "Chennai'; DROP TABLE test; --"
        res = await self.ws.get_current_weather(district=malicious_input)
        self.assertIn(res["status"], ["success", "unavailable"])
        # Parameterized query searches for exact string, returning 0 rows safely
        self.assertEqual(len(res["data"]), 0)
        print(f"✓ Test 20 Passed: Parameterized query successfully neutralized SQL injection attack string without error")


if __name__ == "__main__":
    unittest.main(verbosity=2)
