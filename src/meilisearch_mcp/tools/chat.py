"""
Chat completion tools for Meilisearch MCP server.

These tools provide chat completion functionality using Meilisearch's chat feature.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..context import get_context


def json_serializer(obj: Any) -> str:
    """Custom JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def register_chat_tools(mcp) -> None:
    """Register chat completion tools with the FastMCP server."""

    @mcp.tool(name="create-chat-completion")
    async def create_chat_completion(
        workspace_uid: str,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        stream: bool = True,
    ) -> str:
        """
        Create a conversational chat completion using Meilisearch's chat feature.

        Args:
            workspace_uid: Unique identifier of the chat workspace
            messages: List of message objects comprising the chat history
            model: The model to use for completion (default: gpt-3.5-turbo)
            stream: Whether to stream the response (currently must be true)

        Returns:
            Chat completion response
        """
        ctx = get_context()
        response = await ctx.chat_manager.create_chat_completion(
            workspace_uid=workspace_uid,
            messages=messages,
            model=model,
            stream=stream,
        )
        return f"Chat completion response:\n{response}"

    @mcp.tool(name="get-chat-workspaces")
    async def get_chat_workspaces(
        offset: Optional[int] = None, limit: Optional[int] = None
    ) -> str:
        """
        Get list of available chat workspaces.

        Args:
            offset: Number of workspaces to skip
            limit: Maximum number of workspaces to return

        Returns:
            JSON string with chat workspaces
        """
        ctx = get_context()
        workspaces = await ctx.chat_manager.get_chat_workspaces(
            offset=offset,
            limit=limit,
        )
        formatted_json = json.dumps(workspaces, indent=2, default=json_serializer)
        return f"Chat workspaces:\n{formatted_json}"

    @mcp.tool(name="get-chat-workspace-settings")
    async def get_chat_workspace_settings(workspace_uid: str) -> str:
        """
        Get settings for a specific chat workspace.

        Args:
            workspace_uid: Unique identifier of the chat workspace

        Returns:
            JSON string with workspace settings
        """
        ctx = get_context()
        settings = await ctx.chat_manager.get_chat_workspace_settings(
            workspace_uid=workspace_uid
        )
        formatted_json = json.dumps(settings, indent=2, default=json_serializer)
        return f"Workspace settings for '{workspace_uid}':\n{formatted_json}"

    @mcp.tool(name="update-chat-workspace-settings")
    async def update_chat_workspace_settings(
        workspace_uid: str, settings: Dict[str, Any]
    ) -> str:
        """
        Update settings for a specific chat workspace.

        Args:
            workspace_uid: Unique identifier of the chat workspace
            settings: Settings to update for the workspace

        Returns:
            JSON string with updated workspace settings
        """
        ctx = get_context()
        updated_settings = await ctx.chat_manager.update_chat_workspace_settings(
            workspace_uid=workspace_uid,
            settings=settings,
        )
        formatted_json = json.dumps(updated_settings, indent=2, default=json_serializer)
        return f"Updated workspace settings for '{workspace_uid}':\n{formatted_json}"
