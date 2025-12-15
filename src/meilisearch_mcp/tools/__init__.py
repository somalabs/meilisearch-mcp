"""
MCP Tools package for Meilisearch.

This package contains all tool definitions organized by category.
Each module registers its tools with the FastMCP server instance.
"""

from .connection import register_connection_tools
from .monitoring import register_monitoring_tools
from .indexes import register_index_tools
from .documents import register_document_tools
from .settings import register_settings_tools
from .search import register_search_tools
from .tasks import register_task_tools
from .keys import register_key_tools
from .chat import register_chat_tools


def register_all_tools(mcp) -> None:
    """
    Register all tools with the FastMCP server instance.

    Args:
        mcp: The FastMCP server instance
    """
    register_connection_tools(mcp)
    register_monitoring_tools(mcp)
    register_index_tools(mcp)
    register_document_tools(mcp)
    register_settings_tools(mcp)
    register_search_tools(mcp)
    register_task_tools(mcp)
    register_key_tools(mcp)
    register_chat_tools(mcp)


__all__ = [
    "register_all_tools",
    "register_connection_tools",
    "register_monitoring_tools",
    "register_index_tools",
    "register_document_tools",
    "register_settings_tools",
    "register_search_tools",
    "register_task_tools",
    "register_key_tools",
    "register_chat_tools",
]
