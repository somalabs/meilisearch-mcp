"""
Monitoring and health check tools for Meilisearch MCP server.

These tools provide health checks, version info, stats, and system information.
"""

import json
from datetime import datetime
from typing import Any

from ..context import get_context


def json_serializer(obj: Any) -> str:
    """Custom JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def register_monitoring_tools(mcp) -> None:
    """Register monitoring tools with the FastMCP server."""

    @mcp.tool(name="health-check")
    def health_check() -> str:
        """Check Meilisearch server health."""
        ctx = get_context()
        is_healthy = ctx.meili_client.health_check()
        status = "available" if is_healthy else "unavailable"
        return f"Meilisearch is {status}"

    @mcp.tool(name="get-version")
    def get_version() -> str:
        """Get Meilisearch version information."""
        ctx = get_context()
        version = ctx.meili_client.get_version()
        return f"Version info: {version}"

    @mcp.tool(name="get-stats")
    def get_stats() -> str:
        """Get database statistics."""
        ctx = get_context()
        stats = ctx.meili_client.get_stats()
        return f"Database stats: {stats}"

    @mcp.tool(name="get-health-status")
    def get_health_status() -> str:
        """Get comprehensive health status of Meilisearch."""
        ctx = get_context()
        status = ctx.meili_client.monitoring.get_health_status()
        ctx.logger.info("Health status checked", status=status.__dict__)
        return f"Health status: {json.dumps(status.__dict__, default=json_serializer)}"

    @mcp.tool(name="get-index-metrics")
    def get_index_metrics(indexUid: str) -> str:
        """
        Get detailed metrics for an index.

        Args:
            indexUid: The unique identifier of the index

        Returns:
            JSON string with index metrics
        """
        ctx = get_context()
        metrics = ctx.meili_client.monitoring.get_index_metrics(indexUid)
        ctx.logger.info(
            "Index metrics retrieved",
            index=indexUid,
            metrics=metrics.__dict__,
        )
        return f"Index metrics: {json.dumps(metrics.__dict__, default=json_serializer)}"

    @mcp.tool(name="get-system-info")
    def get_system_info() -> str:
        """Get system-level information."""
        ctx = get_context()
        info = ctx.meili_client.monitoring.get_system_information()
        ctx.logger.info("System information retrieved", info=info)
        return f"System information: {info}"
