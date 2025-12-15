"""
Document management tools for Meilisearch MCP server.

These tools handle getting and adding documents to Meilisearch indexes.
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


def register_document_tools(mcp) -> None:
    """Register document management tools with the FastMCP server."""

    @mcp.tool(name="get-documents")
    def get_documents(
        indexUid: str, offset: Optional[int] = None, limit: Optional[int] = None
    ) -> str:
        """
        Get documents from an index.

        Args:
            indexUid: The unique identifier of the index
            offset: Number of documents to skip (default: 0)
            limit: Maximum number of documents to return (default: 20)

        Returns:
            JSON string with the documents
        """
        ctx = get_context()
        # Use defaults if not provided
        offset_val = offset if offset is not None else 0
        limit_val = limit if limit is not None else 20

        documents = ctx.meili_client.documents.get_documents(
            indexUid, offset_val, limit_val
        )
        formatted_json = json.dumps(documents, indent=2, default=json_serializer)
        return f"Documents:\n{formatted_json}"

    @mcp.tool(name="add-documents")
    def add_documents(
        indexUid: str, documents: List[Dict[str, Any]], primaryKey: Optional[str] = None
    ) -> str:
        """
        Add documents to an index.

        Args:
            indexUid: The unique identifier of the index
            documents: List of document objects to add
            primaryKey: Optional primary key field name

        Returns:
            Task information for the add operation
        """
        ctx = get_context()
        result = ctx.meili_client.documents.add_documents(
            indexUid, documents, primaryKey
        )
        return f"Added documents: {result}"
