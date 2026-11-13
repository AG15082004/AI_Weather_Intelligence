"""Parameterized SQL query executor.

Provides safe, parameterized query execution against the Fabric SQL
database with error handling and structured logging.
"""

import time
from typing import Any, Dict, List, Optional, Tuple

import pyodbc
import structlog

from app.config import get_settings
from app.database.connection import get_pool
from app.services.metrics_service import metrics_service

log = structlog.get_logger()


class FabricDatabaseError(Exception):
    """Base exception for Fabric database errors."""
    pass


class FabricTimeoutError(FabricDatabaseError):
    """Fabric SQL execution or connection timeout."""
    pass


class FabricAuthenticationError(FabricDatabaseError):
    """Fabric SQL authentication failure."""
    pass


class FabricConnectionError(FabricDatabaseError):
    """Fabric SQL connection failure or service unavailable."""
    pass


def classify_db_error(exc: Exception) -> Exception:
    """Classify pyodbc database errors into meaningful semantic exceptions."""
    err_str = str(exc).lower()
    if "hyt00" in err_str or "query timeout" in err_str or "timeout expired" in err_str:
        return FabricTimeoutError(f"Microsoft Fabric SQL query timed out: {exc}")
    if "login timeout" in err_str or "08001" in err_str or "08s01" in err_str or "10060" in err_str:
        return FabricConnectionError(f"Microsoft Fabric connection failed or service is temporarily unavailable: {exc}")
    if "28000" in err_str or "fa004" in err_str or "login failed" in err_str or "token" in err_str:
        return FabricAuthenticationError(f"Microsoft Fabric Entra authentication failed: {exc}")
    return exc


class QueryExecutor:
    """Execute parameterized SQL queries safely.

    All queries MUST use parameterized placeholders (?) to prevent
    SQL injection. Direct string interpolation is never used.
    """

    def __init__(self) -> None:
        self._pool = get_pool()
        settings = get_settings()
        self._query_timeout = getattr(settings, "fabric_query_timeout", 25)

    async def execute_query(
        self,
        sql: str,
        params: Optional[Tuple[Any, ...]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results as list of dicts.

        Args:
            sql: Parameterized SQL query string using ? placeholders.
            params: Tuple of parameter values to bind.

        Returns:
            List of result rows as dicts keyed by column name.

        Raises:
            FabricDatabaseError / pyodbc.Error: On database errors.
        """
        start_time = time.perf_counter()
        cursor = None
        try:
            conn = await self._pool.get_connection()
            try:
                conn.timeout = self._query_timeout
            except Exception:
                pass
            cursor = conn.cursor()

            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)

            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()

            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            results = [dict(zip(columns, row)) for row in rows]
            metrics_service.record_fabric_query(success=True, duration_ms=duration_ms)
            log.info(
                "query_executed",
                row_count=len(results),
                column_count=len(columns),
                duration_ms=duration_ms,
            )
            return results

        except (pyodbc.Error, Exception) as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            metrics_service.record_fabric_query(success=False, duration_ms=duration_ms)
            classified = classify_db_error(exc)
            log.error(
                "query_execution_failed",
                sql=sql[:100],
                duration_ms=duration_ms,
                error_type=type(classified).__name__,
                error=str(exc),
            )
            raise classified from exc
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass

    async def execute_scalar(
        self,
        sql: str,
        params: Optional[Tuple[Any, ...]] = None,
    ) -> Optional[Any]:
        """Execute a query and return the first column of the first row.

        Args:
            sql: Parameterized SQL query string using ? placeholders.
            params: Tuple of parameter values to bind.

        Returns:
            Scalar value, or None if no rows returned.
        """
        start_time = time.perf_counter()
        cursor = None
        try:
            conn = await self._pool.get_connection()
            try:
                conn.timeout = self._query_timeout
            except Exception:
                pass
            cursor = conn.cursor()

            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)

            row = cursor.fetchone()
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            result = row[0] if row else None
            metrics_service.record_fabric_query(success=True, duration_ms=duration_ms)
            log.info("scalar_query_executed", has_result=result is not None, duration_ms=duration_ms)
            return result

        except (pyodbc.Error, Exception) as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            metrics_service.record_fabric_query(success=False, duration_ms=duration_ms)
            classified = classify_db_error(exc)
            log.error(
                "scalar_query_failed",
                sql=sql[:100],
                duration_ms=duration_ms,
                error_type=type(classified).__name__,
                error=str(exc),
            )
            raise classified from exc
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass

    async def execute_non_query(
        self,
        sql: str,
        params: Optional[Tuple[Any, ...]] = None,
    ) -> int:
        """Execute an INSERT/UPDATE/DELETE and return rows affected.

        Args:
            sql: Parameterized SQL statement using ? placeholders.
            params: Tuple of parameter values to bind.

        Returns:
            Number of rows affected.
        """
        try:
            conn = await self._pool.get_connection()
            cursor = conn.cursor()

            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)

            affected = cursor.rowcount
            conn.commit()
            cursor.close()

            log.info("non_query_executed", rows_affected=affected)
            return affected

        except pyodbc.Error as exc:
            log.error("non_query_failed", sql=sql[:100], error=str(exc))
            raise
