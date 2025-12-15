from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
import httpx
import json

from .logging import MCPLogger

logger = MCPLogger()


class ChatManager:
    def __init__(self, url: str, api_key: Optional[str] = None):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json"}
        if api_key and api_key.strip():
            self.headers["Authorization"] = f"Bearer {api_key.strip()}"

    async def create_chat_completion(
        self,
        workspace_uid: str,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        stream: bool = True,
    ) -> str:
        """Create a chat completion using POST /chats/{workspace_uid}/chat/completions"""
        try:
            logger.info(f"Creating chat completion for workspace: {workspace_uid}")

            endpoint = f"/chats/{workspace_uid}/chat/completions"
            request_url = f"{self.url}{endpoint}"

            body = {
                "model": model,
                "messages": messages,
                "stream": stream,
            }

            has_auth = "Authorization" in self.headers
            logger.debug(
                "Creating chat completion request",
                url=request_url,
                workspace_uid=workspace_uid,
                has_auth_header=has_auth,
            )
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    request_url,
                    headers=self.headers,
                    json=body,
                    timeout=60.0,
                ) as response:
                    if response.status_code == 401:
                        logger.error(
                            "Authentication failed in create_chat_completion",
                            workspace_uid=workspace_uid,
                            has_auth_header=has_auth,
                        )
                    response.raise_for_status()

                    # Handle SSE streaming response
                    content_parts = []
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                if "choices" in chunk and chunk["choices"]:
                                    choice = chunk["choices"][0]
                                    if (
                                        "delta" in choice
                                        and "content" in choice["delta"]
                                    ):
                                        content_parts.append(choice["delta"]["content"])
                            except json.JSONDecodeError:
                                continue

            full_response = "".join(content_parts)
            logger.info(
                f"Chat completion created successfully for workspace: {workspace_uid}"
            )
            return full_response

        except httpx.HTTPStatusError as e:
            error_msg = (
                f"Meilisearch API error in create_chat_completion: {e.response.text}"
            )
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Error in create_chat_completion: {e}")
            raise

    async def get_chat_workspaces(
        self, offset: Optional[int] = None, limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get list of chat workspaces using GET /chats"""
        try:
            logger.info(f"Getting chat workspaces (offset={offset}, limit={limit})")
            endpoint = "/chats"
            params = {}
            if offset is not None:
                params["offset"] = offset
            if limit is not None:
                params["limit"] = limit

            request_url = f"{self.url}{endpoint}"
            if params:
                request_url += f"?{urlencode(params)}"

            has_auth = "Authorization" in self.headers
            logger.debug(
                "Getting chat workspaces",
                url=request_url,
                has_auth_header=has_auth,
            )
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method="GET", url=request_url, headers=self.headers, timeout=30.0
                )
                if response.status_code == 401:
                    logger.error(
                        "Authentication failed in get_chat_workspaces",
                        has_auth_header=has_auth,
                    )
                response.raise_for_status()
                workspaces = response.json()
                logger.info(
                    f"Retrieved {len(workspaces.get('results', []))} chat workspaces"
                )
                return workspaces
        except httpx.HTTPStatusError as e:
            error_msg = (
                f"Meilisearch API error in get_chat_workspaces: {e.response.text}"
            )
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Error in get_chat_workspaces: {e}")
            raise

    async def get_chat_workspace_settings(self, workspace_uid: str) -> Dict[str, Any]:
        """Get chat workspace settings using GET /chats/{workspace_uid}/settings"""
        try:
            logger.info(f"Getting settings for chat workspace: {workspace_uid}")
            endpoint = f"/chats/{workspace_uid}/settings"
            request_url = f"{self.url}{endpoint}"

            has_auth = "Authorization" in self.headers
            logger.debug(
                "Getting chat workspace settings",
                url=request_url,
                workspace_uid=workspace_uid,
                has_auth_header=has_auth,
            )
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method="GET", url=request_url, headers=self.headers, timeout=30.0
                )
                if response.status_code == 401:
                    logger.error(
                        "Authentication failed in get_chat_workspace_settings",
                        workspace_uid=workspace_uid,
                        has_auth_header=has_auth,
                    )
                response.raise_for_status()
                settings = response.json()
                logger.info(f"Retrieved settings for workspace: {workspace_uid}")
                return settings
        except httpx.HTTPStatusError as e:
            error_msg = f"Meilisearch API error in get_chat_workspace_settings: {e.response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Error in get_chat_workspace_settings: {e}")
            raise

    async def update_chat_workspace_settings(
        self, workspace_uid: str, settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update chat workspace settings using PATCH /chats/{workspace_uid}/settings"""
        try:
            logger.info(f"Updating settings for chat workspace: {workspace_uid}")
            endpoint = f"/chats/{workspace_uid}/settings"
            request_url = f"{self.url}{endpoint}"

            has_auth = "Authorization" in self.headers
            logger.debug(
                "Updating chat workspace settings",
                url=request_url,
                workspace_uid=workspace_uid,
                has_auth_header=has_auth,
            )
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method="PATCH",
                    url=request_url,
                    headers=self.headers,
                    json=settings,
                    timeout=30.0,
                )
                if response.status_code == 401:
                    logger.error(
                        "Authentication failed in update_chat_workspace_settings",
                        workspace_uid=workspace_uid,
                        has_auth_header=has_auth,
                    )
                response.raise_for_status()
                updated_settings = response.json()
                logger.info(f"Updated settings for workspace: {workspace_uid}")
                return updated_settings
        except httpx.HTTPStatusError as e:
            error_msg = f"Meilisearch API error in update_chat_workspace_settings: {e.response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Error in update_chat_workspace_settings: {e}")
            raise

    async def reset_chat_workspace_settings(self, workspace_uid: str) -> Dict[str, Any]:
        """Reset chat workspace settings using DELETE /chats/{workspace_uid}/settings"""
        try:
            logger.info(f"Resetting settings for chat workspace: {workspace_uid}")
            endpoint = f"/chats/{workspace_uid}/settings"
            request_url = f"{self.url}{endpoint}"

            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method="DELETE", url=request_url, headers=self.headers, timeout=30.0
                )
                response.raise_for_status()
                settings = response.json()
                logger.info(f"Reset settings for workspace: {workspace_uid}")
                return settings
        except httpx.HTTPStatusError as e:
            error_msg = f"Meilisearch API error in reset_chat_workspace_settings: {e.response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Error in reset_chat_workspace_settings: {e}")
            raise
