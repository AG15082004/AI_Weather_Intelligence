"""TTL cache utilities.

Provides thread-safe, bounded in-memory TTL caching with LRU/FIFO eviction
and hit/miss observability metrics to optimize API responsiveness.
"""

from collections import OrderedDict
import functools
import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple
import structlog

from app.config import get_settings

log = structlog.get_logger()


class TTLCache:
    """Thread-safe, bounded in-memory TTL cache with hit/miss tracking."""

    def __init__(
        self,
        ttl_seconds: Optional[int] = None,
        max_entries: int = 500,
    ) -> None:
        """Initialize bounded TTL cache.

        Args:
            ttl_seconds: Lifetime of cached entries in seconds.
            max_entries: Maximum number of items before oldest entries are evicted.
        """
        self._ttl = ttl_seconds or get_settings().cache_ttl_seconds
        self._max_entries = max_entries
        self._cache: OrderedDict[str, Tuple[Any, float, float]] = OrderedDict()
        self._lock = threading.Lock()

        # Telemetry metrics
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value if it exists and hasn't expired.

        Returns:
            Cached value, or None if missing or expired.
        """
        with self._lock:
            if key not in self._cache:
                self.misses += 1
                return None

            value, expiry, _created_at = self._cache[key]
            now = time.time()
            if now > expiry:
                del self._cache[key]
                self.misses += 1
                return None

            # Move to end for LRU behavior
            self._cache.move_to_end(key)
            self.hits += 1
            return value

    def get_with_metadata(
        self, key: str, allow_stale: bool = False, max_stale_seconds: float = 86400.0
    ) -> Optional[Tuple[Any, float, float, bool]]:
        """Retrieve cached value with creation time, expiry, and staleness flag.

        Args:
            key: Cache key.
            allow_stale: Whether to return expired entries for graceful degraded mode.
            max_stale_seconds: Maximum age beyond expiry to permit stale retrieval.

        Returns:
            Tuple of (value, created_at, expiry, is_stale) or None if missing or past max_stale.
        """
        with self._lock:
            if key not in self._cache:
                self.misses += 1
                return None

            value, expiry, created_at = self._cache[key]
            now = time.time()
            is_expired = now > expiry

            if is_expired:
                if not allow_stale or (now - expiry) > max_stale_seconds:
                    del self._cache[key]
                    self.misses += 1
                    return None
                # Allowed stale retrieval during outage
                self.hits += 1
                return value, created_at, expiry, True

            self._cache.move_to_end(key)
            self.hits += 1
            return value, created_at, expiry, False

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Store a value in the cache with bounded capacity enforcement."""
        ttl = ttl_seconds if ttl_seconds is not None else self._ttl
        now = time.time()
        expiry = now + ttl

        with self._lock:
            # Enforce max entries bound (evict oldest if full)
            if key not in self._cache and len(self._cache) >= self._max_entries:
                self._cache.popitem(last=False)
                self.evictions += 1

            self._cache[key] = (value, expiry, now)
            self._cache.move_to_end(key)

    def clear(self) -> int:
        """Clear all cached entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            log.info("cache_cleared", count=count)
            return count

    def evict_expired(self) -> int:
        """Remove all expired entries."""
        now = time.time()
        evicted = 0
        with self._lock:
            keys = list(self._cache.keys())
            for key in keys:
                if key in self._cache and now > self._cache[key][1]:
                    del self._cache[key]
                    evicted += 1
                    self.evictions += 1
        if evicted:
            log.info("cache_evicted", count=evicted)
        return evicted

    def get_stats(self) -> Dict[str, Any]:
        """Return cache health and efficiency metrics."""
        with self._lock:
            total_lookups = self.hits + self.misses
            hit_ratio = (
                round((self.hits / total_lookups) * 100.0, 1)
                if total_lookups > 0
                else 0.0
            )
            return {
                "size": len(self._cache),
                "max_entries": self._max_entries,
                "default_ttl_seconds": self._ttl,
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "hit_ratio_pct": hit_ratio,
            }


# Singleton shared bounded cache for all weather queries & routes
shared_cache = TTLCache(max_entries=500)


def cached(ttl_seconds: Optional[int] = None) -> Callable:
    """Decorator to cache async function results with TTL using the shared cache.

    Args:
        ttl_seconds: Cache entry lifetime in seconds.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            key_parts = [func.__name__] + [str(a) for a in args]
            key_parts += [f"{k}={v}" for k, v in sorted(kwargs.items())]
            cache_key = ":".join(key_parts)

            result = shared_cache.get(cache_key)
            if result is not None:
                log.debug("cache_hit", key=cache_key)
                return result

            log.debug("cache_miss", key=cache_key)
            result = await func(*args, **kwargs)
            shared_cache.set(cache_key, result, ttl_seconds=ttl_seconds)
            return result

        wrapper.cache = shared_cache  # type: ignore[attr-defined]
        return wrapper

    return decorator
