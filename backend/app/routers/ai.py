"""AI router — natural-language weather intelligence powered by local Qwen3:4b and Fabric Lakehouse.

Provides conversational weather insights, entity-extracted analytics,
period comparisons, and structured chart recommendations.
"""

from typing import Any, Dict, Optional
import structlog
from fastapi import APIRouter, HTTPException, Request

from app.schemas.ai import AIChatRequest, AIChatResponse
from app.services.ai_service import AIService
from app.services.rate_limiter import ai_rate_limiter
from app.services.session_memory import session_manager
from app.utils.security import sanitize_query

router = APIRouter(prefix="/ai", tags=["ai"])
log = structlog.get_logger()
ai_service = AIService()


@router.post("/query", response_model=AIChatResponse)
@router.post("/chat", response_model=AIChatResponse)
async def ai_query_endpoint(request: AIChatRequest, raw_request: Request):
    """Process a natural-language weather query using the AI Intelligence Agent.

    Extracts user intent, resolves districts and date windows,
    retrieves verified Fabric Lakehouse data, and returns a grounded response.
    Enforces rate limits and input sanitization.
    """
    # 1. Rate limiting check per client IP
    client_ip = (
        raw_request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (raw_request.client.host if raw_request.client else "127.0.0.1")
    )
    allowed, remaining, retry_after = ai_rate_limiter.is_allowed(
        client_ip, limit=ai_service.settings.ai_rate_limit_per_minute
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {ai_service.settings.ai_rate_limit_per_minute} AI requests per minute.",
            headers={
                "Retry-After": str(int(retry_after) + 1),
                "X-RateLimit-Limit": str(ai_service.settings.ai_rate_limit_per_minute),
                "X-RateLimit-Remaining": "0",
            },
        )

    # 2. Input validation and length check
    raw_prompt = request.prompt_text
    if not raw_prompt:
        raise HTTPException(status_code=400, detail="AI query message cannot be empty.")

    if len(raw_prompt) > 1000:
        raise HTTPException(
            status_code=400,
            detail=f"AI query length ({len(raw_prompt)}) exceeds limit of 1000 characters.",
        )

    clean_prompt = sanitize_query(raw_prompt) or raw_prompt

    log.info(
        "ai_agent_query_received",
        prompt=clean_prompt[:80],
        conversation_id=request.conversation_id,
        client_ip=client_ip,
        remaining_quota=remaining,
    )

    res = await ai_service.generate_response(
        query=clean_prompt,
        context=request.context,
        conversation_id=request.conversation_id,
        district_override=request.district,
        start_date_override=request.start_date,
        end_date_override=request.end_date,
    )
    return res


@router.delete("/session/{conversation_id}")
async def clear_session_endpoint(conversation_id: str):
    """Clear memory context for a specific conversation session."""
    session_manager.clear_session(conversation_id)
    return {"status": "success", "message": f"Session {conversation_id} cleared"}


@router.get("/health")
async def ai_health_endpoint():
    """Health check for AI engine, Ollama service, and Fabric connectivity."""
    active_provider, provider_reason = await ai_service.generator.resolve_ai_provider()
    ollama_health = await ai_service.generator.check_ollama_health()
    return {
        "status": "healthy",
        "service": "AI Weather Intelligence Agent",
        "active_provider": active_provider,
        "provider_reason": provider_reason,
        "ollama": ollama_health,
        "active_sessions": session_manager.active_sessions_count(),
    }
