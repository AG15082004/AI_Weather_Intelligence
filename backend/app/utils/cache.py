"""TTL cache utilities.

Provides a simple time-based cache decorator for async functions,
used to reduce redundant database queries and API calls.
"""

import asyncio
import functools
import time
from typing import Any, Callable, Dict, Optional, Tuple

import structlog

from app.config import get_settings

log = structlog.get_logger()


class TTLCache:
    """Simple in-memory TTL cache.

    Stores results keyed by function arguments with automatic
    expiration based on configured TTL.
    """

    def __init__(self, ttl_seconds: Optional[int] = None) -> None:
        """Initialize the cache.

        Args:
            ttl_seconds: Cache entry lifetime in seconds.
                         Defaults to CACHE_TTL_SECONDS from settings.
        """
        self._ttl = ttl_seconds or get_settings().cache_ttl_seconds
        self._cache: Dict[str, Tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value if it exists and hasn't expired.

        Args:
            key: Cache key string.

        Returns:
            Cached value, or None if missing or expired.
        """
        entry = self._cache.get(key)
        if entry is None:
            return None

        value, expiry = entry
        if time.time() > expiry:
            del self._cache[key]
            return None

        return value

    def set(self, key: str, value: Any) -> None:
        """Store a value in the cache.

        Args:
            key: Cache key string.
            value: Value to cache.
        """
        self._cache[key] = (value, time.time() + self._ttl)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        log.info("cache_cleared")

    def evict_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries evicted.
        """
        now = time.time()
        expired_keys = [k for k, (_, exp) in self._cache.items() if now > exp]
        for key in expired_keys:
            del self._cache[key]
        if expired_keys:
            log.info("cache_evicted", count=len(expired_keys))
        return len(expired_keys)


def cached(ttl_seconds: Optional[int] = None) -> Callable:
    """Decorator to cache async function results with TTL.

    Args:
        ttl_seconds: Cache entry lifetime in seconds.
                     Defaults to CACHE_TTL_SECONDS from settings.

    Returns:
        Decorated function with caching.

    Usage:
        @cached(ttl_seconds=60)
        async def get_data(district: str) -> dict:
            ...
    """
    cache = TTLCache(ttl_seconds=ttl_seconds)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Build cache key from function name + args
            key_parts = [func.__name__] + [str(a) for a in args]
            key_parts += [f"{k}={v}" for k, v in sorted(kwargs.items())]
            cache_key = ":".join(key_parts)

            # Check cache
            result = cache.get(cache_key)
            if result is not None:
                log.debug("cache_hit", key=cache_key)
                return result

            # Call function and cache result
            log.debug("cache_miss", key=cache_key)
            result = await func(*args, **kwargs)
            cache.set(cache_key, result)
            return result

        # Expose cache for manual management
        wrapper.cache = cache  # type: ignore[attr-defined]
        return wrapper

    return decorator
