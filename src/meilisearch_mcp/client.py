import httpx
from typing import Optional, Dict, Any, List

from .indexes import IndexManager
from .documents import DocumentManager
from .tasks import TaskManager
from .settings import SettingsManager
from .keys import KeyManager
from .logging import MCPLogger
from .monitoring import MonitoringManager

logger = MCPLogger()


class MeilisearchClient:
    def __init__(
        self, url: str = "http://localhost:7700", api_key: Optional[str] = None
    ):
        """Initialize Meilisearch client"""
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.indexes = IndexManager(url, api_key)
        self.documents = DocumentManager(url, api_key)
        self.settings = SettingsManager(url, api_key)
        self.tasks = TaskManager(url, api_key)
        self.keys = KeyManager(url, api_key)
        self.monitoring = MonitoringManager(url, api_key)
        # Store headers for HTTP requests
        self.headers = {"Content-Type": "application/json"}
        if api_key and api_key.strip():
            self.headers["Authorization"] = f"Bearer {api_key.strip()}"
            logger.debug(
                f"MeilisearchClient initialized with auth",
                url=self.url,
                has_api_key=True,
                api_key_length=len(api_key.strip()),
            )
        else:
            logger.warning(
                "MeilisearchClient initialized without API key - protected endpoints may fail",
                url=self.url,
            )

    def health_check(self) -> bool:
        """Check if Meilisearch is healthy using GET /health"""
        try:
            request_url = f"{self.url.rstrip('/')}/health"
            with httpx.Client() as client:
                response = client.request(
                    method="GET", url=request_url, headers=self.headers, timeout=5.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("status") == "available"
        except Exception:
            return False

    def get_version(self) -> Dict[str, Any]:
        """Get Meilisearch version information using GET /version"""
        try:
            request_url = f"{self.url.rstrip('/')}/version"
            logger.debug(
                "Making version request",
                url=request_url,
                has_auth_header="Authorization" in self.headers,
                headers_keys=list(self.headers.keys()),
            )
            with httpx.Client() as client:
                response = client.request(
                    method="GET", url=request_url, headers=self.headers, timeout=30.0
                )
                logger.debug(
                    "Version response received",
                    status_code=response.status_code,
                    has_auth_header="Authorization" in self.headers,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "Failed to get version - HTTP error",
                status_code=e.response.status_code,
                response_text=e.response.text[:200],
                has_auth_header="Authorization" in self.headers,
            )
            raise Exception(f"Failed to get version: {e.response.text}")
        except Exception as e:
            logger.error("Failed to get version - exception", error=str(e))
            raise Exception(f"Failed to get version: {str(e)}")

    def get_stats(self) -> Dict[str, Any]:
        """Get database stats using GET /stats"""
        try:
            request_url = f"{self.url.rstrip('/')}/stats"
            with httpx.Client() as client:
                response = client.request(
                    method="GET", url=request_url, headers=self.headers, timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to get stats: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to get stats: {str(e)}")

    def search(
        self,
        query: str,
        index_uid: Optional[str] = None,
        limit: Optional[int] = 20,
        offset: Optional[int] = 0,
        filter: Optional[str] = None,
        sort: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Search through Meilisearch indices.
        If index_uid is provided, search in that specific index.
        If not provided, search across all available indices.
        """
        try:
            # Prepare search parameters, removing None values
            search_body = {
                "q": query,
                "limit": limit if limit is not None else 20,
                "offset": offset if offset is not None else 0,
            }

            if filter is not None:
                search_body["filter"] = filter
            if sort is not None:
                search_body["sort"] = sort

            # Add any additional parameters
            search_body.update({k: v for k, v in kwargs.items() if v is not None})

            if index_uid:
                # Search in specific index using POST /indexes/{index_uid}/search
                endpoint = f"/indexes/{index_uid}/search"
                request_url = f"{self.url}{endpoint}"

                with httpx.Client() as client:
                    response = client.request(
                        method="POST",
                        url=request_url,
                        headers=self.headers,
                        json=search_body,
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    return response.json()
            else:
                # Search across all indices
                results = {}
                indexes = self.indexes.list_indexes()

                for index_data in indexes["results"]:
                    try:
                        index_uid = index_data["uid"]
                        endpoint = f"/indexes/{index_uid}/search"
                        request_url = f"{self.url}{endpoint}"

                        with httpx.Client() as client:
                            search_response = client.request(
                                method="POST",
                                url=request_url,
                                headers=self.headers,
                                json=search_body,
                                timeout=30.0,
                            )
                            search_response.raise_for_status()
                            search_result = search_response.json()
                            if search_result.get("hits"):  # Only include indices with matches
                                results[index_uid] = search_result
                    except httpx.HTTPStatusError as e:
                        logger.warning(
                            f"Failed to search index {index_data.get('uid', 'unknown')}: {e.response.text}"
                        )
                        continue
                    except Exception as e:
                        logger.warning(f"Failed to search index {index_data.get('uid', 'unknown')}: {str(e)}")
                        continue

                return {"multi_index": True, "query": query, "results": results}

        except httpx.HTTPStatusError as e:
            raise Exception(f"Search failed: {e.response.text}")
        except Exception as e:
            raise Exception(f"Search failed: {str(e)}")

    def get_indexes(self) -> Dict[str, Any]:
        """Get all indexes"""
        # list_indexes already returns the correct format from the API
        return self.indexes.list_indexes()
