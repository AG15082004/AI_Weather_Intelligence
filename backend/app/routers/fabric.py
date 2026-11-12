"""Fabric router — connection verification, health monitoring, and schema discovery.

Provides endpoints to verify Microsoft Fabric connectivity, inspect schema,
and execute data integrity validations.
"""

from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from app.services.fabric_connection import FabricConnectionService
from app.services.fabric_data_validator import FabricDataValidator
from app.services.fabric_schema_service import FabricSchemaService

router = APIRouter(prefix="/fabric", tags=["fabric"])
log = structlog.get_logger()

fabric_conn = FabricConnectionService()
schema_svc = FabricSchemaService(fabric_conn)
validator = FabricDataValidator(fabric_conn, schema_svc)


class FabricHealthResponse(BaseModel):
    """Response model for Fabric health check."""

    status: str
    connected: bool
    query_status: Optional[int] = None
    latency_ms: Optional[float] = None
    timestamp: Optional[str] = None
    details: Dict[str, Any]
    error: Optional[str] = None
    error_type: Optional[str] = None
    diagnosis: Optional[str] = None


@router.get("/health", response_model=FabricHealthResponse)
async def fabric_health(response: Response):
    """Verify Fabric SQL connection by executing 'SELECT 1 AS connection_status'.

    Does NOT report a successful connection unless an actual SQL query succeeds.
    Returns status 200 on success, or 503 Service Unavailable on failure,
    with meaningful error diagnostics and zero secret leakage.
    """
    log.info("fabric_health_check_requested")
    result = await fabric_conn.verify_connection()

    if not result.get("connected"):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return result


@router.get("/schema")
async def get_fabric_schema():
    """Return the discovered Fabric Lakehouse schema.

    Returns the cached schema from fabric_schema.json if available,
    otherwise dynamically discovers and persists it.
    """
    cached = schema_svc.load_cached_schema()
    if cached:
        return {"status": "success", "source": "cached", "schema": cached}

    try:
        discovered = await schema_svc.generate_schema_json()
        return {"status": "success", "source": "live_discovery", "schema": discovered}
    except Exception as exc:
        log.error("schema_endpoint_failed", error=str(exc))
        return {
            "status": "error",
            "message": "Fabric schema discovery failed. Check Fabric connection and permissions.",
            "error": str(exc),
            "details": fabric_conn.get_safe_summary(),
        }


@router.post("/discover")
async def trigger_schema_discovery():
    """Trigger a live schema discovery against Microsoft Fabric Lakehouse.

    Inspects all tables, columns, data types, constraints, and row counts,
    and updates backend/app/database/fabric_schema.json.
    """
    log.info("live_schema_discovery_triggered")
    try:
        schema = await schema_svc.generate_schema_json()
        return {
            "status": "success",
            "table_count": len(schema.get("tables", [])),
            "schema": schema,
        }
    except Exception as exc:
        log.error("live_schema_discovery_failed", error=str(exc))
        return {
            "status": "error",
            "message": "Live schema discovery failed.",
            "error": str(exc),
            "details": fabric_conn.get_safe_summary(),
        }


@router.get("/validate")
async def validate_fabric_data():
    """Run data integrity validation against discovered Fabric Gold tables.

    Validates accessibility, record counts, district coverage, date ranges,
    NULL percentages, and compares against documented Fabric platform statistics.
    """
    log.info("fabric_data_validation_requested")
    try:
        report = await validator.validate_all_tables()
        return {"status": "success", "report": report}
    except Exception as exc:
        log.error("fabric_validation_failed", error=str(exc))
        return {
            "status": "error",
            "message": "Data validation failed.",
            "error": str(exc),
            "details": fabric_conn.get_safe_summary(),
        }


@router.get("/status")
async def fabric_status():
    """Return current Fabric configuration status and parameters without secrets."""
    return {
        "status": "configured" if fabric_conn._settings.fabric_server else "unconfigured",
        "summary": fabric_conn.get_safe_summary(),
    }

