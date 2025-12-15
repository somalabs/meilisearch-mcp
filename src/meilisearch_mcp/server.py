"""
Meilisearch MCP Server using FastMCP.

This module provides an MCP server for Meilisearch using the FastMCP framework,
with support for both STDIO and HTTP/SSE transports.
"""

import asyncio
import json
import os
import traceback
from typing import Optional, Dict, Any

from aiohttp import web
from fastmcp import FastMCP

from .context import ServerContext, get_context, set_context, reset_context
from .tools import register_all_tools
from .logging import MCPLogger

# Create FastMCP server instance
mcp = FastMCP(
    "meilisearch",
    version="0.6.0",
)

# Register all tools with the FastMCP server
register_all_tools(mcp)

# Module-level logger
logger = MCPLogger()


def create_server(
    url: str = "http://localhost:7700", api_key: Optional[str] = None
) -> "MeilisearchMCPServer":
    """Create and return a configured MeilisearchMCPServer instance."""
    return MeilisearchMCPServer(url, api_key)


class MeilisearchMCPServer:
    """
    Wrapper class for the FastMCP server with HTTP/SSE support.

    This class provides backward compatibility with the existing API while
    using FastMCP under the hood. It also adds HTTP/SSE endpoints for
    Cloud Run deployment.
    """

    def __init__(
        self,
        url: str = "http://localhost:7700",
        api_key: Optional[str] = None,
        log_dir: Optional[str] = None,
    ):
        """Initialize MCP server for Meilisearch."""
        if not log_dir:
            log_dir = os.path.expanduser("~/.meilisearch-mcp/logs")

        # Initialize context with connection settings
        ctx = ServerContext(url=url, api_key=api_key, log_dir=log_dir)
        set_context(ctx)

        self.logger = ctx.logger
        self._sse_queues: set[asyncio.Queue] = set()

        # Keep reference to the FastMCP server
        self.server = mcp._mcp_server

    @property
    def url(self) -> str:
        """Get the current Meilisearch URL."""
        return get_context().url

    @property
    def api_key(self) -> Optional[str]:
        """Get the current API key."""
        return get_context().api_key

    @property
    def meili_client(self):
        """Get the Meilisearch client."""
        return get_context().meili_client

    @property
    def chat_manager(self):
        """Get the chat manager."""
        return get_context().chat_manager

    def update_connection(
        self, url: Optional[str] = None, api_key: Optional[str] = None
    ):
        """Update connection settings and reinitialize client if needed."""
        get_context().update_connection(url, api_key)

    def _verify_token(self, request: web.Request) -> bool:
        """Verify authentication token from request."""
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
        """SSE endpoint for MCP protocol - server-to-client communication."""
        if not self._verify_token(request):
            logger.warning("SSE connection rejected: Unauthorized")
            return web.json_response({"error": "Unauthorized"}, status=401)

        logger.info("SSE connection established", remote=request.remote)

        response = web.StreamResponse()
        response.headers["Content-Type"] = "text/event-stream"
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Connection"] = "keep-alive"
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"

        message_queue: asyncio.Queue = asyncio.Queue()
        self._sse_queues.add(message_queue)

        try:
            await response.prepare(request)
            await response.write(b": connection established\n\n")
            await response.drain()

            while True:
                try:
                    message = await asyncio.wait_for(message_queue.get(), timeout=30.0)

                    if message is None:
                        break

                    try:
                        sse_data = f"data: {json.dumps(message)}\n\n"
                        await response.write(sse_data.encode())
                        await response.drain()
                        logger.debug(
                            "Sent SSE message",
                            message_id=(
                                message.get("id") if isinstance(message, dict) else None
                            ),
                        )
                    except (
                        ConnectionError,
                        OSError,
                        asyncio.CancelledError,
                    ) as write_error:
                        logger.debug(
                            f"SSE write error (connection likely closed): {write_error}"
                        )
                        break

                except asyncio.TimeoutError:
                    try:
                        await response.write(b": ping\n\n")
                        await response.drain()
                    except (
                        asyncio.CancelledError,
                        ConnectionError,
                        OSError,
                    ) as ping_error:
                        logger.debug(
                            f"SSE ping failed (connection closed): {ping_error}"
                        )
                        break
                except asyncio.CancelledError:
                    logger.debug("SSE connection cancelled")
                    break
                except (ConnectionError, OSError) as e:
                    logger.debug(f"SSE connection error: {e}")
                    break
                except Exception as e:
                    logger.error(
                        f"Unexpected error in SSE loop: {e}",
                        error_type=type(e).__name__,
                        traceback=traceback.format_exc(),
                    )
                    await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(
                f"Error in SSE endpoint: {e}",
                error_type=type(e).__name__,
                remote=request.remote,
                traceback=traceback.format_exc(),
            )
        finally:
            self._sse_queues.discard(message_queue)
            try:
                if not response.prepared:
                    await response.prepare(request)
                await response.write_eof()
            except Exception as eof_error:
                logger.debug(f"Error during SSE cleanup: {eof_error}")

        logger.info("SSE connection closed", remote=request.remote)
        return response

    async def _mcp_post_endpoint(self, request: web.Request):
        """POST endpoint for MCP protocol - client-to-server communication."""
        if not self._verify_token(request):
            logger.warning("POST request rejected: Unauthorized")
            return web.json_response(
                {
                    "jsonrpc": "2.0",
                    "error": {"code": -32000, "message": "Unauthorized"},
                },
                status=401,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                },
            )

        data = None
        request_id = None
        method = None
        try:
            try:
                data = await request.json()
            except json.JSONDecodeError as e:
                logger.error(
                    f"Invalid JSON in request body: {e}", remote=request.remote
                )
                return web.json_response(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": "Parse error"},
                    },
                    status=400,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "*",
                    },
                )
            except Exception as e:
                logger.error(
                    f"Error reading request body: {e}",
                    remote=request.remote,
                    error_type=type(e).__name__,
                )
                return web.json_response(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32600, "message": "Invalid Request"},
                    },
                    status=400,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "*",
                    },
                )

            request_id = data.get("id") if data else None
            method = data.get("method") if data else None
            logger.info(
                f"Received MCP request: {method}",
                request_id=request_id,
                method=method,
                remote=request.remote,
            )

            if data and data.get("jsonrpc") == "2.0":
                params = data.get("params", {})

                if method == "initialize":
                    result = {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {},
                            "logging": {},
                            "prompts": {},
                            "resources": {},
                        },
                        "serverInfo": {
                            "name": "meilisearch",
                            "version": "0.6.0",
                        },
                    }
                elif method == "tools/list":
                    # Get tools from FastMCP
                    tools_list = []
                    all_tools = await mcp._tool_manager.get_tools()
                    for tool in all_tools.values():
                        # Get schema - tool.parameters can be a Pydantic model or dict
                        if tool.parameters:
                            if hasattr(tool.parameters, "model_json_schema"):
                                schema = tool.parameters.model_json_schema()
                            elif isinstance(tool.parameters, dict):
                                schema = tool.parameters
                            else:
                                schema = {
                                    "type": "object",
                                    "properties": {},
                                    "additionalProperties": False,
                                }
                        else:
                            schema = {
                                "type": "object",
                                "properties": {},
                                "additionalProperties": False,
                            }

                        tool_dict = {
                            "name": tool.name,
                            "description": tool.description or "",
                            "inputSchema": schema,
                        }
                        # Ensure additionalProperties is false for OpenAI compatibility
                        if "additionalProperties" not in tool_dict["inputSchema"]:
                            tool_dict["inputSchema"]["additionalProperties"] = False
                        tools_list.append(tool_dict)

                    logger.info(
                        f"Retrieved {len(tools_list)} tools from handler",
                        tool_count=len(tools_list),
                    )
                    result = {"tools": tools_list}

                elif method == "tools/call":
                    tool_name = params.get("name")
                    tool_args = params.get("arguments", {})

                    try:
                        # Execute tool via FastMCP
                        call_result = await asyncio.wait_for(
                            mcp._tool_manager.call_tool(tool_name, tool_args),
                            timeout=300.0,
                        )

                        # Format result for MCP protocol
                        if isinstance(call_result, str):
                            result = {
                                "content": [{"type": "text", "text": call_result}]
                            }
                        elif isinstance(call_result, list):
                            result = {
                                "content": [
                                    (
                                        {"type": "text", "text": str(item)}
                                        if isinstance(item, str)
                                        else item
                                    )
                                    for item in call_result
                                ]
                            }
                        else:
                            result = {
                                "content": [{"type": "text", "text": str(call_result)}]
                            }

                    except asyncio.TimeoutError:
                        logger.error(
                            f"Tool execution timeout: {tool_name}",
                            tool_name=tool_name,
                            request_id=request_id,
                        )
                        result = {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Error: Tool execution timed out after 5 minutes. The operation may still be processing.",
                                }
                            ]
                        }
                    except Exception as tool_error:
                        logger.error(
                            f"Tool execution error: {tool_error}",
                            tool_name=tool_name,
                            request_id=request_id,
                            error_type=type(tool_error).__name__,
                            traceback=traceback.format_exc(),
                        )
                        result = {
                            "content": [
                                {"type": "text", "text": f"Error: {str(tool_error)}"}
                            ]
                        }

                elif method == "prompts/list":
                    logger.info("Received prompts/list request - returning empty list")
                    result = {"prompts": []}
                elif method == "resources/list":
                    logger.info(
                        "Received resources/list request - returning empty list"
                    )
                    result = {"resources": []}
                else:
                    logger.warning(
                        f"Unknown method requested: {method}",
                        method=method,
                        request_id=request_id,
                    )
                    return web.json_response(
                        {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32601,
                                "message": f"Method not found: {method}",
                            },
                        },
                        status=200,
                        headers={
                            "Access-Control-Allow-Origin": "*",
                            "Access-Control-Allow-Headers": "*",
                        },
                    )

                response_data = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result,
                }

                methods_via_post = [
                    "initialize",
                    "tools/list",
                    "tools/call",
                    "prompts/list",
                    "resources/list",
                ]
                if method in methods_via_post or not self._sse_queues:
                    logger.info(
                        f"Returning HTTP response for method {method}",
                        request_id=request_id,
                        via_post=True,
                    )
                    return web.json_response(
                        response_data,
                        headers={
                            "Access-Control-Allow-Origin": "*",
                            "Access-Control-Allow-Headers": "*",
                        },
                    )
                else:
                    logger.info(
                        f"Sending response via SSE for method {method}",
                        request_id=request_id,
                        queue_count=len(self._sse_queues),
                    )
                    sent_count = 0
                    for queue in self._sse_queues:
                        try:
                            await queue.put(response_data)
                            sent_count += 1
                            logger.debug(
                                f"Queued message for SSE stream {sent_count}",
                                request_id=request_id,
                            )
                        except Exception as e:
                            logger.error(f"Failed to send via SSE queue: {e}")
                    logger.info(
                        f"Queued response to {sent_count} SSE stream(s) for method {method}",
                        request_id=request_id,
                    )
                    return web.Response(
                        status=202,
                        headers={
                            "Access-Control-Allow-Origin": "*",
                            "Access-Control-Allow-Headers": "*",
                        },
                    )
            else:
                return web.json_response(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32600,
                            "message": "Invalid JSON-RPC request",
                        },
                    },
                    status=400,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "*",
                    },
                )

        except Exception as e:
            error_traceback = traceback.format_exc()
            logger.error(
                f"Error processing MCP request: {e}",
                error_type=type(e).__name__,
                method=method,
                request_id=request_id,
                remote=request.remote if hasattr(request, "remote") else None,
                traceback=error_traceback,
            )

            error_message = str(e) if e else "Internal error"
            try:
                return web.json_response(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32603, "message": error_message},
                    },
                    status=500,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "*",
                    },
                )
            except Exception as response_error:
                logger.error(
                    f"Failed to send error response: {response_error}",
                    traceback=traceback.format_exc(),
                )
                return web.Response(
                    text="Internal Server Error",
                    status=500,
                    headers={
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "*",
                    },
                )

    async def _create_health_check_app(self):
        """Create HTTP health check application for Cloud Run."""
        app = web.Application()

        async def health_check(request):
            """Health check endpoint for Cloud Run."""
            try:
                is_healthy = self.meili_client.health_check()
                if is_healthy:
                    return web.json_response(
                        {"status": "healthy", "service": "meilisearch-mcp"}, status=200
                    )
                else:
                    return web.json_response(
                        {
                            "status": "degraded",
                            "service": "meilisearch-mcp",
                            "reason": "meilisearch_unavailable",
                        },
                        status=503,
                    )
            except Exception as e:
                return web.json_response(
                    {"status": "error", "service": "meilisearch-mcp", "error": str(e)},
                    status=503,
                )

        async def root_handler(request):
            """Root endpoint - redirects to MCP SSE or health check based on Accept header."""
            accept = request.headers.get("Accept", "")
            if "text/event-stream" in accept or request.query_string == "sse":
                return await self._mcp_sse_endpoint(request)
            return await health_check(request)

        app.router.add_get("/", root_handler)
        app.router.add_get("/health", health_check)
        app.router.add_get("/ready", health_check)

        # MCP endpoints
        app.router.add_get("/mcp", self._mcp_sse_endpoint)
        app.router.add_post("/mcp", self._mcp_post_endpoint)
        app.router.add_get("/sse", self._mcp_sse_endpoint)
        app.router.add_post("/sse", self._mcp_post_endpoint)
        app.router.add_get("/v1/sse", self._mcp_sse_endpoint)
        app.router.add_post("/v1/sse", self._mcp_post_endpoint)
        app.router.add_post("/message", self._mcp_post_endpoint)
        app.router.add_post("/v1/message", self._mcp_post_endpoint)

        # CORS preflight handler
        async def options_handler(request):
            return web.Response(
                status=200,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Max-Age": "86400",
                },
            )

        app.router.add_options("/", options_handler)
        app.router.add_options("/mcp", options_handler)
        app.router.add_options("/sse", options_handler)
        app.router.add_options("/v1/sse", options_handler)
        app.router.add_options("/message", options_handler)
        app.router.add_options("/v1/message", options_handler)

        logger.info("Registered HTTP routes:")
        for route in app.router.routes():
            logger.info(f"  {route.method} {route.resource.canonical}")

        return app

    async def run(self):
        """Run the MCP server, optionally with HTTP health check for Cloud Run."""
        port = os.getenv("PORT")

        if port:
            port_num = int(port)
            logger.info(
                f"Cloud Run detected: Starting HTTP health check on port {port_num}"
            )

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

    async def _run_mcp_server(self):
        """Run the MCP server on stdio using FastMCP."""
        logger.info("Starting Meilisearch MCP server...")
        await mcp.run_async(transport="stdio")

    def cleanup(self):
        """Clean shutdown."""
        reset_context()


def main():
    """Main entry point."""
    url = os.getenv("MEILI_HTTP_ADDR", "http://localhost:7700")
    api_key = os.getenv("MEILI_MASTER_KEY")

    server = create_server(url, api_key)
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
