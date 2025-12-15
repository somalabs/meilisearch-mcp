"""
Settings management tools for Meilisearch MCP server.

These tools handle getting and updating index settings.
"""

from typing import Any, Dict

from ..context import get_context


def register_settings_tools(mcp) -> None:
    """Register settings management tools with the FastMCP server."""

    @mcp.tool(name="get-settings")
    def get_settings(indexUid: str) -> str:
        """
        Get current settings for an index.

        Args:
            indexUid: The unique identifier of the index

        Returns:
            Current settings configuration
        """
        ctx = get_context()
        settings = ctx.meili_client.settings.get_settings(indexUid)
        return f"Current settings: {settings}"

    @mcp.tool(name="update-settings")
    def update_settings(indexUid: str, settings: Dict[str, Any]) -> str:
        """
        Update settings for an index.

        Args:
            indexUid: The unique identifier of the index
            settings: Settings object with configuration to update

        Returns:
            Task information for the settings update
        """
        ctx = get_context()
        result = ctx.meili_client.settings.update_settings(indexUid, settings)
        return f"Settings updated: {result}"
