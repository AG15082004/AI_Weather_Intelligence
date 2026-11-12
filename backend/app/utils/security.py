"""Input sanitization utilities.

Provides functions to sanitize and validate user inputs
to prevent injection attacks and ensure data integrity.
"""

import hmac
import re
from typing import Any, Optional
import structlog

from app.config import get_settings

log = structlog.get_logger()

# Allowed characters for district names
_DISTRICT_PATTERN = re.compile(r"^[a-zA-Z\s\-\.]+$")

# Maximum lengths
_MAX_DISTRICT_LENGTH = 50
_MAX_QUERY_LENGTH = 1000


def sanitize_district_name(district: Optional[str]) -> Optional[str]:
    """Sanitize and validate a district name input.

    Args:
        district: Raw district name from user input.

    Returns:
        Sanitized district name, or None if invalid.
    """
    if district is None:
        return None

    district = district.strip()
    if not district:
        return None

    if len(district) > _MAX_DISTRICT_LENGTH:
        log.warning("district_name_too_long", length=len(district))
        return None

    if not _DISTRICT_PATTERN.match(district):
        log.warning("district_name_invalid_chars", district=district)
        return None

    return district


def sanitize_query(query: Optional[str]) -> Optional[str]:
    """Sanitize a free-text query input.

    Strips dangerous characters while preserving natural language.

    Args:
        query: Raw query string.

    Returns:
        Sanitized query string, or None if invalid.
    """
    if query is None:
        return None

    query = query.strip()
    if not query:
        return None

    if len(query) > _MAX_QUERY_LENGTH:
        log.warning("query_too_long", length=len(query))
        query = query[:_MAX_QUERY_LENGTH]

    # Remove potential SQL injection patterns
    dangerous_patterns = [
        r";\s*DROP\b",
        r";\s*DELETE\b",
        r";\s*INSERT\b",
        r";\s*UPDATE\b",
        r"--",
        r"/\*",
        r"\*/",
        r"xp_",
        r"EXEC\s+",
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            log.warning("query_contains_dangerous_pattern", pattern=pattern)
            query = re.sub(pattern, "", query, flags=re.IGNORECASE)

    return query


def sanitize_sql_identifier(identifier: str) -> str:
    """Sanitize a SQL identifier (table or column name).

    Only allows alphanumeric characters and underscores.

    Args:
        identifier: Raw identifier string.

    Returns:
        Sanitized identifier.

    Raises:
        ValueError: If identifier is empty or contains only invalid chars.
    """
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "", identifier)
    if not sanitized:
        raise ValueError(f"Invalid SQL identifier: {identifier!r}")
    return sanitized


# ---------------------------------------------------------------------------
# Production Secret Masking & Authentication
# ---------------------------------------------------------------------------

_SENSITIVE_KEY_PATTERNS = re.compile(
    r"(password|secret|token|authorization|cookie|bearer|key|credential|private)",
    re.IGNORECASE,
)


def mask_secrets(data: Any) -> Any:
    """Recursively mask sensitive values in dictionaries, lists, or strings.

    Args:
        data: Arbitrary object to be sanitized for logging or reporting.

    Returns:
        Sanitized copy with sensitive values masked with '***REDACTED***'.
    """
    if isinstance(data, dict):
        sanitized_dict = {}
        for k, v in data.items():
            if isinstance(k, str) and _SENSITIVE_KEY_PATTERNS.search(k):
                sanitized_dict[k] = "***REDACTED***"
            else:
                sanitized_dict[k] = mask_secrets(v)
        return sanitized_dict
    elif isinstance(data, (list, tuple, set)):
        return [mask_secrets(item) for item in data]
    elif isinstance(data, str):
        # Mask inline Bearer tokens or passwords if present in string
        if "bearer " in data.lower():
            return re.sub(r"(bearer\s+)[a-zA-Z0-9_\-\.]+", r"\1***REDACTED***", data, flags=re.IGNORECASE)
        return data
    return data


def verify_admin_key(provided_key: Optional[str]) -> bool:
    """Verify administrator authorization key using constant-time comparison.

    Args:
        provided_key: Key supplied via X-API-Key or Authorization header.

    Returns:
        True if valid, False otherwise.
    """
    settings = get_settings()
    configured_key = settings.admin_api_key

    # If no admin key is configured in production, deny sensitive operations
    if not configured_key:
        if settings.app_env.lower() in ("production", "staging"):
            log.warning("admin_key_verification_blocked", reason="admin_key_not_configured_in_production")
            return False
        # In local development without configured key, permit with warning
        log.warning("admin_key_unconfigured_permitting_dev")
        return True

    if not provided_key:
        return False

    # Extract bearer prefix if provided
    token = provided_key.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    return hmac.compare_digest(token, configured_key.strip())


def validate_ai_prompt(prompt: Optional[str], max_length: int = 1000) -> str:
    """Validate and sanitize a natural-language query for AI endpoints.

    Args:
        prompt: Raw user query string.
        max_length: Maximum allowed prompt character length.

    Returns:
        Sanitized prompt string.

    Raises:
        ValueError: If prompt is empty or exceeds character limits.
    """
    if not prompt or not prompt.strip():
        raise ValueError("AI query message cannot be empty.")

    clean_prompt = prompt.strip()
    if len(clean_prompt) > max_length:
        raise ValueError(f"AI query length ({len(clean_prompt)}) exceeds maximum limit of {max_length} characters.")

    sanitized = sanitize_query(clean_prompt)
    if not sanitized:
        raise ValueError("AI query contains invalid or dangerous content.")

    return sanitized
