"""Microsoft Fabric Gold Table Data Validation Service.

Executes safe, read-only queries against discovered Fabric Lakehouse tables
to validate table accessibility, actual record counts, district coverage,
date ranges, NULL metrics, and latest weather observations.
"""

from typing import Any, Dict, List, Optional

import structlog

from app.services.fabric_connection import FabricConnectionService
from app.services.fabric_schema_service import FabricSchemaService

log = structlog.get_logger()

EXPECTED_BENCHMARKS = {
    "daily_weather": {
        "expected_rows": 11666,
        "tolerance": 0.15,
        "expected_districts": 38,
        "description": "Daily weather analytics historical observations",
    },
    "monthly_weather": {
        "expected_rows": 418,
        "tolerance": 0.15,
        "expected_districts": 38,
        "description": "Monthly weather analytics aggregated records",
    },
    "rainfall": {
        "expected_rows": 418,
        "tolerance": 0.15,
        "expected_districts": 38,
        "description": "Rainfall analytics monthly metrics",
    },
    "current_weather": {
        "expected_rows": 38,
        "tolerance": 0.05,
        "expected_districts": 38,
        "description": "Latest current weather for all 38 districts",
    },
    "air_quality": {
        "expected_rows": 38,
        "tolerance": 0.05,
        "expected_districts": 38,
        "description": "Latest air quality readings for all 38 districts",
    },
}


class FabricDataValidator:
    """Validates data integrity and accessibility across Fabric Gold tables."""

    def __init__(
        self,
        connection_service: Optional[FabricConnectionService] = None,
        schema_service: Optional[FabricSchemaService] = None,
    ) -> None:
        self._conn_svc = connection_service or FabricConnectionService()
        self._schema_svc = schema_service or FabricSchemaService(self._conn_svc)

    async def validate_table(
        self, schema: str, table_name: str, columns: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Run validation checks on a single table.

        Args:
            schema: Table schema (e.g. dbo).
            table_name: Table name.
            columns: Discovered column definitions.

        Returns:
            Dict containing validation findings.
        """
        clean_s = schema.replace("]", "").replace("[", "")
        clean_t = table_name.replace("]", "").replace("[", "")
        col_names = [c["name"] for c in columns]

        result: Dict[str, Any] = {
            "table_name": clean_t,
            "schema": clean_s,
            "accessible": False,
            "row_count": None,
            "district_column": None,
            "district_count": None,
            "date_column": None,
            "min_date": None,
            "max_date": None,
            "null_analysis": {},
            "sample_row": None,
            "benchmark_comparison": None,
        }

        # 1. Identify potential district and date columns
        district_col = self._find_column(col_names, ["district", "district_name", "location", "city"])
        date_col = self._find_column(col_names, ["date", "observation_date", "recorded_date", "timestamp", "last_updated"])
        result["district_column"] = district_col
        result["date_column"] = date_col

        conn = await self._conn_svc.connect()
        cursor = conn.cursor()

        try:
            # Accessibility & sample check
            cursor.execute(f"SELECT TOP 1 * FROM [{clean_s}].[{clean_t}]")
            cols = [desc[0] for desc in cursor.description] if cursor.description else []
            sample = cursor.fetchone()
            result["accessible"] = True
            if sample and cols:
                result["sample_row"] = {
                    cols[i]: str(sample[i]) if sample[i] is not None else None
                    for i in range(len(cols))
                }

            # Row count check
            cursor.execute(f"SELECT COUNT(*) FROM [{clean_s}].[{clean_t}]")
            row_cnt = cursor.fetchone()
            count_val = int(row_cnt[0]) if row_cnt else 0
            result["row_count"] = count_val

            # District coverage check
            if district_col:
                cursor.execute(
                    f"SELECT COUNT(DISTINCT [{district_col}]) FROM [{clean_s}].[{clean_t}] WHERE [{district_col}] IS NOT NULL"
                )
                d_cnt = cursor.fetchone()
                result["district_count"] = int(d_cnt[0]) if d_cnt else 0

            # Date range check
            if date_col:
                cursor.execute(
                    f"SELECT MIN([{date_col}]), MAX([{date_col}]) FROM [{clean_s}].[{clean_t}]"
                )
                d_range = cursor.fetchone()
                if d_range:
                    result["min_date"] = str(d_range[0]) if d_range[0] is not None else None
                    result["max_date"] = str(d_range[1]) if d_range[1] is not None else None

            # Null analysis on numeric / metric columns
            metric_cols = [c["name"] for c in columns if c["data_type"] in ("float", "decimal", "int", "numeric", "real")][:5]
            if metric_cols and count_val > 0:
                null_selects = ", ".join(
                    f"SUM(CASE WHEN [{mc}] IS NULL THEN 1 ELSE 0 END) AS [{mc}_nulls]"
                    for mc in metric_cols
                )
                cursor.execute(f"SELECT {null_selects} FROM [{clean_s}].[{clean_t}]")
                null_counts = cursor.fetchone()
                if null_counts:
                    for i, mc in enumerate(metric_cols):
                        n_cnt = int(null_counts[i]) if null_counts[i] is not None else 0
                        pct = round((n_cnt / count_val) * 100, 2)
                        result["null_analysis"][mc] = {"null_count": n_cnt, "null_pct": pct}

            # Benchmark comparison
            result["benchmark_comparison"] = self._evaluate_benchmark(clean_t, count_val, result.get("district_count"))

        except Exception as exc:
            log.warning("table_validation_error", table=table_name, error=str(exc))
            result["error"] = str(exc)
        finally:
            cursor.close()

        return result

    async def validate_all_tables(self) -> Dict[str, Any]:
        """Discover tables and validate all discovered Gold / dimension tables."""
        tables = await self._schema_svc.discover_tables()
        validation_results: List[Dict[str, Any]] = []

        for tbl in tables:
            cols = await self._schema_svc.discover_columns(tbl["name"], schema=tbl["schema"])
            val = await self.validate_table(tbl["schema"], tbl["name"], cols)
            validation_results.append(val)

        return {
            "total_tables_validated": len(validation_results),
            "accessible_tables": sum(1 for v in validation_results if v["accessible"]),
            "results": validation_results,
        }

    def _find_column(self, columns: List[str], candidates: List[str]) -> Optional[str]:
        """Find the best matching column name case-insensitively."""
        col_map = {c.lower(): c for c in columns}
        for cand in candidates:
            if cand.lower() in col_map:
                return col_map[cand.lower()]
        for cand in candidates:
            for c_low, c_actual in col_map.items():
                if cand.lower() in c_low:
                    return c_actual
        return None

    def _evaluate_benchmark(
        self, table_name: str, actual_rows: int, actual_districts: Optional[int]
    ) -> Optional[Dict[str, Any]]:
        """Compare actual counts against documented platform statistics."""
        t_low = table_name.lower()
        matched_key = None
        for key in EXPECTED_BENCHMARKS:
            if key in t_low or (key == "daily_weather" and "daily" in t_low):
                matched_key = key
                break

        if not matched_key:
            return None

        bench = EXPECTED_BENCHMARKS[matched_key]
        expected_rows = bench["expected_rows"]
        diff_pct = abs(actual_rows - expected_rows) / expected_rows if expected_rows else 0
        matches = diff_pct <= bench["tolerance"]

        return {
            "dataset": matched_key,
            "expected_rows": expected_rows,
            "actual_rows": actual_rows,
            "row_match": matches,
            "expected_districts": bench["expected_districts"],
            "actual_districts": actual_districts,
            "district_match": actual_districts == bench["expected_districts"] if actual_districts else False,
            "description": bench["description"],
        }

