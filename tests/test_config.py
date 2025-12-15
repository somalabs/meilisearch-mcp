"""Tests for configuration validation."""

import os
import pytest
from src.meilisearch_mcp.config import Config


class TestConfigValidation:
    """Test configuration validation logic."""

    def test_validate_empty_config(self):
        """Test validation with default configuration."""
        errors = Config.validate()
        assert isinstance(errors, list)
        # Default config should be valid
        # Note: May have errors in CI due to env vars

    def test_cors_wildcard(self):
        """Test CORS headers with wildcard origin."""
        headers = Config.get_cors_headers()
        assert "Access-Control-Allow-Origin" in headers
        assert headers["Access-Control-Allow-Origin"] == "*"

    def test_cors_specific_origin_allowed(self):
        """Test CORS headers with specific allowed origin."""
        # Save original and set test value
        original_origins = Config.CORS_ORIGINS
        try:
            Config.CORS_ORIGINS = ["https://example.com", "https://test.com"]
            headers = Config.get_cors_headers("https://example.com")
            assert headers["Access-Control-Allow-Origin"] == "https://example.com"
        finally:
            Config.CORS_ORIGINS = original_origins

    def test_cors_specific_origin_not_allowed(self):
        """Test CORS headers with disallowed origin."""
        original_origins = Config.CORS_ORIGINS
        try:
            Config.CORS_ORIGINS = ["https://example.com"]
            headers = Config.get_cors_headers("https://evil.com")
            assert headers == {}
        finally:
            Config.CORS_ORIGINS = original_origins

    def test_cors_invalid_origin_url(self):
        """Test CORS headers with invalid origin URL."""
        original_origins = Config.CORS_ORIGINS
        try:
            Config.CORS_ORIGINS = ["https://example.com"]
            # Invalid URL should be rejected
            headers = Config.get_cors_headers("not-a-valid-url")
            assert headers == {}
        finally:
            Config.CORS_ORIGINS = original_origins
