from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from urllib.parse import urlencode
import httpx

from .logging import MCPLogger
from .http_client import get_http_pool
from .config import config

logger = MCPLogger()


@dataclass
class IndexConfig:
    """Index configuration model"""

    uid: str
    primary_key: Optional[str] = None


class IndexManager:
    """Manage Meilisearch indexes"""

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
    ) -> Dict[str, Any]:
        """Make HTTP request to Meilisearch API using connection pool"""
        # Log request details (without exposing sensitive data)
        has_auth = "Authorization" in self.headers
        logger.debug(
            f"IndexManager request: {method} {endpoint}",
            url=self.url,
            method=method,
            has_auth_header=has_auth,
        )
        http_pool = get_http_pool()
        client, headers = http_pool.get_client(
            self.url,
            self.api_key,
            timeout=config.HTTP_TIMEOUT,
        )
        response = client.request(method=method, url=endpoint, json=json, headers=headers)
        if response.status_code == 401:
            logger.error(
                "Authentication failed",
                endpoint=endpoint,
                has_auth_header=has_auth,
                response_text=response.text[:200],
            )
        response.raise_for_status()
        return response.json()

    def create_index(
        self, uid: str, primary_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new index using POST /indexes"""
        try:
            endpoint = "/indexes"
            body = {"uid": uid}
            if primary_key is not None:
                body["primaryKey"] = primary_key
            return self._make_request("POST", endpoint, json=body)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to create index: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to create index: {str(e)}")

    def get_index(self, uid: str) -> Dict[str, Any]:
        """Get index information using GET /indexes/{index_uid}"""
        try:
            endpoint = f"/indexes/{uid}"
            return self._make_request("GET", endpoint)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to get index: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to get index: {str(e)}")

    def list_indexes(
        self, offset: Optional[int] = None, limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """List all indexes using GET /indexes"""
        try:
            endpoint = "/indexes"
            params = {}
            if offset is not None:
                params["offset"] = offset
            if limit is not None:
                params["limit"] = limit

            endpoint_with_params = endpoint
            if params:
                endpoint_with_params += f"?{urlencode(params)}"

            http_pool = get_http_pool()
            client, headers = http_pool.get_client(
                self.url,
                self.api_key,
                timeout=config.HTTP_TIMEOUT,
            )
            response = client.get(endpoint_with_params, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to list indexes: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to list indexes: {str(e)}")

    def delete_index(self, uid: str) -> Dict[str, Any]:
        """Delete an index using DELETE /indexes/{index_uid}"""
        try:
            endpoint = f"/indexes/{uid}"
            return self._make_request("DELETE", endpoint)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to delete index: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to delete index: {str(e)}")

    def update_index(
        self, uid: str, primary_key: Optional[str] = None, new_uid: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update index using PATCH /indexes/{index_uid}"""
        try:
            endpoint = f"/indexes/{uid}"
            body = {}
            if primary_key is not None:
                body["primaryKey"] = primary_key
            if new_uid is not None:
                body["uid"] = new_uid
            return self._make_request("PATCH", endpoint, json=body)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to update index: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to update index: {str(e)}")

    def swap_indexes(self, indexes: List[List[str]]) -> Dict[str, Any]:
        """Swap indexes using POST /swap-indexes"""
        try:
            endpoint = "/swap-indexes"
            # Convert List[List[str]] to API format: List[Dict[str, Any]]
            # Each inner list represents a pair of indexes to swap
            swap_payload = []
            for index_pair in indexes:
                if len(index_pair) != 2:
                    raise ValueError(
                        "Each index pair must contain exactly two index UIDs"
                    )
                swap_payload.append({"indexes": index_pair, "rename": False})
            return self._make_request("POST", endpoint, json=swap_payload)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to swap indexes: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to swap indexes: {str(e)}")
