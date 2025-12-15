"""
Connection management tools for Meilisearch MCP server.

These tools allow getting and updating the Meilisearch connection settings.
"""

from typing import Optional

from ..context import get_context


def register_connection_tools(mcp) -> None:
    """Register connection management tools with the FastMCP server."""

    @mcp.tool(name="get-connection-settings")
    def get_connection_settings() -> str:
        """Get current Meilisearch connection settings."""
        ctx = get_context()
        api_key_display = "*" * 8 if ctx.api_key else "Not set"
        return (
            f"Current connection settings:\nURL: {ctx.url}\nAPI Key: {api_key_display}"
        )

    @mcp.tool(name="update-connection-settings")
    def update_connection_settings(
        url: Optional[str] = None, api_key: Optional[str] = None
    ) -> str:
        """
        Update Meilisearch connection settings.

        Args:
            url: New Meilisearch server URL
            api_key: New API key for authentication

        Returns:
            Confirmation message with the updated URL
        """
        ctx = get_context()
        ctx.update_connection(url, api_key)
        return f"Successfully updated connection settings to URL: {ctx.url}"
