"""TN Weather Intelligence API — FastAPI application entry point.

Provides weather data, analytics, and AI-powered insights
for all 38 districts of Tamil Nadu.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
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
)

settings = get_settings()

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
    log.info("application_startup", title="TN Weather Intelligence API")
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

# CORS middleware — origins driven by env
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers — all under /api
# ---------------------------------------------------------------------------
app.include_router(overview.router, prefix="/api")
app.include_router(temperature.router, prefix="/api")
app.include_router(rainfall.router, prefix="/api")
app.include_router(districts.router, prefix="/api")
app.include_router(current_weather.router, prefix="/api")
app.include_router(air_quality.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(dashboard_builder.router, prefix="/api")
app.include_router(fabric.router, prefix="/api")
app.include_router(historical.router, prefix="/api")


# ---------------------------------------------------------------------------
# Health check & Schema Discovery
# ---------------------------------------------------------------------------
@app.get("/api/health", tags=["health"])
async def health_check():
    """Return service health status."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "TN Weather Intelligence API",
        "version": "1.0.0",
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
