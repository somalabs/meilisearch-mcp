"""Tests for HTTP client pool."""

import pytest
from src.meilisearch_mcp.http_client import HTTPClientPool, get_http_pool


class TestHTTPClientPool:
    """Test HTTP client pool functionality."""

    def test_singleton_pattern(self):
        """Test that HTTPClientPool implements singleton pattern."""
        pool1 = HTTPClientPool()
        pool2 = HTTPClientPool()
        assert pool1 is pool2

    def test_get_http_pool_returns_singleton(self):
        """Test that get_http_pool() returns the same instance."""
        pool1 = get_http_pool()
        pool2 = get_http_pool()
        assert pool1 is pool2

    def test_get_client_returns_tuple(self):
        """Test that get_client() returns (client, headers) tuple."""
        pool = get_http_pool()
        result = pool.get_client("http://localhost:7700")
        assert isinstance(result, tuple)
        assert len(result) == 2
        client, headers = result
        assert client is not None
        assert isinstance(headers, dict)

    def test_get_client_with_api_key(self):
        """Test that get_client() includes auth header when API key provided."""
        pool = get_http_pool()
        client, headers = pool.get_client("http://localhost:7700", api_key="test_key")
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_key"

    def test_get_client_without_api_key(self):
        """Test that get_client() excludes auth header when no API key."""
        pool = get_http_pool()
        client, headers = pool.get_client("http://localhost:7700")
        assert "Authorization" not in headers

    def test_get_client_reuses_client(self):
        """Test that get_client() reuses clients for same URL."""
        pool = get_http_pool()
        client1, _ = pool.get_client("http://localhost:7700")
        client2, _ = pool.get_client("http://localhost:7700")
        # Should return the same client instance
        assert client1 is client2

    def test_get_client_different_headers_same_client(self):
        """Test that different API keys use the same client but different headers."""
        pool = get_http_pool()
        client1, headers1 = pool.get_client("http://localhost:7700", api_key="key1")
        client2, headers2 = pool.get_client("http://localhost:7700", api_key="key2")
        # Should reuse the same client
        assert client1 is client2
        # But headers should be different
        assert headers1 != headers2
        assert headers1["Authorization"] == "Bearer key1"
        assert headers2["Authorization"] == "Bearer key2"
