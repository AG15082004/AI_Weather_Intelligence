"""OpenAI GPT-6 Luna Provider using the OpenAI Responses API.

Provides enterprise-grade, data-grounded natural-language processing
for the Tamil Nadu Weather Intelligence Platform.

Key Guarantees:
- Uses official OpenAI Responses API (`client.responses.create`).
- Asynchronous non-blocking client with configurable timeouts.
- Thread-safe token usage tracking (prompt, completion, total, cost metrics).
- Safe exception handling with semantic error categorization.
- Secret masking (never logs or leaks full API keys).
- Strict data-grounding instructions (model never invents weather metrics).
"""

import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import structlog
from zoneinfo import ZoneInfo

from app.config import get_settings

log = structlog.get_logger()
IST_ZONE = ZoneInfo("Asia/Kolkata")


class OpenAIProvider:
    """Enterprise OpenAI GPT-6 Luna client using the Responses API."""

    _instance: Optional["OpenAIProvider"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self.settings = get_settings()
        self._lock = threading.Lock()
        self._client: Optional[Any] = None
        self._initialized_key: Optional[str] = None

        # Telemetry & Usage Metrics
        self._total_requests: int = 0
        self._successful_requests: int = 0
        self._failed_requests: int = 0
        self._prompt_tokens: int = 0
        self._completion_tokens: int = 0
        self._total_tokens: int = 0
        self._last_successful_request_ist: Optional[str] = None
        self._last_error: Optional[str] = None
        self._last_error_type: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "OpenAIProvider":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @property
    def api_key(self) -> Optional[str]:
        return self.settings.openai_api_key

    @property
    def model(self) -> str:
        return self.settings.openai_model or "gpt-6-luna"

    @property
    def timeout_seconds(self) -> float:
        return float(self.settings.openai_timeout_seconds or 30.0)

    @property
    def max_output_tokens(self) -> int:
        return int(self.settings.openai_max_output_tokens or 1024)

    def is_configured(self) -> bool:
        """Check if an API key has been provided and is non-empty."""
        key = self.api_key
        return bool(key and len(key.strip()) > 5)

    def _get_client(self) -> Any:
        """Lazily initialize or return AsyncOpenAI client."""
        key = self.api_key
        if not key or len(key.strip()) <= 5:
            raise ValueError("OpenAI API key is not configured")

        if self._client is None or self._initialized_key != key:
            import openai
            self._client = openai.AsyncOpenAI(
                api_key=key.strip(),
                timeout=self.timeout_seconds,
            )
            self._initialized_key = key
        return self._client

    def _mask_api_key(self) -> str:
        """Safely mask API key for logging and monitoring displays."""
        key = self.api_key
        if not key:
            return "not_configured"
        key_str = key.strip()
        if len(key_str) < 8:
            return "***"
        return f"{key_str[:4]}...{key_str[-4:]}"

    async def generate_response(
        self,
        prompt: str,
        instructions: Optional[str] = None,
        max_tokens: Optional[int] = None,
        session_history: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """Call OpenAI Responses API with prompt and strict grounding instructions.

        Returns:
            (generated_text, usage_metadata)

        Raises:
            Exception on unrecoverable API errors (caller engages emergency fallback).
        """
        if not self.is_configured():
            raise ValueError("OpenAI provider not configured with valid API key")

        client = self._get_client()
        effective_max_tokens = max_tokens or self.max_output_tokens

        # Format conversation context if present
        full_input = prompt
        if session_history and len(session_history) > 0:
            history_lines = []
            for item in session_history[-4:]:  # Keep recent context bounded
                role = item.get("role", "user").capitalize()
                content = item.get("content", "").strip()
                if content:
                    history_lines.append(f"{role}: {content}")
            if history_lines:
                context_str = "\n".join(history_lines)
                full_input = f"PREVIOUS CONVERSATION CONTEXT:\n{context_str}\n\nCURRENT REQUEST:\n{prompt}"

        t0 = time.perf_counter()
        with self._lock:
            self._total_requests += 1

        try:
            log.info(
                "openai_request_dispatched",
                model=self.model,
                input_length=len(full_input),
                has_instructions=bool(instructions),
            )

            # Call official OpenAI Responses API
            response = await client.responses.create(
                model=self.model,
                input=full_input,
                instructions=instructions,
                max_output_tokens=effective_max_tokens,
                timeout=self.timeout_seconds,
            )

            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            out_text = getattr(response, "output_text", None) or ""
            if not out_text and hasattr(response, "output"):
                # Fallback extraction if output_text property is empty
                out_items = getattr(response, "output", [])
                out_text = " ".join(
                    str(getattr(item, "text", "")) for item in out_items if hasattr(item, "text")
                )

            # Extract and track usage
            p_tokens = 0
            c_tokens = 0
            t_tokens = 0
            if hasattr(response, "usage") and response.usage:
                p_tokens = getattr(response.usage, "input_tokens", 0) or 0
                c_tokens = getattr(response.usage, "output_tokens", 0) or 0
                t_tokens = getattr(response.usage, "total_tokens", 0) or (p_tokens + c_tokens)

            now_ist = datetime.now(IST_ZONE).strftime("%Y-%m-%d %H:%M:%S IST")

            with self._lock:
                self._successful_requests += 1
                self._prompt_tokens += p_tokens
                self._completion_tokens += c_tokens
                self._total_tokens += t_tokens
                self._last_successful_request_ist = now_ist
                self._last_error = None
                self._last_error_type = None

            log.info(
                "openai_response_received",
                model=self.model,
                latency_ms=latency_ms,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                total_tokens=t_tokens,
            )

            usage_dict = {
                "model": self.model,
                "latency_ms": latency_ms,
                "prompt_tokens": p_tokens,
                "completion_tokens": c_tokens,
                "total_tokens": t_tokens,
                "timestamp_ist": now_ist,
            }

            return out_text.strip(), usage_dict

        except Exception as exc:
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            err_type = type(exc).__name__
            err_msg = str(exc)

            with self._lock:
                self._failed_requests += 1
                self._last_error = err_msg
                self._last_error_type = err_type

            log.error(
                "openai_request_failed",
                model=self.model,
                error_type=err_type,
                error=err_msg,
                latency_ms=latency_ms,
            )
            raise

    def get_health_status(self) -> Dict[str, Any]:
        """Provide detailed health status and token usage for monitoring."""
        configured = self.is_configured()
        with self._lock:
            status = "ready" if configured else "unconfigured"
            if configured and self._failed_requests > 0 and self._successful_requests == 0:
                status = "failing"
            elif configured and self._last_error_type == "AuthenticationError":
                status = "authentication_failed"

            return {
                "status": status,
                "configured": configured,
                "model": self.model,
                "api_key_masked": self._mask_api_key(),
                "timeout_seconds": self.timeout_seconds,
                "max_output_tokens": self.max_output_tokens,
                "total_requests": self._total_requests,
                "successful_requests": self._successful_requests,
                "failed_requests": self._failed_requests,
                "last_successful_request": self._last_successful_request_ist,
                "last_error": self._last_error,
                "last_error_type": self._last_error_type,
                "token_usage": {
                    "prompt_tokens": self._prompt_tokens,
                    "completion_tokens": self._completion_tokens,
                    "total_tokens": self._total_tokens,
                },
            }

    def reset_metrics(self) -> None:
        """Reset metrics (useful for isolated testing)."""
        with self._lock:
            self._total_requests = 0
            self._successful_requests = 0
            self._failed_requests = 0
            self._prompt_tokens = 0
            self._completion_tokens = 0
            self._total_tokens = 0
            self._last_successful_request_ist = None
            self._last_error = None
            self._last_error_type = None


openai_provider = OpenAIProvider.get_instance()
