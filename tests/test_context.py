"""Tests for server context management."""

import pytest
from src.meilisearch_mcp.context import ServerContext, get_context, reset_context, set_context


class TestServerContext:
    """Test ServerContext functionality."""

    def teardown_method(self):
        """Reset context after each test."""
        reset_context()

    def test_default_initialization(self):
        """Test that ServerContext initializes with defaults."""
        ctx = ServerContext()
        assert ctx.url is not None
        assert "localhost" in ctx.url or "MEILI_HTTP_ADDR" in str(ctx.url)

    def test_lazy_client_initialization(self):
        """Test that clients are lazily initialized."""
        ctx = ServerContext()
        assert ctx._meili_client is None
        # Access property to trigger lazy init
        client = ctx.meili_client
        assert client is not None
        assert ctx._meili_client is not None

    def test_lazy_chat_manager_initialization(self):
        """Test that chat manager is lazily initialized."""
        ctx = ServerContext()
        assert ctx._chat_manager is None
        # Access property to trigger lazy init
        manager = ctx.chat_manager
        assert manager is not None
        assert ctx._chat_manager is not None

    def test_update_connection(self):
        """Test updating connection settings."""
        ctx = ServerContext()
        new_url = "http://newhost:7700"
        new_key = "new_api_key"
        ctx.update_connection(url=new_url, api_key=new_key)
        assert ctx.url == new_url
        assert ctx.api_key == new_key


class TestContextSingleton:
    """Test global context singleton functionality."""

    def teardown_method(self):
        """Reset context after each test."""
        reset_context()

    def test_get_context_returns_singleton(self):
        """Test that get_context() returns the same instance."""
        ctx1 = get_context()
        ctx2 = get_context()
        assert ctx1 is ctx2

    def test_set_context(self):
        """Test setting a custom context."""
        custom_ctx = ServerContext(url="http://custom:7700")
        set_context(custom_ctx)
        retrieved_ctx = get_context()
        assert retrieved_ctx is custom_ctx
        assert retrieved_ctx.url == "http://custom:7700"

    def test_reset_context(self):
        """Test resetting the global context."""
        ctx1 = get_context()
        reset_context()
        ctx2 = get_context()
        # After reset, should get a new instance
        assert ctx1 is not ctx2
