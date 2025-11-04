from typing import Dict, Any, List, Optional, Union
from urllib.parse import urlencode
import httpx

from .logging import MCPLogger

logger = MCPLogger()


class TaskManager:
    def __init__(self, url: str, api_key: Optional[str] = None):
        """Initialize TaskManager with Meilisearch URL and API key"""
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json"}
        if api_key and api_key.strip():
            self.headers["Authorization"] = f"Bearer {api_key.strip()}"

    def _build_query_params(
        self, parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Build query parameters from dict, converting lists to comma-separated strings"""
        if not parameters:
            return {}
        params = {}
        for key, value in parameters.items():
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                # Convert list to comma-separated string
                params[key] = ",".join(str(v) for v in value)
            else:
                params[key] = str(value)
        return params

    def _make_request(
        self, method: str, endpoint: str, params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Meilisearch API"""
        request_url = f"{self.url}{endpoint}"
        if params:
            request_url += f"?{urlencode(params)}"

        has_auth = "Authorization" in self.headers
        logger.debug(
            f"TaskManager request: {method} {endpoint}",
            url=request_url,
            method=method,
            has_auth_header=has_auth,
        )
        with httpx.Client() as client:
            response = client.request(
                method=method, url=request_url, headers=self.headers, timeout=30.0
            )
            if response.status_code == 401:
                logger.error(
                    "Authentication failed",
                    endpoint=endpoint,
                    has_auth_header=has_auth,
                    response_text=response.text[:200],
                )
            response.raise_for_status()
            return response.json()

    def get_task(self, task_uid: int) -> Dict[str, Any]:
        """Get information about a specific task using GET /tasks/{task_uid}"""
        try:
            endpoint = f"/tasks/{task_uid}"
            return self._make_request("GET", endpoint)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to get task: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to get task: {str(e)}")

    def get_tasks(self, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get list of tasks with optional filters using GET /tasks"""
        try:
            endpoint = "/tasks"
            params = self._build_query_params(parameters)
            return self._make_request("GET", endpoint, params)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to get tasks: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to get tasks: {str(e)}")

    def cancel_tasks(self, query_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel tasks based on query parameters using POST /tasks/cancel"""
        try:
            endpoint = "/tasks/cancel"
            params = self._build_query_params(query_parameters)
            return self._make_request("POST", endpoint, params)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to cancel tasks: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to cancel tasks: {str(e)}")

    def delete_tasks(self, query_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Delete tasks based on query parameters using DELETE /tasks"""
        try:
            endpoint = "/tasks"
            params = self._build_query_params(query_parameters)
            return self._make_request("DELETE", endpoint, params)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to delete tasks: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to delete tasks: {str(e)}")
