"""Observability, Structured Logging, and Safe Exception Handling Middleware.

Ensures every HTTP request carries an X-Request-ID, logs structured audit events
with execution timing, updates real-time operational metrics,
and masks sensitive information from logs and error messages.
"""

from datetime import datetime, timezone
import time
from typing import Callable
import uuid
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from app.services.metrics_service import metrics_service
from app.utils.security import mask_secrets

log = structlog.get_logger()


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Instruments incoming HTTP requests with request tracing, timing, and error safety."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or generate X-Request-ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start_time = time.perf_counter()
        method = request.method
        path = request.url.path

        # Sanitize client IP
        client_host = request.client.host if request.client else "unknown"

        try:
            response: Response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Record telemetry
            metrics_service.record_request(
                path=path,
                method=method,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

            # Structured request logging
            log.info(
                "http_request_completed",
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
                request_id=request_id,
                method=method,
                path=path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                client_ip=client_host,
            )

            # Inject trace headers into response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time-Ms"] = str(duration_ms)
            return response

        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Record failure metric
            metrics_service.record_request(
                path=path,
                method=method,
                status_code=500,
                duration_ms=duration_ms,
            )

            # Log sanitized detailed exception internally
            log.error(
                "unhandled_server_exception",
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
                request_id=request_id,
                method=method,
                path=path,
                error_type=type(exc).__name__,
                error=mask_secrets(str(exc)),
                duration_ms=duration_ms,
                client_ip=client_host,
            )

            # Return sanitized client response with zero traceback or credential exposure
            safe_error = {
                "status": "error",
                "message": "An internal server error occurred while processing your request.",
                "request_id": request_id,
            }
            error_response = JSONResponse(status_code=500, content=safe_error)
            error_response.headers["X-Request-ID"] = request_id
            error_response.headers["X-Response-Time-Ms"] = str(duration_ms)
            return error_response

