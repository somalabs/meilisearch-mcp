"""
Task management tools for Meilisearch MCP server.

These tools handle getting and managing asynchronous tasks in Meilisearch.
"""

from typing import List, Optional

from ..context import get_context


def register_task_tools(mcp) -> None:
    """Register task management tools with the FastMCP server."""

    @mcp.tool(name="get-task")
    def get_task(taskUid: int) -> str:
        """
        Get information about a specific task.

        Args:
            taskUid: The unique identifier of the task

        Returns:
            Task information
        """
        ctx = get_context()
        task = ctx.meili_client.tasks.get_task(taskUid)
        return f"Task information: {task}"

    @mcp.tool(name="get-tasks")
    def get_tasks(
        limit: Optional[int] = None,
        from_: Optional[int] = None,
        reverse: Optional[bool] = None,
        batchUids: Optional[List[str]] = None,
        uids: Optional[List[int]] = None,
        canceledBy: Optional[List[str]] = None,
        types: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        indexUids: Optional[List[str]] = None,
        afterEnqueuedAt: Optional[str] = None,
        beforeEnqueuedAt: Optional[str] = None,
        afterStartedAt: Optional[str] = None,
        beforeStartedAt: Optional[str] = None,
        afterFinishedAt: Optional[str] = None,
        beforeFinishedAt: Optional[str] = None,
    ) -> str:
        """
        Get list of tasks with optional filters.

        Args:
            limit: Maximum number of tasks to return
            from_: Task UID to start from (pagination)
            reverse: Whether to reverse the order
            batchUids: Filter by batch UIDs
            uids: Filter by specific task UIDs
            canceledBy: Filter by tasks canceled by specific UIDs
            types: Filter by task types
            statuses: Filter by task statuses
            indexUids: Filter by index UIDs
            afterEnqueuedAt: Filter tasks enqueued after this date
            beforeEnqueuedAt: Filter tasks enqueued before this date
            afterStartedAt: Filter tasks started after this date
            beforeStartedAt: Filter tasks started before this date
            afterFinishedAt: Filter tasks finished after this date
            beforeFinishedAt: Filter tasks finished before this date

        Returns:
            List of tasks matching the filters
        """
        ctx = get_context()

        # Build parameters dict, only including non-None values
        valid_params = {
            "limit",
            "from",
            "reverse",
            "batchUids",
            "uids",
            "canceledBy",
            "types",
            "statuses",
            "indexUids",
            "afterEnqueuedAt",
            "beforeEnqueuedAt",
            "afterStartedAt",
            "beforeStartedAt",
            "afterFinishedAt",
            "beforeFinishedAt",
        }

        # Map parameters - note: from_ maps to "from"
        params = {}
        if limit is not None:
            params["limit"] = limit
        if from_ is not None:
            params["from"] = from_
        if reverse is not None:
            params["reverse"] = reverse
        if batchUids is not None:
            params["batchUids"] = batchUids
        if uids is not None:
            params["uids"] = uids
        if canceledBy is not None:
            params["canceledBy"] = canceledBy
        if types is not None:
            params["types"] = types
        if statuses is not None:
            params["statuses"] = statuses
        if indexUids is not None:
            params["indexUids"] = indexUids
        if afterEnqueuedAt is not None:
            params["afterEnqueuedAt"] = afterEnqueuedAt
        if beforeEnqueuedAt is not None:
            params["beforeEnqueuedAt"] = beforeEnqueuedAt
        if afterStartedAt is not None:
            params["afterStartedAt"] = afterStartedAt
        if beforeStartedAt is not None:
            params["beforeStartedAt"] = beforeStartedAt
        if afterFinishedAt is not None:
            params["afterFinishedAt"] = afterFinishedAt
        if beforeFinishedAt is not None:
            params["beforeFinishedAt"] = beforeFinishedAt

        tasks = ctx.meili_client.tasks.get_tasks(params if params else None)
        return f"Tasks: {tasks}"

    @mcp.tool(name="cancel-tasks")
    def cancel_tasks(
        uids: Optional[str] = None,
        indexUids: Optional[str] = None,
        types: Optional[str] = None,
        statuses: Optional[str] = None,
    ) -> str:
        """
        Cancel tasks based on filters.

        Args:
            uids: Comma-separated list of task UIDs to cancel
            indexUids: Comma-separated list of index UIDs
            types: Comma-separated list of task types
            statuses: Comma-separated list of statuses

        Returns:
            Result of the cancellation request
        """
        ctx = get_context()

        params = {}
        if uids is not None:
            params["uids"] = uids
        if indexUids is not None:
            params["indexUids"] = indexUids
        if types is not None:
            params["types"] = types
        if statuses is not None:
            params["statuses"] = statuses

        result = ctx.meili_client.tasks.cancel_tasks(params)
        return f"Tasks cancelled: {result}"
