"""Dashboard builder router — AI-powered dashboard generation.

Provides endpoints for creating and managing custom dashboards.
"""

from typing import Optional

import structlog
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
log = structlog.get_logger()
dashboard_service = DashboardService()


class DashboardRequest(BaseModel):
    """Request body for dashboard generation."""

    prompt: str = Field(..., description="Natural-language dashboard description")
    districts: Optional[list[str]] = Field(None, description="Districts to include")


@router.post("/generate")
async def generate_dashboard(request: DashboardRequest):
    """Generate a custom dashboard layout from a natural-language prompt.

    Uses AI to interpret the user's request and produce a dashboard
    configuration with appropriate chart types and data bindings.
    """
    log.info("dashboard_generate_requested", prompt=request.prompt)
    return await dashboard_service.generate_dashboard(
        prompt=request.prompt, districts=request.districts
    )


@router.get("/presets")
async def list_presets():
    """List available pre-built dashboard configurations.

    Returns a collection of ready-to-use dashboard templates
    covering common weather monitoring scenarios.
    """
    log.info("dashboard_presets_requested")
    return await dashboard_service.list_presets()
