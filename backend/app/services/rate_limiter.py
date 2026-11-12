"""In-Memory Sliding-Window Rate Limiter.

Provides fast, thread-safe rate limiting per client IP address
without requiring external storage (Redis) to preserve zero-cost deployment.
"""

from collections import deque
import threading
import time
from typing import Dict, Optional, Tuple
import structlog

log = structlog.get_logger()


class InMemoryRateLimiter:
    """Sliding-window in-memory rate limiter per client IP."""

    def __init__(self, default_limit: int = 30, default_window_seconds: int = 60) -> None:
        self.default_limit = default_limit
        self.default_window_seconds = default_window_seconds
        self._records: Dict[str, deque] = {}
        self._lock = threading.Lock()
        self._last_cleanup = time.time()

    def is_allowed(
        self, client_ip: str, limit: Optional[int] = None, window_seconds: Optional[int] = None
    ) -> Tuple[bool, int, float]:
        """Check if request from client_ip is permitted under rate limit.

        Args:
            client_ip: Identifier for caller (e.g. client IP).
            limit: Max requests allowed in the window (defaults to default_limit).
            window_seconds: Window duration in seconds (defaults to default_window_seconds).

        Returns:
            Tuple of (is_allowed, remaining_quota, retry_after_seconds)
        """
        max_requests = limit or self.default_limit
        window = window_seconds or self.default_window_seconds
        now = time.time()
        window_start = now - window

        with self._lock:
            # Periodic cleanup of records older than 10 minutes
            if now - self._last_cleanup > 300:
                self._cleanup_stale(window_start)

            if client_ip not in self._records:
                self._records[client_ip] = deque()

            ip_deque = self._records[client_ip]

            # Purge entries older than window_start
            while ip_deque and ip_deque[0] <= window_start:
                ip_deque.popleft()

            current_count = len(ip_deque)

            if current_count >= max_requests:
                # Calculate retry after based on the oldest event that needs to drop off
                oldest_event = ip_deque[0]
                retry_after = max(0.1, round(oldest_event + window - now, 1))
                log.warning(
                    "rate_limit_exceeded",
                    client_ip=client_ip,
                    current_count=current_count,
                    limit=max_requests,
                    retry_after=retry_after,
                )
                return False, 0, retry_after

            # Record this valid request
            ip_deque.append(now)
            remaining = max(0, max_requests - len(ip_deque))
            return True, remaining, 0.0

    def _cleanup_stale(self, threshold: float) -> None:
        """Prune idle IP records to prevent unbounded memory growth."""
        stale_ips = [
            ip for ip, d in self._records.items() if not d or d[-1] < threshold
        ]
        for ip in stale_ips:
            del self._records[ip]
        self._last_cleanup = time.time()

    def reset(self, client_ip: Optional[str] = None) -> None:
        """Reset rate limit history for a specific IP or all IPs."""
        with self._lock:
            if client_ip:
                self._records.pop(client_ip, None)
            else:
                self._records.clear()


# Global rate limiter instance for AI chat
ai_rate_limiter = InMemoryRateLimiter(default_limit=30, default_window_seconds=60)

