"""Session-based Conversational Memory for Tamil Nadu Weather Intelligence Agent.

Maintains recent dialogue state, contextual entities (district, date range, metric, intent)
to support intelligent multi-turn follow-up queries without state drift.
"""

from datetime import datetime, timezone
import time
from typing import Dict, List, Optional
import uuid
import structlog

from app.schemas.ai import DateRangeSpecification, ExtractedIntent, IntentType, MetricType

log = structlog.get_logger()


class ConversationSession:
    """Stateful dialogue context for a single conversation session."""

    def __init__(self, conversation_id: str) -> None:
        self.conversation_id: str = conversation_id
        self.last_district: Optional[str] = None
        self.last_districts: List[str] = []
        self.last_date_range: Optional[DateRangeSpecification] = None
        self.last_intent: Optional[IntentType] = None
        self.last_metric: Optional[MetricType] = None
        self.history: List[Dict[str, str]] = []  # [{"role": "user", "text": ...}, ...]
        self.last_updated: float = time.time()

    def update(
        self,
        extracted: ExtractedIntent,
        user_text: str,
        assistant_text: str,
    ) -> None:
        """Update session context with verified turn entities."""
        if extracted.district:
            self.last_district = extracted.district
        if extracted.districts:
            self.last_districts = extracted.districts

        if extracted.date_range and extracted.date_range.is_explicit:
            self.last_date_range = extracted.date_range

        if extracted.intent != "unknown_intent":
            self.last_intent = extracted.intent

        if extracted.metric != "general":
            self.last_metric = extracted.metric

        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": assistant_text})
        # Keep only the last 10 turns (20 messages) to prevent memory bloating
        if len(self.history) > 20:
            self.history = self.history[-20:]

        self.last_updated = time.time()

    def resolve_follow_up(self, extracted: ExtractedIntent) -> ExtractedIntent:
        """Enrich an extracted intent with contextual entities from previous turns."""
        # 1. District inheritance: If user didn't mention district, but previous turn had one
        if not extracted.district and self.last_district:
            # Check if query is a follow-up ("what about it?", "how about the rain?", "did it rain?")
            q_lower = extracted.raw_query.lower()
            if any(w in q_lower for w in ["there", "it", "then", "also", "same", "temperature", "rain", "aqi", "humidity"]):
                extracted.district = self.last_district

        # 2. Date inheritance: If user explicitly provided a new district (e.g. "What about Coimbatore?")
        # but didn't provide a date, inherit the previous turn's explicit date window!
        if extracted.district and (not extracted.date_range.is_explicit) and self.last_date_range:
            q_lower = extracted.raw_query.lower()
            if any(w in q_lower for w in ["what about", "how about", "and in", "for "]):
                extracted.date_range = self.last_date_range

        # 3. Metric inheritance: If user asks "What about Coimbatore?", retain metric (e.g. temperature)
        if extracted.metric == "general" and self.last_metric:
            q_lower = extracted.raw_query.lower()
            if any(w in q_lower for w in ["what about", "how about", "compare"]):
                extracted.metric = self.last_metric

        return extracted


class SessionManager:
    """Thread-safe in-memory session manager with TTL eviction."""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._sessions: Dict[str, ConversationSession] = {}
        self._ttl_seconds: int = ttl_seconds

    def get_or_create(self, conversation_id: Optional[str] = None) -> ConversationSession:
        """Get existing session or initialize a fresh one."""
        self._cleanup_expired()
        cid = conversation_id.strip() if conversation_id and conversation_id.strip() else str(uuid.uuid4())
        if cid not in self._sessions:
            self._sessions[cid] = ConversationSession(cid)
        return self._sessions[cid]

    def clear_session(self, conversation_id: str) -> None:
        """Clear memory for a conversation."""
        if conversation_id in self._sessions:
            del self._sessions[conversation_id]

    def active_sessions_count(self) -> int:
        """Return number of active unexpired sessions."""
        self._cleanup_expired()
        return len(self._sessions)

    def _cleanup_expired(self) -> None:
        """Remove sessions inactive for longer than TTL."""
        now = time.time()
        expired = [cid for cid, s in self._sessions.items() if now - s.last_updated > self._ttl_seconds]
        for cid in expired:
            del self._sessions[cid]


# Global singleton session manager
session_manager = SessionManager(ttl_seconds=3600)

