"""
HTTP client with connection pooling for production use.

This module provides a shared HTTP client instance with connection pooling
to improve performance and resource management.
"""

import httpx
from typing import Optional, Dict
import threading
import logging


class HTTPClientPool:
    """
    Thread-safe HTTP client pool for managing persistent connections.

    This class provides a singleton pattern for httpx.Client instances
    with connection pooling enabled for better performance.
    """

    _instance: Optional["HTTPClientPool"] = None
    _lock = threading.Lock()
    _clients: Dict[str, httpx.Client] = {}
    _client_locks: Dict[str, threading.Lock] = {}

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def _get_headers(self, api_key: Optional[str] = None) -> Dict[str, str]:
        """
        Get headers for requests, including authentication if provided.

        Args:
            api_key: Optional API key for authentication

        Returns:
            Dictionary of headers
        """
        headers = {"Content-Type": "application/json"}
        if api_key and api_key.strip():
            headers["Authorization"] = f"Bearer {api_key.strip()}"
        return headers

    def get_client(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
    ) -> tuple[httpx.Client, Dict[str, str]]:
        """
        Get or create an HTTP client for a specific base URL.

        This method no longer includes api_key in the client_key to prevent
        memory leaks when API keys are rotated. Instead, headers are returned
        separately and should be passed per-request.

        Args:
            base_url: Base URL for the client
            api_key: Optional API key for authentication (used in returned headers)
            timeout: Request timeout in seconds
            max_connections: Maximum number of connections in pool
            max_keepalive_connections: Maximum keepalive connections

        Returns:
            Tuple of (httpx.Client instance, headers dict with auth)
        """
        # Create a unique key based only on base_url and timeout
        # API key is NOT included to prevent memory leaks on key rotation
        client_key = f"{base_url}:{timeout}"

        if client_key not in self._clients:
            with self._lock:
                if client_key not in self._clients:
                    # Create client with connection pooling
                    limits = httpx.Limits(
                        max_connections=max_connections,
                        max_keepalive_connections=max_keepalive_connections,
                    )
                    timeout_config = httpx.Timeout(timeout, connect=10.0)

                    self._clients[client_key] = httpx.Client(
                        base_url=base_url,
                        timeout=timeout_config,
                        limits=limits,
                        http2=True,  # Enable HTTP/2 for better performance
                    )
                    self._client_locks[client_key] = threading.Lock()

        # Return client and headers separately
        headers = self._get_headers(api_key)
        return self._clients[client_key], headers

    def close_all(self) -> None:
        """Close all HTTP clients and clean up resources."""
        with self._lock:
            for client in self._clients.values():
                try:
                    client.close()
                except Exception as e:
                    # Log but don't fail on cleanup errors
                    logging.error(f"Error closing HTTP client: {e}")
            self._clients.clear()
            self._client_locks.clear()


# Global singleton instance
_http_pool: Optional[HTTPClientPool] = None


def get_http_pool() -> HTTPClientPool:
    """Get the global HTTP client pool instance."""
    global _http_pool
    if _http_pool is None:
        _http_pool = HTTPClientPool()
    return _http_pool
