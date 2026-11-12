"""Input sanitization utilities.

Provides functions to sanitize and validate user inputs
to prevent injection attacks and ensure data integrity.
"""

import re
from typing import Optional

import structlog

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
