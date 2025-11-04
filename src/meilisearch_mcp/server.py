import asyncio
import json
import os
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from aiohttp import web
from aiohttp.web_response import Response
import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

from .client import MeilisearchClient
from .chat import ChatManager
from .logging import MCPLogger

logger = MCPLogger()


def json_serializer(obj: Any) -> str:
    """Custom JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def create_server(
    url: str = "http://localhost:7700", api_key: Optional[str] = None
) -> "MeilisearchMCPServer":
    """Create and return a configured MeilisearchMCPServer instance"""
    return MeilisearchMCPServer(url, api_key)


class MeilisearchMCPServer:
    def __init__(
        self,
        url: str = "http://localhost:7700",
        api_key: Optional[str] = None,
        log_dir: Optional[str] = None,
    ):
        """Initialize MCP server for Meilisearch"""
        if not log_dir:
            log_dir = os.path.expanduser("~/.meilisearch-mcp/logs")

        self.logger = MCPLogger("meilisearch-mcp", log_dir)
        self.url = url
        self.api_key = api_key
        self.meili_client = MeilisearchClient(url, api_key)
        self.chat_manager = ChatManager(url, api_key)
        self.server = Server("meilisearch")
        self._sse_queues: set[asyncio.Queue] = set()
        self._list_tools_handler = None
        self._call_tool_handler = None
        self._setup_handlers()

    def update_connection(
        self, url: Optional[str] = None, api_key: Optional[str] = None
    ):
        """Update connection settings and reinitialize client if needed"""
        if url:
            self.url = url
        if api_key is not None:  # Allow setting to None or empty string explicitly
            self.api_key = api_key.strip() if api_key and api_key.strip() else None

        self.meili_client = MeilisearchClient(self.url, self.api_key)
        self.chat_manager = ChatManager(self.url, self.api_key)
        self.logger.info(
            "Updated Meilisearch connection settings",
            url=self.url,
            has_api_key=bool(self.api_key),
            api_key_length=len(self.api_key) if self.api_key else 0,
        )

    def _setup_handlers(self):
        """Setup MCP request handlers"""
        
        async def list_tools_impl() -> list[types.Tool]:
            """List available tools"""
            return [
                types.Tool(
                    name="get-connection-settings",
                    description="Get current Meilisearch connection settings",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="update-connection-settings",
                    description="Update Meilisearch connection settings",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {"type": "string"},
                            "api_key": {"type": "string"},
                        },
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="health-check",
                    description="Check Meilisearch server health",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="get-version",
                    description="Get Meilisearch version information",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="get-stats",
                    description="Get database statistics",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="create-index",
                    description="Create a new Meilisearch index",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "uid": {"type": "string"},
                            "primaryKey": {"type": "string"},
                        },
                        "required": ["uid"],
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="list-indexes",
                    description="List all Meilisearch indexes",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="delete-index",
                    description="Delete a Meilisearch index",
                    inputSchema={
                        "type": "object",
                        "properties": {"uid": {"type": "string"}},
                        "required": ["uid"],
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="get-documents",
                    description="Get documents from an index",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "indexUid": {"type": "string"},
                            "offset": {"type": "integer"},
                            "limit": {"type": "integer"},
                        },
                        "required": ["indexUid"],
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="add-documents",
                    description="Add documents to an index",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "indexUid": {"type": "string"},
                            "documents": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": True,
                                },
                            },
                            "primaryKey": {"type": "string"},
                        },
                        "required": ["indexUid", "documents"],
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="get-settings",
                    description="Get current settings for an index",
                    inputSchema={
                        "type": "object",
                        "properties": {"indexUid": {"type": "string"}},
                        "required": ["indexUid"],
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="update-settings",
                    description="Update settings for an index",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "indexUid": {"type": "string"},
                            "settings": {
                                "type": "object",
                                "additionalProperties": True,
                            },
                        },
                        "required": ["indexUid", "settings"],
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="search",
                    description="Search through Meilisearch indices. If indexUid is not provided, it will search across all indices.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "indexUid": {"type": "string"},
                            "limit": {"type": "integer"},
                            "offset": {"type": "integer"},
                            "filter": {"type": "string"},
                            "sort": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["query"],
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="get-task",
                    description="Get information about a specific task",
                    inputSchema={
                        "type": "object",
                        "properties": {"taskUid": {"type": "integer"}},
                        "required": ["taskUid"],
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="get-tasks",
                    description="Get list of tasks with optional filters",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer"},
                            "from": {"type": "integer"},
                            "reverse": {"type": "boolean"},
                            "batchUids": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "uids": {
                                "type": "array",
                                "items": {"type": "integer"},
                            },
                            "canceledBy": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "types": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "statuses": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "indexUids": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "afterEnqueuedAt": {"type": "string"},
                            "beforeEnqueuedAt": {"type": "string"},
                            "afterStartedAt": {"type": "string"},
                            "beforeStartedAt": {"type": "string"},
                            "afterFinishedAt": {"type": "string"},
                            "beforeFinishedAt": {"type": "string"},
                        },
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="cancel-tasks",
                    description="Cancel tasks based on filters",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "uids": {"type": "string"},
                            "indexUids": {"type": "string"},
                            "types": {"type": "string"},
                            "statuses": {"type": "string"},
                        },
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="get-keys",
                    description="Get list of API keys",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "offset": {"type": "integer"},
                            "limit": {"type": "integer"},
                        },
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="create-key",
                    description="Create a new API key",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "actions": {"type": "array", "items": {"type": "string"}},
                            "indexes": {"type": "array", "items": {"type": "string"}},
                            "expiresAt": {"type": "string"},
                        },
                        "required": ["actions", "indexes"],
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="delete-key",
                    description="Delete an API key",
                    inputSchema={
                        "type": "object",
                        "properties": {"key": {"type": "string"}},
                        "required": ["key"],
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="get-health-status",
                    description="Get comprehensive health status of Meilisearch",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="get-index-metrics",
                    description="Get detailed metrics for an index",
                    inputSchema={
                        "type": "object",
                        "properties": {"indexUid": {"type": "string"}},
                        "required": ["indexUid"],
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="get-system-info",
                    description="Get system-level information",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="create-chat-completion",
                    description="Create a conversational chat completion using Meilisearch's chat feature",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workspace_uid": {
                                "type": "string",
                                "description": "Unique identifier of the chat workspace",
                            },
                            "messages": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "role": {
                                            "type": "string",
                                            "enum": ["user", "assistant", "system"],
                                        },
                                        "content": {"type": "string"},
                                    },
                                    "required": ["role", "content"],
                                },
                                "description": "List of message objects comprising the chat history",
                            },
                            "model": {
                                "type": "string",
                                "default": "gpt-3.5-turbo",
                                "description": "The model to use for completion",
                            },
                            "stream": {
                                "type": "boolean",
                                "default": True,
                                "description": "Whether to stream the response (currently must be true)",
                            },
                        },
                        "required": ["workspace_uid", "messages"],
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="get-chat-workspaces",
                    description="Get list of available chat workspaces",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "offset": {
                                "type": "integer",
                                "description": "Number of workspaces to skip",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of workspaces to return",
                            },
                        },
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="get-chat-workspace-settings",
                    description="Get settings for a specific chat workspace",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workspace_uid": {
                                "type": "string",
                                "description": "Unique identifier of the chat workspace",
                            },
                        },
                        "required": ["workspace_uid"],
                        "additionalProperties": False,
                    },
                ),
                types.Tool(
                    name="update-chat-workspace-settings",
                    description="Update settings for a specific chat workspace",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workspace_uid": {
                                "type": "string",
                                "description": "Unique identifier of the chat workspace",
                            },
                            "settings": {
                                "type": "object",
                                "description": "Settings to update for the workspace",
                                "additionalProperties": True,
                            },
                        },
                        "required": ["workspace_uid", "settings"],
                        "additionalProperties": False,
                    },
                ),
            ]
        
        self._list_tools_handler = list_tools_impl
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """List available tools - registered with MCP server"""
            return await list_tools_impl()
        
        async def call_tool_impl(name: str, arguments: Dict[str, Any]) -> list[types.TextContent]:
            """Handle tool execution"""
            try:
                if name == "get-connection-settings":
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Current connection settings:\nURL: {self.url}\nAPI Key: {'*' * 8 if self.api_key else 'Not set'}",
                        )
                    ]

                elif name == "update-connection-settings":
                    self.update_connection(
                        arguments.get("url"), arguments.get("api_key")
                    )
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully updated connection settings to URL: {self.url}",
                        )
                    ]

                elif name == "create-index":
                    result = self.meili_client.indexes.create_index(
                        arguments["uid"], arguments.get("primaryKey")
                    )
                    return [
                        types.TextContent(type="text", text=f"Created index: {result}")
                    ]

                elif name == "list-indexes":
                    indexes = self.meili_client.get_indexes()
                    formatted_json = json.dumps(
                        indexes, indent=2, default=json_serializer
                    )
                    return [
                        types.TextContent(
                            type="text", text=f"Indexes:\n{formatted_json}"
                        )
                    ]

                elif name == "delete-index":
                    result = self.meili_client.indexes.delete_index(arguments["uid"])
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully deleted index: {arguments['uid']}",
                        )
                    ]

                elif name == "get-documents":
                    offset = arguments.get("offset", 0)
                    limit = arguments.get("limit", 20)
                    documents = self.meili_client.documents.get_documents(
                        arguments["indexUid"],
                        offset,
                        limit,
                    )
                    formatted_json = json.dumps(
                        documents, indent=2, default=json_serializer
                    )
                    return [
                        types.TextContent(
                            type="text", text=f"Documents:\n{formatted_json}"
                        )
                    ]

                elif name == "add-documents":
                    result = self.meili_client.documents.add_documents(
                        arguments["indexUid"],
                        arguments["documents"],
                        arguments.get("primaryKey"),
                    )
                    return [
                        types.TextContent(
                            type="text", text=f"Added documents: {result}"
                        )
                    ]

                elif name == "health-check":
                    is_healthy = self.meili_client.health_check()
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Meilisearch is {is_healthy and 'available' or 'unavailable'}",
                        )
                    ]

                elif name == "get-version":
                    version = self.meili_client.get_version()
                    return [
                        types.TextContent(type="text", text=f"Version info: {version}")
                    ]

                elif name == "get-stats":
                    stats = self.meili_client.get_stats()
                    return [
                        types.TextContent(type="text", text=f"Database stats: {stats}")
                    ]

                elif name == "get-settings":
                    settings = self.meili_client.settings.get_settings(
                        arguments["indexUid"]
                    )
                    return [
                        types.TextContent(
                            type="text", text=f"Current settings: {settings}"
                        )
                    ]

                elif name == "update-settings":
                    result = self.meili_client.settings.update_settings(
                        arguments["indexUid"], arguments["settings"]
                    )
                    return [
                        types.TextContent(
                            type="text", text=f"Settings updated: {result}"
                        )
                    ]

                elif name == "search":
                    search_results = self.meili_client.search(
                        query=arguments["query"],
                        index_uid=arguments.get("indexUid"),
                        limit=arguments.get("limit"),
                        offset=arguments.get("offset"),
                        filter=arguments.get("filter"),
                        sort=arguments.get("sort"),
                    )

                    formatted_results = json.dumps(
                        search_results, indent=2, default=json_serializer
                    )
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Search results for '{arguments['query']}':\n{formatted_results}",
                        )
                    ]

                elif name == "get-task":
                    task = self.meili_client.tasks.get_task(arguments["taskUid"])
                    return [
                        types.TextContent(type="text", text=f"Task information: {task}")
                    ]

                elif name == "get-tasks":
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
                    filtered_args = (
                        {k: v for k, v in arguments.items() if k in valid_params}
                        if arguments
                        else {}
                    )
                    tasks = self.meili_client.tasks.get_tasks(filtered_args)
                    return [types.TextContent(type="text", text=f"Tasks: {tasks}")]

                elif name == "cancel-tasks":
                    result = self.meili_client.tasks.cancel_tasks(arguments)
                    return [
                        types.TextContent(
                            type="text", text=f"Tasks cancelled: {result}"
                        )
                    ]

                elif name == "get-keys":
                    keys = self.meili_client.keys.get_keys(arguments)
                    return [types.TextContent(type="text", text=f"API keys: {keys}")]

                elif name == "create-key":
                    key = self.meili_client.keys.create_key(
                        {
                            "description": arguments.get("description"),
                            "actions": arguments["actions"],
                            "indexes": arguments["indexes"],
                            "expiresAt": arguments.get("expiresAt"),
                        }
                    )
                    return [
                        types.TextContent(type="text", text=f"Created API key: {key}")
                    ]

                elif name == "delete-key":
                    self.meili_client.keys.delete_key(arguments["key"])
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully deleted API key: {arguments['key']}",
                        )
                    ]

                elif name == "get-health-status":
                    status = self.meili_client.monitoring.get_health_status()
                    self.logger.info("Health status checked", status=status.__dict__)
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Health status: {json.dumps(status.__dict__, default=json_serializer)}",
                        )
                    ]

                elif name == "get-index-metrics":
                    metrics = self.meili_client.monitoring.get_index_metrics(
                        arguments["indexUid"]
                    )
                    self.logger.info(
                        "Index metrics retrieved",
                        index=arguments["indexUid"],
                        metrics=metrics.__dict__,
                    )
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Index metrics: {json.dumps(metrics.__dict__, default=json_serializer)}",
                        )
                    ]

                elif name == "get-system-info":
                    info = self.meili_client.monitoring.get_system_information()
                    self.logger.info("System information retrieved", info=info)
                    return [
                        types.TextContent(
                            type="text", text=f"System information: {info}"
                        )
                    ]

                elif name == "create-chat-completion":
                    response = await self.chat_manager.create_chat_completion(
                        workspace_uid=arguments["workspace_uid"],
                        messages=arguments["messages"],
                        model=arguments.get("model", "gpt-3.5-turbo"),
                        stream=arguments.get("stream", True),
                    )
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Chat completion response:\n{response}",
                        )
                    ]

                elif name == "get-chat-workspaces":
                    workspaces = await self.chat_manager.get_chat_workspaces(
                        offset=arguments.get("offset") if arguments else None,
                        limit=arguments.get("limit") if arguments else None,
                    )
                    formatted_json = json.dumps(
                        workspaces, indent=2, default=json_serializer
                    )
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Chat workspaces:\n{formatted_json}",
                        )
                    ]

                elif name == "get-chat-workspace-settings":
                    settings = await self.chat_manager.get_chat_workspace_settings(
                        workspace_uid=arguments["workspace_uid"]
                    )
                    formatted_json = json.dumps(
                        settings, indent=2, default=json_serializer
                    )
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Workspace settings for '{arguments['workspace_uid']}':\n{formatted_json}",
                        )
                    ]

                elif name == "update-chat-workspace-settings":
                    updated_settings = (
                        await self.chat_manager.update_chat_workspace_settings(
                            workspace_uid=arguments["workspace_uid"],
                            settings=arguments["settings"],
                        )
                    )
                    formatted_json = json.dumps(
                        updated_settings, indent=2, default=json_serializer
                    )
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Updated workspace settings for '{arguments['workspace_uid']}':\n{formatted_json}",
                        )
                    ]

                raise ValueError(f"Unknown tool: {name}")

            except Exception as e:
                # Extract more details from the exception for better debugging
                error_details = {
                    "tool": name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "url": self.url,
                    "has_api_key": bool(self.api_key),
                }
                
                # If it's an HTTP error, try to extract status code and response
                if hasattr(e, "response") and hasattr(e.response, "status_code"):
                    error_details["status_code"] = e.response.status_code
                    error_details["response_text"] = e.response.text[:500] if hasattr(e.response, "text") else None
                
                self.logger.error(
                    f"Error executing tool {name}",
                    **error_details,
                )
                return [types.TextContent(type="text", text=f"Error: {str(e)}")]
        
        self._call_tool_handler = call_tool_impl
        
        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Optional[Dict[str, Any]] = None
        ) -> list[types.TextContent]:
            """Handle tool execution - registered with MCP server"""
            return await call_tool_impl(name, arguments or {})

    async def _run_mcp_server(self):
        """Run the MCP server on stdio"""
        logger.info("Starting Meilisearch MCP server...")

        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="meilisearch",
                    server_version="0.1.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

    def _verify_token(self, request: web.Request) -> bool:
        """Verify authentication token from request"""
        expected_token = os.getenv("MCP_AUTH_TOKEN")
        if not expected_token:
            return True
        
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return token == expected_token
        
        token_header = request.headers.get("X-MCP-Token", "")
        if token_header:
            return token_header == expected_token
        
        return False

    async def _mcp_sse_endpoint(self, request: web.Request):
        """SSE endpoint for MCP protocol - server-to-client communication"""
        if not self._verify_token(request):
            logger.warning("SSE connection rejected: Unauthorized")
            return web.json_response(
                {"error": "Unauthorized"}, status=401
            )
        
        logger.info("SSE connection established", remote=request.remote)
        
        response = web.StreamResponse()
        response.headers["Content-Type"] = "text/event-stream"
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Connection"] = "keep-alive"
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        
        await response.prepare(request)
        
        message_queue: asyncio.Queue = asyncio.Queue()
        self._sse_queues.add(message_queue)
        
        # Send initial connection message (not JSON-RPC, just a status message)
        # Note: This is a plain SSE message, not a JSON-RPC message
        try:
            await response.write(
                b": connection established\n\n"
            )
            
            while True:
                try:
                    message = await asyncio.wait_for(message_queue.get(), timeout=30.0)
                    
                    if message is None:
                        break
                    
                    sse_data = f"data: {json.dumps(message)}\n\n"
                    await response.write(sse_data.encode())
                    # Flush to ensure message is sent immediately
                    await response.drain()
                    logger.debug("Sent SSE message", message_id=message.get("id") if isinstance(message, dict) else None)
                    
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    try:
                        await response.write(b": ping\n\n")
                        await response.drain()
                    except (asyncio.CancelledError, ConnectionError, OSError):
                        # Connection closed, exit gracefully
                        break
                except asyncio.CancelledError:
                    # Connection cancelled, exit gracefully
                    break
                except (ConnectionError, OSError) as e:
                    # Connection error, exit gracefully
                    logger.debug(f"SSE connection error: {e}")
                    break
                
        except asyncio.CancelledError:
            pass
        finally:
            self._sse_queues.discard(message_queue)
            await response.write_eof()
        
        return response

    async def _mcp_post_endpoint(self, request: web.Request):
        """POST endpoint for MCP protocol - client-to-server communication"""
        if not self._verify_token(request):
            logger.warning("POST request rejected: Unauthorized")
            return web.json_response(
                {"jsonrpc": "2.0", "error": {"code": -32000, "message": "Unauthorized"}}, 
                status=401,
                headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
            )
        
        data = None
        request_id = None
        try:
            data = await request.json()
            request_id = data.get("id") if data else None
            method = data.get("method") if data else None
            logger.info(f"Received MCP request: {method}", request_id=request_id, method=method)
            
            if data and data.get("jsonrpc") == "2.0":
                params = data.get("params", {})
                
                if method == "initialize":
                    caps = self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    )
                    # Convert capabilities to dict and ensure null values are empty objects
                    if hasattr(caps, 'model_dump'):
                        caps_dict = caps.model_dump()
                    elif hasattr(caps, 'dict'):
                        caps_dict = caps.dict()
                    else:
                        caps_dict = {}
                    
                    # Ensure all capability fields are objects, not null
                    for key in ['logging', 'completions', 'prompts', 'resources']:
                        if key in caps_dict and caps_dict[key] is None:
                            caps_dict[key] = {}
                    
                    result = {
                        "protocolVersion": "2024-11-05",
                        "capabilities": caps_dict,
                        "serverInfo": {
                            "name": "meilisearch",
                            "version": "0.6.0",
                        },
                    }
                elif method == "tools/list":
                    if self._list_tools_handler:
                        tools_result = await self._list_tools_handler()
                        tools_list = tools_result if isinstance(tools_result, list) else []
                        logger.info(f"Retrieved {len(tools_list)} tools from handler", tool_count=len(tools_list))
                        
                        # Convert tools to dict format, excluding None values
                        def clean_tool_dict(d: Dict[str, Any]) -> Dict[str, Any]:
                            """Remove None values from tool dict, recursively"""
                            if isinstance(d, dict):
                                return {
                                    k: clean_tool_dict(v) 
                                    for k, v in d.items() 
                                    if v is not None
                                }
                            elif isinstance(d, list):
                                return [clean_tool_dict(item) for item in d]
                            return d
                        
                        tools_dict_list = []
                        for tool in tools_list:
                            if hasattr(tool, 'model_dump'):
                                # Use exclude_none=True if available (Pydantic v2)
                                try:
                                    tool_dict = tool.model_dump(exclude_none=True)
                                except TypeError:
                                    # Fallback for Pydantic v1 or if exclude_none not supported
                                    tool_dict = tool.model_dump()
                                    tool_dict = clean_tool_dict(tool_dict)
                            elif hasattr(tool, 'dict'):
                                # Pydantic v1
                                tool_dict = tool.dict(exclude_none=True)
                            elif hasattr(tool, '__dict__'):
                                tool_dict = clean_tool_dict(tool.__dict__)
                            else:
                                tool_dict = {"name": str(tool), "description": ""}
                            tools_dict_list.append(tool_dict)
                            logger.debug(f"Tool: {tool_dict.get('name', 'unknown')}")
                        
                        result = {"tools": tools_dict_list}
                        logger.info(f"Returning {len(tools_dict_list)} tools in response", tool_count=len(tools_dict_list))
                    else:
                        logger.warning("tools/list requested but handler not initialized")
                        result = {"tools": []}
                elif method == "tools/call":
                    tool_name = params.get("name")
                    tool_args = params.get("arguments", {})
                    if self._call_tool_handler:
                        call_result = await self._call_tool_handler(tool_name, tool_args)
                        result = {
                            "content": [
                                content.model_dump() if hasattr(content, 'model_dump')
                                else content.dict() if hasattr(content, 'dict')
                                else {"type": "text", "text": str(content)}
                                for content in call_result
                            ]
                        }
                    else:
                        result = {"content": [{"type": "text", "text": "Handler not initialized"}]}
                elif method == "prompts/list":
                    # MCP clients may request prompts - we don't support them, return empty list
                    logger.info("Received prompts/list request - returning empty list")
                    result = {"prompts": []}
                elif method == "resources/list":
                    # MCP clients may request resources - we don't support them, return empty list
                    logger.info("Received resources/list request - returning empty list")
                    result = {"resources": []}
                else:
                    logger.warning(f"Unknown method requested: {method}", method=method, request_id=request_id)
                    return web.json_response(
                        {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}},
                        status=200,
                        headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
                    )
                
                response_data = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result,
                }
                
                # MCP HTTP/SSE protocol: Send response via the appropriate channel
                # For "initialize", "tools/list", "tools/call", "prompts/list", and "resources/list", 
                # always send via POST response body (SSE connection might not be established yet)
                # Tool calls need immediate responses, so always use POST
                # For other methods, prefer SSE if available
                methods_via_post = ["initialize", "tools/list", "tools/call", "prompts/list", "resources/list"]
                if method in methods_via_post or not self._sse_queues:
                    # Send response via POST body (especially for initialize and tools/list)
                    logger.info(f"Returning HTTP response for method {method}", request_id=request_id, via_post=True)
                    return web.json_response(
                        response_data,
                        headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
                    )
                else:
                    # Send response via SSE stream for other methods
                    logger.info(f"Sending response via SSE for method {method}", request_id=request_id, queue_count=len(self._sse_queues))
                    sent_count = 0
                    for queue in self._sse_queues:
                        try:
                            await queue.put(response_data)
                            sent_count += 1
                            logger.debug(f"Queued message for SSE stream {sent_count}", request_id=request_id)
                        except Exception as e:
                            logger.error(f"Failed to send via SSE queue: {e}")
                    logger.info(f"Queued response to {sent_count} SSE stream(s) for method {method}", request_id=request_id)
                    # Return 202 Accepted since response is sent via SSE
                    return web.Response(
                        status=202,
                        headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
                    )
            else:
                return web.json_response(
                    {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32600, "message": "Invalid JSON-RPC request"}},
                    status=400,
                    headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
                )
                
        except Exception as e:
            logger.error(f"Error processing MCP request: {e}")
            # request_id is already set from the try block if data was parsed
            return web.json_response(
                {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32603, "message": str(e)}},
                status=500,
                headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
            )

    async def _create_health_check_app(self):
        """Create HTTP health check application for Cloud Run"""
        app = web.Application()

        async def health_check(request):
            """Health check endpoint for Cloud Run"""
            try:
                is_healthy = self.meili_client.health_check()
                if is_healthy:
                    return web.json_response(
                        {"status": "healthy", "service": "meilisearch-mcp"}, status=200
                    )
                else:
                    return web.json_response(
                        {"status": "degraded", "service": "meilisearch-mcp", "reason": "meilisearch_unavailable"},
                        status=503
                    )
            except Exception as e:
                return web.json_response(
                    {"status": "error", "service": "meilisearch-mcp", "error": str(e)},
                    status=503
                )
        
        async def root_handler(request):
            """Root endpoint - redirects to MCP SSE or health check based on Accept header"""
            accept = request.headers.get("Accept", "")
            if "text/event-stream" in accept or request.query_string == "sse":
                return await self._mcp_sse_endpoint(request)
            return await health_check(request)

        app.router.add_get("/", root_handler)
        app.router.add_get("/health", health_check)
        app.router.add_get("/ready", health_check)
        
        # MCP endpoints - Cursor may connect to /mcp, /sse, /v1/sse, or root
        # Note: Some MCP clients use the same path for both GET (SSE) and POST
        app.router.add_get("/mcp", self._mcp_sse_endpoint)
        app.router.add_post("/mcp", self._mcp_post_endpoint)
        app.router.add_get("/sse", self._mcp_sse_endpoint)
        app.router.add_post("/sse", self._mcp_post_endpoint)
        app.router.add_get("/v1/sse", self._mcp_sse_endpoint)
        app.router.add_post("/v1/sse", self._mcp_post_endpoint)
        app.router.add_post("/message", self._mcp_post_endpoint)
        app.router.add_post("/v1/message", self._mcp_post_endpoint)
        
        # Add OPTIONS handler for CORS preflight
        async def options_handler(request):
            return web.Response(
                status=200,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Max-Age": "86400",
                }
            )
        
        app.router.add_options("/", options_handler)
        app.router.add_options("/mcp", options_handler)
        app.router.add_options("/sse", options_handler)
        app.router.add_options("/v1/sse", options_handler)
        app.router.add_options("/message", options_handler)
        app.router.add_options("/v1/message", options_handler)

        # Log registered routes for debugging
        logger.info("Registered HTTP routes:")
        for route in app.router.routes():
            logger.info(f"  {route.method} {route.resource.canonical}")
        
        return app

    async def run(self):
        """Run the MCP server, optionally with HTTP health check for Cloud Run"""
        port = os.getenv("PORT")
        
        if port:
            port_num = int(port)
            logger.info(f"Cloud Run detected: Starting HTTP health check on port {port_num}")
            
            app = await self._create_health_check_app()
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", port_num)
            await site.start()
            
            logger.info(f"HTTP health check server started on port {port_num}")
            
            async def run_mcp_with_error_handling():
                try:
                    await self._run_mcp_server()
                except (EOFError, OSError) as e:
                    logger.warning(
                        f"MCP stdio server unavailable: {e}. "
                        "Container will remain alive for health checks."
                    )
                    await asyncio.Event().wait()
                except Exception as e:
                    logger.error(f"Unexpected error in MCP server: {e}")
                    await asyncio.Event().wait()
            
            asyncio.create_task(run_mcp_with_error_handling())
            
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                logger.info("Shutting down HTTP health check server...")
                await runner.cleanup()
                raise
        else:
            await self._run_mcp_server()

    def cleanup(self):
        """Clean shutdown"""
        self.logger.info("Shutting down MCP server")
        self.logger.shutdown()


def main():
    """Main entry point"""
    url = os.getenv("MEILI_HTTP_ADDR", "http://localhost:7700")
    api_key = os.getenv("MEILI_MASTER_KEY")

    server = create_server(url, api_key)
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
