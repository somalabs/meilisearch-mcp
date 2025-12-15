from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import httpx

from .logging import MCPLogger

logger = MCPLogger()


@dataclass
class SearchSettings:
    displayedAttributes: Optional[List[str]] = None
    searchableAttributes: Optional[List[str]] = None
    filterableAttributes: Optional[List[str]] = None
    sortableAttributes: Optional[List[str]] = None
    rankingRules: Optional[List[str]] = None
    stopWords: Optional[List[str]] = None
    synonyms: Optional[Dict[str, List[str]]] = None
    distinctAttribute: Optional[str] = None
    typoTolerance: Optional[Dict[str, Any]] = None
    faceting: Optional[Dict[str, Any]] = None
    pagination: Optional[Dict[str, Any]] = None


class SettingsManager:
    """Manage Meilisearch index settings"""

    def __init__(self, url: str, api_key: Optional[str] = None):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json"}
        if api_key and api_key.strip():
            self.headers["Authorization"] = f"Bearer {api_key.strip()}"

    def _make_request(
        self, method: str, endpoint: str, json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Meilisearch API"""
        request_url = f"{self.url}{endpoint}"
        has_auth = "Authorization" in self.headers
        logger.debug(
            f"SettingsManager request: {method} {endpoint}",
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
            return response.json()

    def get_settings(self, index_uid: str) -> Dict[str, Any]:
        """Get all settings for an index using GET /indexes/{index_uid}/settings"""
        try:
            endpoint = f"/indexes/{index_uid}/settings"
            return self._make_request("GET", endpoint)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to get settings: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to get settings: {str(e)}")

    def update_settings(
        self, index_uid: str, settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update settings for an index using PATCH /indexes/{index_uid}/settings"""
        try:
            endpoint = f"/indexes/{index_uid}/settings"
            return self._make_request("PATCH", endpoint, json=settings)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to update settings: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to update settings: {str(e)}")

    def reset_settings(self, index_uid: str) -> Dict[str, Any]:
        """Reset settings to default values using DELETE /indexes/{index_uid}/settings"""
        try:
            endpoint = f"/indexes/{index_uid}/settings"
            return self._make_request("DELETE", endpoint)
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to reset settings: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to reset settings: {str(e)}")
