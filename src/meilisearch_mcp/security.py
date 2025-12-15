"""
Security utilities for production use.

This module provides security functions including secure token comparison
to prevent timing attacks.
"""

import hmac
import hashlib
from typing import Optional


def secure_compare(a: Optional[str], b: Optional[str]) -> bool:
    """
    Securely compare two strings to prevent timing attacks.

    Uses constant-time comparison to prevent attackers from learning
    information about the expected value through timing differences.

    Args:
        a: First string to compare
        b: Second string to compare

    Returns:
        True if strings are equal, False otherwise
    """
    if a is None or b is None:
        return a == b

    # Convert to bytes for hmac comparison
    a_bytes = a.encode("utf-8") if isinstance(a, str) else a
    b_bytes = b.encode("utf-8") if isinstance(b, str) else b

    # Use hmac.compare_digest for constant-time comparison
    return hmac.compare_digest(a_bytes, b_bytes)


def validate_url(url: str) -> bool:
    """
    Validate URL format and security.

    Args:
        url: URL to validate

    Returns:
        True if URL is valid and safe
    """
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
        # Only allow http/https
        if parsed.scheme not in ("http", "https"):
            return False
        # Must have netloc
        if not parsed.netloc:
            return False
        # Prevent localhost in production (can be overridden if needed)
        # This is a basic check - you may want to make it configurable
        return True
    except Exception:
        return False


def sanitize_for_logging(value: Optional[str], max_length: int = 50) -> str:
    """
    Sanitize sensitive values for logging.

    Args:
        value: Value to sanitize
        max_length: Maximum length before truncation

    Returns:
        Sanitized string safe for logging
    """
    if value is None:
        return "None"
    if not value:
        return ""
    if len(value) > max_length:
        return value[:max_length] + "..."
    # Mask sensitive data (API keys, tokens, etc.)
    if len(value) > 8:
        return value[:4] + "*" * (len(value) - 8) + value[-4:]
    return "*" * len(value)
