"""
Search tools for Meilisearch MCP server.

These tools provide search functionality across Meilisearch indexes.
"""

import json
from datetime import datetime
from typing import Any, List, Optional

from ..context import get_context


def json_serializer(obj: Any) -> str:
    """Custom JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def register_search_tools(mcp) -> None:
    """Register search tools with the FastMCP server."""

    @mcp.tool(name="search")
    def search(
        query: str,
        indexUid: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        filter: Optional[str] = None,
        sort: Optional[List[str]] = None,
    ) -> str:
        """
        Search through Meilisearch indices. If indexUid is not provided, it will search across all indices.

        Args:
            query: The search query string
            indexUid: Optional index to search in (searches all if not provided)
            limit: Maximum number of results to return
            offset: Number of results to skip
            filter: Filter expression for results
            sort: List of attributes to sort by (e.g., ["price:asc"])

        Returns:
            JSON string with search results
        """
        ctx = get_context()

        search_results = ctx.meili_client.search(
            query=query,
            index_uid=indexUid,
            limit=limit,
            offset=offset,
            filter=filter,
            sort=sort,
        )

        formatted_results = json.dumps(
            search_results, indent=2, default=json_serializer
        )
        return f"Search results for '{query}':\n{formatted_results}"
