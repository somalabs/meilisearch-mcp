"""
Index management tools for Meilisearch MCP server.

These tools handle creating, listing, and deleting Meilisearch indexes.
"""

import json
from datetime import datetime
from typing import Any, Optional

from ..context import get_context


def json_serializer(obj: Any) -> str:
    """Custom JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def register_index_tools(mcp) -> None:
    """Register index management tools with the FastMCP server."""

    @mcp.tool(name="create-index")
    def create_index(uid: str, primaryKey: Optional[str] = None) -> str:
        """
        Create a new Meilisearch index.

        Args:
            uid: Unique identifier for the index
            primaryKey: Optional primary key field name for documents

        Returns:
            Confirmation of index creation
        """
        ctx = get_context()
        result = ctx.meili_client.indexes.create_index(uid, primaryKey)
        return f"Created index: {result}"

    @mcp.tool(name="list-indexes")
    def list_indexes() -> str:
        """List all Meilisearch indexes."""
        ctx = get_context()
        indexes = ctx.meili_client.get_indexes()
        formatted_json = json.dumps(indexes, indent=2, default=json_serializer)
        return f"Indexes:\n{formatted_json}"

    @mcp.tool(name="delete-index")
    def delete_index(uid: str) -> str:
        """
        Delete a Meilisearch index.

        Args:
            uid: Unique identifier of the index to delete

        Returns:
            Confirmation of deletion
        """
        ctx = get_context()
        ctx.meili_client.indexes.delete_index(uid)
        return f"Successfully deleted index: {uid}"
