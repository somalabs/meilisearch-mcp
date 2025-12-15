from typing import Dict, Any, List, Optional, Union
from urllib.parse import urlencode
import httpx

from .logging import MCPLogger
from .http_client import get_http_pool
from .config import config

logger = MCPLogger()


class DocumentManager:
    """Manage documents within Meilisearch indexes"""

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
        has_auth = bool(self.api_key)
        logger.debug(
            f"DocumentManager request: {method} {endpoint}",
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
        response = client.request(method=method, url=endpoint, headers=headers, json=json)
        if response.status_code == 401:
            logger.error(
                "Authentication failed",
                endpoint=endpoint,
                has_auth_header=has_auth,
                response_text=response.text[:200],
            )
        response.raise_for_status()
        return response.json()

    def get_documents(
        self,
        index_uid: str,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get documents from an index using POST /indexes/{index_uid}/documents/fetch"""
        try:
            endpoint = f"/indexes/{index_uid}/documents/fetch"
            body = {}
            if offset is not None:
                body["offset"] = offset
            if limit is not None:
                body["limit"] = limit
            if fields is not None:
                body["fields"] = fields

            return self._make_request("POST", endpoint, json=body if body else {})
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to get documents: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to get documents: {str(e)}")

    def get_document(
        self, index_uid: str, document_id: Union[str, int]
    ) -> Dict[str, Any]:
        """Get a single document using GET /indexes/{index_uid}/documents/{document_id}"""
        try:
            endpoint = f"/indexes/{index_uid}/documents/{document_id}"
            return self._make_request("GET", endpoint)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to get document: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to get document: {str(e)}")

    def add_documents(
        self,
        index_uid: str,
        documents: List[Dict[str, Any]],
        primary_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add or replace documents using PUT /indexes/{index_uid}/documents"""
        try:
            endpoint = f"/indexes/{index_uid}/documents"
            params = {}
            if primary_key:
                params["primaryKey"] = primary_key

            # Build endpoint with query parameters if needed
            endpoint_with_params = endpoint
            if params:
                endpoint_with_params += f"?{urlencode(params)}"

            http_pool = get_http_pool()
            client, headers = http_pool.get_client(
                self.url,
                self.api_key,
                timeout=config.HTTP_TIMEOUT,
            )
            response = client.put(endpoint_with_params, headers=headers, json=documents)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to add documents: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to add documents: {str(e)}")

    def update_documents(
        self, index_uid: str, documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Update documents using PATCH /indexes/{index_uid}/documents"""
        try:
            endpoint = f"/indexes/{index_uid}/documents"
            return self._make_request("PATCH", endpoint, json=documents)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to update documents: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to update documents: {str(e)}")

    def delete_document(
        self, index_uid: str, document_id: Union[str, int]
    ) -> Dict[str, Any]:
        """Delete a single document using DELETE /indexes/{index_uid}/documents/{document_id}"""
        try:
            endpoint = f"/indexes/{index_uid}/documents/{document_id}"
            return self._make_request("DELETE", endpoint)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to delete document: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to delete document: {str(e)}")

    def delete_documents(
        self, index_uid: str, document_ids: List[Union[str, int]]
    ) -> Dict[str, Any]:
        """Delete multiple documents by ID using POST /indexes/{index_uid}/documents/delete-batch"""
        try:
            endpoint = f"/indexes/{index_uid}/documents/delete-batch"
            return self._make_request("POST", endpoint, json=document_ids)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to delete documents: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to delete documents: {str(e)}")

    def delete_all_documents(self, index_uid: str) -> Dict[str, Any]:
        """Delete all documents using DELETE /indexes/{index_uid}/documents"""
        try:
            endpoint = f"/indexes/{index_uid}/documents"
            return self._make_request("DELETE", endpoint)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to delete all documents: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to delete all documents: {str(e)}")
