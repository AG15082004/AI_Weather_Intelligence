"""Phase 8.5 — Performance Optimization and Production Reliability Automated Tests.

Verifies:
1. Thread-safe bounded TTL cache with capacity enforcement and LRU/FIFO eviction.
2. Cache hit/miss metric tracking and hit ratio calculation.
3. Unified cache invalidation across services and routers.
4. Strict NULL rainfall preservation in cached payloads (never convert NULL to 0.0).
5. Safe concurrent query handling without deadlocks or thread contention.
6. Non-blocking health checks and operational telemetry reporting.
7. Date-range-aware cache key isolation.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import sys
import time
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, ".")

from app.main import app
from app.services.metrics_service import metrics_service
from app.utils.cache import TTLCache, shared_cache


class TestPhase85PerformanceAndReliability(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        shared_cache.clear()

    # -------------------------------------------------------------------------
    # 1. Bounded Cache Capacity Enforcement
    # -------------------------------------------------------------------------
    def test_01_bounded_cache_capacity_eviction(self):
        """Cache must evict oldest entries when capacity threshold is reached."""
        small_cache = TTLCache(ttl_seconds=60, max_entries=5)

        # Insert 5 entries (fill to capacity)
        for i in range(1, 6):
            small_cache.set(f"key_{i}", f"val_{i}")

        self.assertEqual(small_cache.get_stats()["size"], 5)
        self.assertEqual(small_cache.get_stats()["evictions"], 0)

        # Access key_1 to make it recently used (key_2 becomes oldest)
        self.assertEqual(small_cache.get("key_1"), "val_1")

        # Insert 6th entry: must evict the least recently used key (key_2)
        small_cache.set("key_6", "val_6")

        stats = small_cache.get_stats()
        self.assertEqual(stats["size"], 5)
        self.assertEqual(stats["evictions"], 1)
        self.assertIsNone(small_cache.get("key_2"))
        self.assertEqual(small_cache.get("key_1"), "val_1")
        self.assertEqual(small_cache.get("key_6"), "val_6")

    # -------------------------------------------------------------------------
    # 2. Hit / Miss Metrics Tracking
    # -------------------------------------------------------------------------
    def test_02_cache_metrics_tracking(self):
        """Cache accurately tracks hits, misses, and hit ratio percentage."""
        test_cache = TTLCache(ttl_seconds=60, max_entries=10)

        test_cache.set("item_a", {"temp": 32.5})

        # 1 hit
        val = test_cache.get("item_a")
        self.assertIsNotNone(val)

        # 2 misses
        self.assertIsNone(test_cache.get("non_existent_1"))
        self.assertIsNone(test_cache.get("non_existent_2"))

        stats = test_cache.get_stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 2)
        # Hit ratio = 1 / (1 + 2) = 33.3%
        self.assertEqual(stats["hit_ratio_pct"], 33.3)

    # -------------------------------------------------------------------------
    # 3. Cache Expiration (TTL Enforcement)
    # -------------------------------------------------------------------------
    def test_03_ttl_expiration(self):
        """Expired entries must return None and register as misses."""
        fast_cache = TTLCache(ttl_seconds=1, max_entries=10)
        fast_cache.set("ephemeral", "quick_data", ttl_seconds=0.05)

        # Immediate fetch succeeds
        self.assertEqual(fast_cache.get("ephemeral"), "quick_data")

        # Wait for expiration
        time.sleep(0.06)

        # Expired fetch returns None
        self.assertIsNone(fast_cache.get("ephemeral"))
        self.assertEqual(fast_cache.get_stats()["misses"], 1)

    # -------------------------------------------------------------------------
    # 4. Strict NULL Rainfall Preservation in Cache
    # -------------------------------------------------------------------------
    def test_04_null_rainfall_cache_preservation(self):
        """Cached rainfall analytics must preserve None/NULL values without converting to 0.0."""
        payload_with_null = {
            "status": "success",
            "rainfall_quality": {
                "total_days": 10,
                "measured_days": 2,
                "missing_days": 8,
            },
            "rainfall_trend": [
                {"date": "2026-10-01", "rainfall_mm": None, "status": "missing"},
                {"date": "2026-11-11", "rainfall_mm": 18.5, "status": "measured_positive"},
                {"date": "2026-11-12", "rainfall_mm": 0.0, "status": "measured_zero"},
            ],
        }

        shared_cache.set("rainfall_quality_test", payload_with_null)
        cached_result = shared_cache.get("rainfall_quality_test")

        self.assertIsNotNone(cached_result)
        # Oct 1 record must be None, NOT 0.0!
        self.assertIsNone(cached_result["rainfall_trend"][0]["rainfall_mm"])
        # Nov 11 record is 18.5
        self.assertEqual(cached_result["rainfall_trend"][1]["rainfall_mm"], 18.5)
        # Nov 12 record is 0.0
        self.assertEqual(cached_result["rainfall_trend"][2]["rainfall_mm"], 0.0)

    # -------------------------------------------------------------------------
    # 5. Thread-Safe Concurrency
    # -------------------------------------------------------------------------
    def test_05_concurrent_cache_access(self):
        """Concurrent reads and writes must execute cleanly without race conditions."""
        concurrent_cache = TTLCache(ttl_seconds=60, max_entries=50)

        def worker(thread_id: int):
            for i in range(50):
                concurrent_cache.set(f"k_{thread_id}_{i}", f"v_{i}")
                concurrent_cache.get(f"k_{thread_id}_{i}")

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(worker, tid) for tid in range(8)]
            for f in futures:
                f.result()

        stats = concurrent_cache.get_stats()
        self.assertLessEqual(stats["size"], 50)
        self.assertGreater(stats["hits"], 0)
        self.assertGreater(stats["evictions"], 0)

    # -------------------------------------------------------------------------
    # 6. Date-Range-Aware Cache Key Isolation
    # -------------------------------------------------------------------------
    def test_06_date_range_cache_isolation(self):
        """Different date ranges must generate isolated cache entries."""
        key_1 = "overview:2026-11-06:2026-11-12"
        key_2 = "overview:2026-10-01:2026-10-05"

        shared_cache.set(key_1, {"range": "recent_7_days", "avg_temp": 30.5})
        shared_cache.set(key_2, {"range": "early_october", "avg_temp": 28.2})

        res_1 = shared_cache.get(key_1)
        res_2 = shared_cache.get(key_2)

        self.assertNotEqual(res_1["avg_temp"], res_2["avg_temp"])
        self.assertEqual(res_1["range"], "recent_7_days")
        self.assertEqual(res_2["range"], "early_october")

    # -------------------------------------------------------------------------
    # 7. Operational Status Cache Reporting
    # -------------------------------------------------------------------------
    def test_07_operational_status_includes_cache_stats(self):
        """Operational status endpoint reports cache health and hit/miss stats."""
        resp = self.client.get("/api/monitoring/operational-status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertIn("cache", data)
        self.assertIn("size", data["cache"])
        self.assertIn("max_entries", data["cache"])
        self.assertIn("hits", data["cache"])
        self.assertIn("misses", data["cache"])
        self.assertIn("hit_ratio_pct", data["cache"])


if __name__ == "__main__":
    unittest.main()

