"""Tests for security utilities."""

import pytest
from src.meilisearch_mcp.security import secure_compare, validate_url, sanitize_for_logging


class TestSecureCompare:
    """Test secure string comparison function."""

    def test_equal_strings(self):
        """Test comparison of equal strings."""
        assert secure_compare("secret123", "secret123") is True

    def test_different_strings(self):
        """Test comparison of different strings."""
        assert secure_compare("secret123", "secret456") is False

    def test_none_values(self):
        """Test comparison with None values."""
        assert secure_compare(None, None) is True
        assert secure_compare("secret", None) is False
        assert secure_compare(None, "secret") is False

    def test_empty_strings(self):
        """Test comparison of empty strings."""
        assert secure_compare("", "") is True
        assert secure_compare("secret", "") is False


class TestValidateUrl:
    """Test URL validation function."""

    def test_valid_http_url(self):
        """Test validation of valid HTTP URL."""
        assert validate_url("http://localhost:7700") is True

    def test_valid_https_url(self):
        """Test validation of valid HTTPS URL."""
        assert validate_url("https://example.com") is True

    def test_invalid_scheme(self):
        """Test rejection of invalid URL scheme."""
        assert validate_url("ftp://example.com") is False

    def test_invalid_url_format(self):
        """Test rejection of invalid URL format."""
        assert validate_url("not-a-url") is False

    def test_missing_scheme(self):
        """Test rejection of URL without scheme."""
        assert validate_url("example.com") is False


class TestSanitizeForLogging:
    """Test log sanitization function."""

    def test_sanitize_short_string(self):
        """Test sanitization of short string."""
        result = sanitize_for_logging("short")
        # Short strings should be partially redacted
        assert "*" in result or result == "<redacted>"

    def test_sanitize_api_key(self):
        """Test sanitization of API key-like string."""
        result = sanitize_for_logging("sk_test_1234567890abcdef")
        # Should be redacted
        assert "*" in result or result == "<redacted>"

    def test_sanitize_none(self):
        """Test sanitization of None value."""
        result = sanitize_for_logging(None)
        assert result == "None"
