from typing import Dict, Any, List, Optional, Union
from urllib.parse import urlencode
import httpx

from .logging import MCPLogger

logger = MCPLogger()


class KeyManager:
    """Manage Meilisearch API keys"""

    def __init__(self, url: str, api_key: Optional[str] = None):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json"}
        if api_key and api_key.strip():
            self.headers["Authorization"] = f"Bearer {api_key.strip()}"

    def _make_request(
        self,
        method: str,
        endpoint: str,
        json: Optional[Union[Dict[str, Any], List[Any]]] = None,
    ) -> Union[Dict[str, Any], None]:
        """Make HTTP request to Meilisearch API"""
        request_url = f"{self.url}{endpoint}"
        has_auth = "Authorization" in self.headers
        logger.debug(
            f"KeyManager request: {method} {endpoint}",
            url=request_url,
            method=method,
            has_auth_header=has_auth,
        )
        with httpx.Client() as client:
            response = client.request(
                method=method,
                url=request_url,
                headers=self.headers,
                json=json,
                timeout=30.0,
            )
            if response.status_code == 401:
                logger.error(
                    "Authentication failed",
                    endpoint=endpoint,
                    has_auth_header=has_auth,
                    response_text=response.text[:200],
                )
            response.raise_for_status()
            # DELETE returns 204 No Content, so return None
            if response.status_code == 204:
                return None
            return response.json()

    def get_keys(self, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get list of API keys using GET /keys"""
        try:
            endpoint = "/keys"
            params = {}
            if parameters:
                # Handle offset and limit from parameters
                if "offset" in parameters:
                    params["offset"] = parameters["offset"]
                if "limit" in parameters:
                    params["limit"] = parameters["limit"]

            request_url = f"{self.url}{endpoint}"
            if params:
                request_url += f"?{urlencode(params)}"

            with httpx.Client() as client:
                response = client.request(
                    method="GET", url=request_url, headers=self.headers, timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to get keys: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to get keys: {str(e)}")

    def get_key(self, key: str) -> Dict[str, Any]:
        """Get information about a specific key using GET /keys/{key_or_uid}"""
        try:
            endpoint = f"/keys/{key}"
            return self._make_request("GET", endpoint)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to get key: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to get key: {str(e)}")

    def create_key(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new API key using POST /keys"""
        try:
            endpoint = "/keys"
            # Build body according to API spec
            body = {
                "actions": options["actions"],
                "indexes": options["indexes"],
                "expiresAt": options.get("expiresAt"),
            }
            # Optional fields
            if "name" in options:
                body["name"] = options["name"]
            if "description" in options:
                body["description"] = options["description"]
            if "uid" in options:
                body["uid"] = options["uid"]

            return self._make_request("POST", endpoint, json=body)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to create key: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to create key: {str(e)}")

    def update_key(self, key: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing API key using PATCH /keys/{key_or_uid}"""
        try:
            endpoint = f"/keys/{key}"
            # Only name and description can be updated according to API spec
            body = {}
            if "name" in options:
                body["name"] = options["name"]
            if "description" in options:
                body["description"] = options["description"]

            return self._make_request("PATCH", endpoint, json=body)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to update key: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to update key: {str(e)}")

    def delete_key(self, key: str) -> None:
        """Delete an API key using DELETE /keys/{key_or_uid}"""
        try:
            endpoint = f"/keys/{key}"
            self._make_request("DELETE", endpoint)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to delete key: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to delete key: {str(e)}")
