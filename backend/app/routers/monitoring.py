"""Operational Monitoring, Health Metrics, and Administrative Router.

Provides real-time system observability, Fabric query performance statistics,
data freshness tracking, and protected administrative operations.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Header, HTTPException, status
import structlog

from app.config import get_settings
from app.services.ai_service import AIService
from app.services.metrics_service import metrics_service
from app.utils.cache import shared_cache
from app.utils.security import verify_admin_key

router = APIRouter(prefix="/monitoring", tags=["monitoring"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])
log = structlog.get_logger()
ai_service = AIService()


@router.get("/operational-status")
async def get_operational_status() -> Dict[str, Any]:
    """Retrieve operational telemetry for real-time frontend monitoring.

    Returns live status of Backend API, Microsoft Fabric Lakehouse,
    AI provider selection, and meteorological data freshness.
    Zero external dependencies and zero added hosting costs.
    """
    settings = get_settings()
    summary = metrics_service.get_summary()

    # AI Provider telemetry
    active_provider, provider_reason = await ai_service.generator.resolve_ai_provider()
    ollama_health = await ai_service.generator.check_ollama_health()

    return {
        "status": "healthy",
        "service": "TN Weather Intelligence Platform",
        "environment": settings.app_env,
        "uptime_seconds": summary["uptime_seconds"],
        "api": {
            "status": "healthy",
            "version": "1.0.0",
            "avg_latency_ms": summary["http_metrics"]["avg_duration_ms"],
        },
        "fabric": {
            "status": summary["fabric_metrics"]["status"],
            "total_queries": summary["fabric_metrics"]["total_queries"],
            "avg_latency_ms": summary["fabric_metrics"]["avg_duration_ms"],
            "last_query_timestamp": summary["fabric_metrics"]["last_query_timestamp"],
        },
        "ai": {
            "status": "healthy",
            "active_provider": active_provider,
            "provider_reason": provider_reason,
            "ollama_available": ollama_health.get("available", False),
            "avg_latency_ms": summary["ai_metrics"]["avg_duration_ms"],
        },
        "data_freshness": summary["data_freshness"],
    }


@router.get("/metrics")
async def get_system_metrics() -> Dict[str, Any]:
    """Return raw aggregated performance metrics."""
    return metrics_service.get_summary()


# ---------------------------------------------------------------------------
# Protected Administrative Operations
# ---------------------------------------------------------------------------

@admin_router.post("/clear-cache")
async def admin_clear_cache(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Purge in-memory API response cache.

    Protected operation: requires valid ADMIN_API_KEY when configured.
    """
    provided_key = x_api_key or authorization
    if not verify_admin_key(provided_key):
        log.warning("unauthorized_admin_cache_clear_attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid or missing administrator credentials.",
        )

    cleared_count = shared_cache.clear()
    log.info("admin_cache_cleared", cleared_keys_count=cleared_count)
    return {
        "status": "success",
        "message": f"Successfully cleared {cleared_count} cached entries.",
    }
