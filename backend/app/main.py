"""TN Weather Intelligence API — FastAPI application entry point.

Provides weather data, analytics, and AI-powered insights
for all 38 districts of Tamil Nadu.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.middleware.observability import ObservabilityMiddleware
from app.middleware.security import RequestSizeLimitMiddleware, SecurityHeadersMiddleware
from app.routers import (
    overview,
    temperature,
    rainfall,
    districts,
    current_weather,
    air_quality,
    ai,
    dashboard_builder,
    fabric,
    historical,
    monitoring,
)
from app.services.ai_service import AIService
from app.services.data_reliability_service import data_reliability_service
from app.services.metrics_service import metrics_service

settings = get_settings()
ai_service = AIService()

# ---------------------------------------------------------------------------
# Structured logging setup
# ---------------------------------------------------------------------------
log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(log_level),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

log = structlog.get_logger()


from app.utils.date_utils import validate_timezone_support

# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # 1. Validate timezone support (Asia/Kolkata) on startup
    validate_timezone_support()

    # 2. Validate Microsoft Fabric configuration safely on startup
    from app.services.fabric_connection import FabricConnectionService
    fabric_diag = FabricConnectionService(settings).validate_configuration()
    log.info(
        "application_startup",
        title="TN Weather Intelligence API",
        fabric_status=fabric_diag.get("status"),
        fabric_mode=fabric_diag.get("effective_auth_mode"),
    )
    yield
    log.info("application_shutdown")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="TN Weather Intelligence API",
    description=(
        "Weather data, analytics, and AI-powered insights "
        "for all 38 districts of Tamil Nadu."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Security headers (injected into all responses)
if settings.enable_security_headers:
    app.add_middleware(SecurityHeadersMiddleware)

# Request payload size guard
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_bytes=settings.max_request_body_bytes,
)

# Observability, X-Request-ID, duration tracking & error masking
app.add_middleware(ObservabilityMiddleware)

# CORS middleware — origins driven by env and regex for Render production domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)


@app.options("/{full_path:path}", include_in_schema=False)
async def options_catchall(full_path: str):
    """Fallback handler for direct non-CORS OPTIONS probes."""
    return Response(status_code=200)


@app.exception_handler(Exception)
async def global_unhandled_exception_handler(request: Request, exc: Exception):
    """Global exception handler guaranteeing JSON error schema and CORS header preservation."""
    log.error(
        "unhandled_application_exception",
        path=request.url.path,
        method=request.method,
        error_type=type(exc).__name__,
        error=str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "An internal server error occurred while processing your request.",
            "path": request.url.path,
        },
    )

# ---------------------------------------------------------------------------
# Routers — all under /api
# ---------------------------------------------------------------------------
app.include_router(overview.router, prefix="/api")
app.include_router(temperature.router, prefix="/api")
app.include_router(rainfall.router, prefix="/api")
app.include_router(districts.router, prefix="/api")
app.include_router(current_weather.router, prefix="/api")
app.include_router(current_weather.weather_current_router, prefix="/api")
app.include_router(air_quality.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(dashboard_builder.router, prefix="/api")
app.include_router(fabric.router, prefix="/api")
app.include_router(historical.router, prefix="/api")
app.include_router(monitoring.router, prefix="/api")
app.include_router(monitoring.admin_router, prefix="/api")


# ---------------------------------------------------------------------------
# Health check & Schema Discovery
# ---------------------------------------------------------------------------
@app.get("/", tags=["root"])
async def root():
    """Service root endpoint."""
    return {
        "service": "TN Weather Intelligence API",
        "status": "healthy",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health", tags=["health"])
async def health_check():
    """Return comprehensive multi-tier service health status.

    Evaluates:
      - FastAPI API core
      - Microsoft Fabric telemetry and connectivity state (cached, non-blocking)
      - AI Provider status (healthy via deterministic fallback even if Ollama offline)
      - Data freshness and district coverage
    """
    summary = metrics_service.get_summary()
    active_prov, prov_reason = await ai_service.generator.resolve_ai_provider()
    ollama_health = await ai_service.generator.check_ollama_health()

    fabric_status = summary["fabric_metrics"]["status"]
    
    # Global status evaluation:
    # 1. Distinguish API health from Fabric dependency health.
    # 2. Do not mark the overall API unhealthy merely because Fabric is deferred.
    # 3. Overall API is healthy when API core is functioning, even if Fabric is deferred.
    if fabric_status == "deferred":
        overall_status = "healthy"
    elif fabric_status == "unavailable":
        overall_status = "unavailable"
    elif fabric_status == "degraded":
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "TN Weather Intelligence API",
        "version": "1.0.0",
        "uptime_seconds": summary["uptime_seconds"],
        "components": {
            "api": {
                "status": "healthy",
                "avg_response_time_ms": summary["http_metrics"]["avg_duration_ms"],
            },
            "fabric": {
                "status": fabric_status,
                "total_queries": summary["fabric_metrics"]["total_queries"],
                "last_query_timestamp": summary["fabric_metrics"]["last_query_timestamp"],
                "avg_query_time_ms": summary["fabric_metrics"]["avg_duration_ms"],
            },
            "ai": {
                "status": "healthy",
                "active_provider": active_prov,
                "provider_reason": prov_reason,
                "ollama_available": ollama_health.get("available", False),
            },
            "data_freshness": summary["data_freshness"],
            "data_reliability": data_reliability_service.get_summary(),
        },
    }


@app.get("/api/schema", tags=["schema"])
async def get_schema():
    """Discover and return Microsoft Fabric Lakehouse schema."""
    from app.services.fabric_schema_service import FabricSchemaService
    schema_service = FabricSchemaService()
    try:
        schema = await schema_service.generate_schema_json()
        return {"status": "connected", "source": "fabric", "schema": schema}
    except Exception as exc:
        log.warning("schema_discovery_offline", error=str(exc))
        return {
            "status": "pending_connection",
            "message": "Fabric SQL endpoint not connected yet or credentials pending. Schema will be dynamically discovered upon connection.",
            "error": str(exc),
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["app"],
        reload_excludes=["venv/*", "*.pyc", "__pycache__/*", "*.log"],
    )
