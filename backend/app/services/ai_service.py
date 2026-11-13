"""AI Weather Intelligence Agent Service.

Orchestrates natural language understanding (intent classification, entity extraction),
conversational memory (follow-up context resolution),
Fabric data-grounded query routing, structured chart generation,
and factually grounded explanations powered by Qwen3:4b.
"""

from datetime import date
import time
from typing import Any, Dict, List, Optional
import structlog

from app.config import get_settings
from app.schemas.ai import AIChatRequest, AIChatResponse, ChartSpec, ExtractedIntent
from app.services.grounded_response_generator import GroundedResponseGenerator
from app.services.openai_provider import openai_provider
from app.services.metrics_service import metrics_service
from app.services.session_memory import session_manager
from app.services.weather_agent_router import WeatherAgentRouter
from app.utils.date_extractor import extract_date_range
from app.utils.district_extractor import ALL_TN_DISTRICTS, extract_districts, extract_single_district
from app.utils.intent_classifier import classify_intent_rule_based

log = structlog.get_logger()


class AIService:
    """Enterprise AI Weather Intelligence Agent for Tamil Nadu."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.router = WeatherAgentRouter()
        self.generator = GroundedResponseGenerator()
        self.openai_provider = openai_provider

    async def detect_intent(self, query: str) -> str:
        """Fast intent detection based on the 15 supported intents."""
        extracted = classify_intent_rule_based(query)
        return extracted.intent

    async def extract_district(self, query: str) -> Optional[str]:
        """Extract a single canonical Tamil Nadu district name."""
        return extract_single_district(query)

    async def extract_districts_list(self, query: str) -> List[str]:
        """Extract all mentioned Tamil Nadu districts."""
        return extract_districts(query)

    async def extract_dates(self, query: str) -> Dict[str, Optional[str]]:
        """Extract date references resolved to ISO date strings."""
        spec = extract_date_range(query)
        return {
            "start_date": str(spec.start_date) if spec.start_date else None,
            "end_date": str(spec.end_date) if spec.end_date else None,
            "preset": spec.preset,
        }

    async def generate_response(
        self,
        query: str,
        context: Optional[str] = None,
        conversation_id: Optional[str] = None,
        district_override: Optional[str] = None,
        start_date_override: Optional[date] = None,
        end_date_override: Optional[date] = None,
    ) -> Dict[str, Any]:
        """End-to-end agent invocation for a natural-language user query."""
        clean_q = (query or "").strip()
        if not clean_q:
            return {
                "answer": "Please ask a question about weather across Tamil Nadu's 38 districts.",
                "response": "Please ask a question about weather across Tamil Nadu's 38 districts.",
                "intent": "unknown_intent",
                "district": None,
                "confidence": 0.0,
                "conversation_id": conversation_id or "default",
                "sources": [],
                "applied_filters": {},
                "follow_up_suggestions": [
                    "What is the weather across Tamil Nadu today?",
                    "Which district is the hottest right now?",
                ],
            }

        # 1. Retrieve or create conversational session
        session = session_manager.get_or_create(conversation_id)

        # 2. Extract intent and parameters
        extracted = classify_intent_rule_based(clean_q)

        # Apply any explicit API overrides
        if district_override:
            extracted.district = district_override
            if district_override not in extracted.districts:
                extracted.districts.append(district_override)
        if start_date_override:
            extracted.date_range.start_date = start_date_override
            extracted.date_range.is_explicit = True
        if end_date_override:
            extracted.date_range.end_date = end_date_override
            extracted.date_range.is_explicit = True

        # 3. Resolve follow-up references using session memory
        extracted = session.resolve_follow_up(extracted)
        log.info(
            "ai_intent_classified",
            intent=extracted.intent,
            metric=extracted.metric,
            district=extracted.district,
            districts=extracted.districts,
            preset=extracted.date_range.preset,
            start=str(extracted.date_range.start_date),
            end=str(extracted.date_range.end_date),
        )

        # 4. Route intent to verified Fabric Lakehouse queries
        try:
            query_result = await self.router.execute_intent(extracted)
        except Exception as exc:
            log.error("fabric_query_routing_failed", error=str(exc))
            query_result = {
                "source": "Microsoft Fabric Lakehouse",
                "error": str(exc),
                "data": [],
                "data_status": "UNAVAILABLE",
                "data_source": "none",
                "is_stale": True,
                "observation_timestamp": "Unavailable",
            }

        # 5. Generate grounded natural-language answer & follow-up suggestions
        ai_gen_start = time.perf_counter()
        answer_text, suggestions = await self.generator.generate_answer(
            query=clean_q,
            extracted=extracted,
            query_result=query_result,
            session_history=session.history,
        )
        gen_duration_ms = round((time.perf_counter() - ai_gen_start) * 1000, 2)
        active_prov, _ = await self.generator.resolve_ai_provider()
        metrics_service.record_ai_query(provider=active_prov, duration_ms=gen_duration_ms, success=True)

        # 6. Update conversational memory
        session.update(extracted, clean_q, answer_text)

        # 7. Extract chart specification if produced
        chart_obj = query_result.get("chart")
        chart_dict = chart_obj.model_dump() if isinstance(chart_obj, ChartSpec) else None

        # Build response payload
        res = {
            "conversation_id": session.conversation_id,
            "answer": answer_text,
            "response": answer_text,  # For backwards compatibility
            "intent": extracted.intent,
            "district": extracted.district,
            "districts": extracted.districts,
            "confidence": extracted.confidence,
            "sources": [query_result.get("source", "Microsoft Fabric Lakehouse")],
            "applied_filters": {
                "district": extracted.district,
                "districts": extracted.districts,
                "preset": extracted.date_range.preset,
                "start_date": str(extracted.date_range.start_date) if extracted.date_range.start_date else None,
                "end_date": str(extracted.date_range.end_date) if extracted.date_range.end_date else None,
            },
            "observation_timestamp": query_result.get("observation_timestamp"),
            "data_summary": {
                "metric": extracted.metric,
                "aggregation": extracted.aggregation,
                "rankings_count": len(query_result.get("rankings", [])),
                "data_points": len(query_result.get("data", [])),
            },
            "chart": chart_dict,
            "data_status": query_result.get("data_status", "LIVE"),
            "data_source": query_result.get("data_source", "microsoft_fabric"),
            "is_stale": query_result.get("is_stale", False),
            "warning": query_result.get("warning"),
            "follow_up_suggestions": suggestions,
        }
        return res
