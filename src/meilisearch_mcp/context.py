"""
Server context for shared state management.

This module provides a context class that holds shared state across all tools,
including the Meilisearch client and chat manager instances.
"""

import os
import threading
from dataclasses import dataclass, field
from typing import Optional

from .client import MeilisearchClient
from .chat import ChatManager
from .logging import MCPLogger


@dataclass
class ServerContext:
    """
    Server context holding shared state for all MCP tools.

    This context is passed to tools via FastMCP's dependency injection,
    allowing tools to access the Meilisearch client and other shared resources.
    """

    url: str = field(
        default_factory=lambda: os.getenv("MEILI_HTTP_ADDR", "http://localhost:7700")
    )
    api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("MEILI_MASTER_KEY")
    )
    log_dir: Optional[str] = field(
        default_factory=lambda: os.path.expanduser("~/.meilisearch-mcp/logs")
    )

    # Lazy-initialized clients
    _meili_client: Optional[MeilisearchClient] = field(default=None, repr=False)
    _chat_manager: Optional[ChatManager] = field(default=None, repr=False)
    _logger: Optional[MCPLogger] = field(default=None, repr=False)

    @property
    def meili_client(self) -> MeilisearchClient:
        """Get or create the Meilisearch client."""
        if self._meili_client is None:
            self._meili_client = MeilisearchClient(self.url, self.api_key)
        return self._meili_client

    @property
    def chat_manager(self) -> ChatManager:
        """Get or create the chat manager."""
        if self._chat_manager is None:
            self._chat_manager = ChatManager(self.url, self.api_key)
        return self._chat_manager

    @property
    def logger(self) -> MCPLogger:
        """Get or create the logger."""
        if self._logger is None:
            self._logger = MCPLogger("meilisearch-mcp", self.log_dir)
        return self._logger

    def update_connection(
        self, url: Optional[str] = None, api_key: Optional[str] = None
    ) -> None:
        """
        Update connection settings and reinitialize clients.

        Args:
            url: New Meilisearch URL (optional)
            api_key: New API key (optional, can be empty string to clear)
        """
        if url:
            self.url = url
        if api_key is not None:
            self.api_key = api_key.strip() if api_key and api_key.strip() else None

        # Reinitialize clients with new settings
        self._meili_client = MeilisearchClient(self.url, self.api_key)
        self._chat_manager = ChatManager(self.url, self.api_key)

        self.logger.info(
            "Updated Meilisearch connection settings",
            url=self.url,
            has_api_key=bool(self.api_key),
            api_key_length=len(self.api_key) if self.api_key else 0,
        )

    def cleanup(self) -> None:
        """Clean shutdown of resources."""
        if self._logger:
            self._logger.info("Shutting down MCP server")
            self._logger.shutdown()


# Global context instance - initialized lazily with thread safety
_context: Optional[ServerContext] = None
_context_lock = threading.Lock()


def get_context() -> ServerContext:
    """
    Get the global server context, creating it if necessary.

    Uses double-checked locking pattern for thread-safe lazy initialization.
    """
    global _context
    if _context is None:
        with _context_lock:
            # Double-check after acquiring lock
            if _context is None:
                _context = ServerContext()
    return _context


def set_context(context: ServerContext) -> None:
    """Set the global server context."""
    global _context
    _context = context


def reset_context() -> None:
    """Reset the global context (useful for testing)."""
    global _context
    with _context_lock:
        if _context:
            try:
                _context.cleanup()
            except Exception as e:
                # Log but don't fail on cleanup errors
                import logging
                logging.error(f"Error during context cleanup: {e}")
        _context = None
