"""AI router — natural-language weather intelligence powered by local Qwen3:4b and Fabric Lakehouse.

Provides conversational weather insights, entity-extracted analytics,
period comparisons, and structured chart recommendations.
"""

from typing import Any, Dict, Optional
import structlog
from fastapi import APIRouter

from app.schemas.ai import AIChatRequest, AIChatResponse
from app.services.ai_service import AIService
from app.services.session_memory import session_manager

router = APIRouter(prefix="/ai", tags=["ai"])
log = structlog.get_logger()
ai_service = AIService()


@router.post("/query", response_model=AIChatResponse)
@router.post("/chat", response_model=AIChatResponse)
async def ai_query_endpoint(request: AIChatRequest):
    """Process a natural-language weather query using the AI Intelligence Agent.

    Extracts user intent, resolves districts and date windows,
    retrieves verified Fabric Lakehouse data, and returns a grounded response.
    """
    prompt = request.prompt_text
    log.info("ai_agent_query_received", prompt=prompt, conversation_id=request.conversation_id)

    res = await ai_service.generate_response(
        query=prompt,
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
    ollama_health = await ai_service.generator.check_ollama_health()
    return {
        "status": "healthy",
        "service": "AI Weather Intelligence Agent",
        "ollama": ollama_health,
        "active_sessions": session_manager.active_sessions_count(),
    }
