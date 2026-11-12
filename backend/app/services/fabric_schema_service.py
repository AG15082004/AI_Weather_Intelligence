"""Microsoft Fabric Lakehouse schema discovery service.

Discovers schemas, tables, columns, data types, constraints, and row counts
from the connected Fabric SQL Analytics Endpoint using INFORMATION_SCHEMA.
Generates backend/app/database/fabric_schema.json with actual discovered metadata.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from app.services.fabric_connection import FabricConnectionService

log = structlog.get_logger()

DEFAULT_SCHEMA_PATH = (
    Path(__file__).parent.parent / "database" / "fabric_schema.json"
)


class FabricSchemaService:
    """Discovers and inspects Microsoft Fabric SQL database schemas and metadata."""

    def __init__(
        self, connection_service: Optional[FabricConnectionService] = None
    ) -> None:
        self._connection_service = connection_service or FabricConnectionService()

    async def discover_schemas(self) -> List[str]:
        """Discover all distinct schemas in the database.

        Returns:
            List of schema names (excluding system schemas if desired).
        """
        conn = await self._connection_service.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT DISTINCT TABLE_SCHEMA "
                "FROM INFORMATION_SCHEMA.TABLES "
                "ORDER BY TABLE_SCHEMA"
            )
            schemas = [row[0] for row in cursor.fetchall()]
            log.info("schemas_discovered", count=len(schemas), schemas=schemas)
            return schemas
        finally:
            cursor.close()

    async def discover_tables(
        self, schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Discover tables and views in the database.

        Args:
            schema: Optional schema filter. If None, discovers across all non-system schemas.

        Returns:
            List of table metadata dicts with schema, name, and type.
        """
        conn = await self._connection_service.connect()
        cursor = conn.cursor()
        try:
            if schema:
                cursor.execute(
                    "SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE "
                    "FROM INFORMATION_SCHEMA.TABLES "
                    "WHERE TABLE_SCHEMA = ? "
                    "ORDER BY TABLE_SCHEMA, TABLE_NAME",
                    (schema,),
                )
            else:
                cursor.execute(
                    "SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE "
                    "FROM INFORMATION_SCHEMA.TABLES "
                    "WHERE TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA') "
                    "ORDER BY TABLE_SCHEMA, TABLE_NAME"
                )

            tables = [
                {
                    "schema": row[0],
                    "name": row[1],
                    "type": row[2],
                }
                for row in cursor.fetchall()
            ]
            log.info("tables_discovered", count=len(tables), schema=schema)
            return tables
        finally:
            cursor.close()

    async def discover_columns(
        self, table_name: str, schema: str = "dbo"
    ) -> List[Dict[str, Any]]:
        """Discover column definitions for a given table.

        Args:
            table_name: Name of the table.
            schema: Schema name.

        Returns:
            List of column metadata dictionaries.
        """
        conn = await self._connection_service.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT COLUMN_NAME, ORDINAL_POSITION, DATA_TYPE, IS_NULLABLE, "
                "       CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE, COLUMN_DEFAULT "
                "FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? "
                "ORDER BY ORDINAL_POSITION",
                (schema, table_name),
            )
            columns = [
                {
                    "name": row[0],
                    "ordinal_position": row[1],
                    "data_type": row[2],
                    "is_nullable": row[3] == "YES",
                    "max_length": row[4],
                    "numeric_precision": row[5],
                    "numeric_scale": row[6],
                    "default_value": row[7],
                }
                for row in cursor.fetchall()
            ]
            return columns
        finally:
            cursor.close()

    async def discover_primary_keys(
        self, table_name: str, schema: str = "dbo"
    ) -> List[str]:
        """Discover primary key columns for a table where available."""
        conn = await self._connection_service.connect()
        cursor = conn.cursor()
        try:
            sql = (
                "SELECT kcu.COLUMN_NAME "
                "FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc "
                "JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu "
                "  ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME "
                "  AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA "
                "WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY' "
                "  AND tc.TABLE_SCHEMA = ? AND tc.TABLE_NAME = ? "
                "ORDER BY kcu.ORDINAL_POSITION"
            )
            cursor.execute(sql, (schema, table_name))
            return [row[0] for row in cursor.fetchall()]
        except Exception:
            # Lakehouse SQL endpoints may not enforce declarative PK constraints
            return []
        finally:
            cursor.close()

    async def get_table_row_count(
        self, table_name: str, schema: str = "dbo"
    ) -> Optional[int]:
        """Safely fetch row count for a table."""
        conn = await self._connection_service.connect()
        cursor = conn.cursor()
        try:
            # Sanitize identifier to prevent SQL injection
            clean_schema = schema.replace("]", "").replace("[", "")
            clean_table = table_name.replace("]", "").replace("[", "")
            sql = f"SELECT COUNT(*) FROM [{clean_schema}].[{clean_table}]"
            cursor.execute(sql)
            row = cursor.fetchone()
            return int(row[0]) if row else 0
        except Exception as exc:
            log.warning("row_count_failed", table=table_name, error=str(exc))
            return None
        finally:
            cursor.close()

    async def generate_schema_json(
        self, output_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Discover complete database schema and write to fabric_schema.json.

        Args:
            output_path: Target path for the JSON file. Defaults to
                         backend/app/database/fabric_schema.json.

        Returns:
            Dict containing full schema metadata.
        """
        target_path = output_path or DEFAULT_SCHEMA_PATH
        schemas = await self.discover_schemas()
        tables = await self.discover_tables()

        schema_doc: Dict[str, Any] = {
            "database": self._connection_service._settings.fabric_database,
            "server": self._connection_service._settings.fabric_server,
            "discovered_at": None,
            "schemas": schemas,
            "tables": [],
            "gold_analytics": {},
        }

        import time

        schema_doc["discovered_at"] = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
        )

        for tbl in tables:
            s_name = tbl["schema"]
            t_name = tbl["name"]
            columns = await self.discover_columns(t_name, schema=s_name)
            pks = await self.discover_primary_keys(t_name, schema=s_name)
            row_count = await self.get_table_row_count(t_name, schema=s_name)

            table_meta = {
                "schema": s_name,
                "name": t_name,
                "full_name": f"[{s_name}].[{t_name}]",
                "type": tbl["type"],
                "row_count": row_count,
                "column_count": len(columns),
                "primary_keys": pks,
                "columns": columns,
            }
            schema_doc["tables"].append(table_meta)

            # Check if this table matches any Gold analytics category
            self._categorize_gold_table(table_meta, schema_doc["gold_analytics"])

        # Write to JSON file
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(schema_doc, f, indent=2)

        log.info(
            "schema_json_saved",
            path=str(target_path),
            table_count=len(schema_doc["tables"]),
        )
        return schema_doc

    def _categorize_gold_table(
        self, table: Dict[str, Any], gold_map: Dict[str, Any]
    ) -> None:
        """Map discovered table to the 5 documented Gold analytics datasets if matching."""
        name = table["name"].lower()
        cnt = table["row_count"] or 0

        # Dataset 1: Daily weather analytics (~11,666 records)
        if "daily" in name or (10000 <= cnt <= 15000):
            gold_map["daily_weather"] = table["name"]
        # Dataset 2: Monthly weather analytics (~418 records)
        elif "monthly" in name or ("month" in name and (350 <= cnt <= 500)):
            gold_map["monthly_weather"] = table["name"]
        # Dataset 3: Rainfall analytics (~418 records)
        elif "rain" in name and ("analytics" in name or "monthly" in name or (350 <= cnt <= 500)):
            gold_map["rainfall"] = table["name"]
        # Dataset 4: Latest current weather (~38 records)
        elif "current" in name or (cnt == 38 and "weather" in name):
            gold_map["current_weather"] = table["name"]
        # Dataset 5: Latest air quality (~38 records)
        elif "air" in name or "aqi" in name or (cnt == 38 and "quality" in name):
            gold_map["air_quality"] = table["name"]

    def load_cached_schema(
        self, schema_path: Optional[Path] = None
    ) -> Optional[Dict[str, Any]]:
        """Load previously discovered schema from JSON file if available."""
        path = schema_path or DEFAULT_SCHEMA_PATH
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as exc:
                log.warning("cached_schema_read_failed", error=str(exc))
        return None
