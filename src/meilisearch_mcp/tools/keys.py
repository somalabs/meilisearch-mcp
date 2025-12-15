"""
API key management tools for Meilisearch MCP server.

These tools handle getting, creating, and deleting API keys.
"""

from typing import List, Optional

from ..context import get_context


def register_key_tools(mcp) -> None:
    """Register API key management tools with the FastMCP server."""

    @mcp.tool(name="get-keys")
    def get_keys(offset: Optional[int] = None, limit: Optional[int] = None) -> str:
        """
        Get list of API keys.

        Args:
            offset: Number of keys to skip
            limit: Maximum number of keys to return

        Returns:
            List of API keys
        """
        ctx = get_context()

        params = {}
        if offset is not None:
            params["offset"] = offset
        if limit is not None:
            params["limit"] = limit

        keys = ctx.meili_client.keys.get_keys(params if params else None)
        return f"API keys: {keys}"

    @mcp.tool(name="create-key")
    def create_key(
        actions: List[str],
        indexes: List[str],
        description: Optional[str] = None,
        expiresAt: Optional[str] = None,
    ) -> str:
        """
        Create a new API key.

        Args:
            actions: List of allowed actions (e.g., ["search", "documents.add"])
            indexes: List of indexes this key can access (["*"] for all)
            description: Optional description for the key
            expiresAt: Optional expiration date (ISO 8601 format)

        Returns:
            Created API key information
        """
        ctx = get_context()

        key_config = {
            "actions": actions,
            "indexes": indexes,
        }
        if description is not None:
            key_config["description"] = description
        if expiresAt is not None:
            key_config["expiresAt"] = expiresAt

        key = ctx.meili_client.keys.create_key(key_config)
        return f"Created API key: {key}"

    @mcp.tool(name="delete-key")
    def delete_key(key: str) -> str:
        """
        Delete an API key.

        Args:
            key: The API key or key UID to delete

        Returns:
            Confirmation of deletion
        """
        ctx = get_context()
        ctx.meili_client.keys.delete_key(key)
        return f"Successfully deleted API key: {key}"
