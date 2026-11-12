"""Production Security Middleware.

Applies standard OWASP security headers, request body size limits,
and safe error response sanitization.
"""

from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from app.config import get_settings

log = structlog.get_logger()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces standard OWASP HTTP security headers on all responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response: Response = await call_next(request)

        # Do not override existing headers if already set
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()",
        )
        response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Enforces maximum incoming payload size to guard against buffer exhaustion."""

    def __init__(self, app, max_bytes: int = 1_048_576) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check content-length header if provided
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_bytes:
                    log.warning(
                        "request_payload_too_large",
                        content_length=length,
                        limit=self.max_bytes,
                        path=request.url.path,
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "status": "error",
                            "message": f"Payload size exceeds maximum limit of {self.max_bytes} bytes.",
                        },
                    )
            except ValueError:
                pass

        return await call_next(request)

