from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import httpx

from .indexes import IndexManager
from .logging import MCPLogger

logger = MCPLogger()


@dataclass
class HealthStatus:
    """Detailed health status information"""

    is_healthy: bool
    database_size: int
    last_update: datetime
    indexes_count: int
    indexes_info: List[Dict[str, Any]]


@dataclass
class IndexMetrics:
    """Detailed index metrics"""

    number_of_documents: int
    field_distribution: Dict[str, int]
    is_indexing: bool
    index_size: Optional[int] = None


class MonitoringManager:
    """Enhanced monitoring and statistics for Meilisearch"""

    def __init__(self, url: str, api_key: Optional[str] = None):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json"}
        if api_key and api_key.strip():
            self.headers["Authorization"] = f"Bearer {api_key.strip()}"
        # Use IndexManager for getting indexes
        self.indexes = IndexManager(url, api_key)

    def _make_request(self, method: str, endpoint: str) -> Dict[str, Any]:
        """Make HTTP request to Meilisearch API"""
        request_url = f"{self.url}{endpoint}"
        has_auth = "Authorization" in self.headers
        logger.debug(
            f"MonitoringManager request: {method} {endpoint}",
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

    def get_health_status(self) -> HealthStatus:
        """Get comprehensive health status"""
        try:
            # Get various stats to build health picture
            stats = self._make_request("GET", "/stats")
            indexes = self.indexes.list_indexes()

            indexes_info = []
            for index_data in indexes.get("results", []):
                index_uid = index_data["uid"]
                index_stats = self._make_request("GET", f"/indexes/{index_uid}/stats")
                indexes_info.append(
                    {
                        "uid": index_uid,
                        "documents_count": index_stats["numberOfDocuments"],
                        "is_indexing": index_stats["isIndexing"],
                    }
                )

            return HealthStatus(
                is_healthy=True,
                database_size=stats["databaseSize"],
                last_update=datetime.fromisoformat(
                    stats["lastUpdate"].replace("Z", "+00:00")
                ),
                indexes_count=len(indexes.get("results", [])),
                indexes_info=indexes_info,
            )
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to get health status: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to get health status: {str(e)}")

    def get_index_metrics(self, index_uid: str) -> IndexMetrics:
        """Get detailed metrics for an index using GET /indexes/{index_uid}/stats"""
        try:
            endpoint = f"/indexes/{index_uid}/stats"
            stats = self._make_request("GET", endpoint)

            return IndexMetrics(
                number_of_documents=stats["numberOfDocuments"],
                field_distribution=stats["fieldDistribution"],
                is_indexing=stats["isIndexing"],
                index_size=stats.get("indexSize"),
            )
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to get index metrics: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to get index metrics: {str(e)}")

    def get_system_information(self) -> Dict[str, Any]:
        """Get system-level information"""
        try:
            version = self._make_request("GET", "/version")
            stats = self._make_request("GET", "/stats")

            return {
                "version": version,
                "database_size": stats["databaseSize"],
                "last_update": stats["lastUpdate"],
                "indexes": stats["indexes"],
            }
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to get system information: {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to get system information: {str(e)}")
