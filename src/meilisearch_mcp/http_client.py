"""
HTTP client with connection pooling for production use.

This module provides a shared HTTP client instance with connection pooling
to improve performance and resource management.
"""

import httpx
from typing import Optional
import threading
from contextlib import contextmanager


class HTTPClientPool:
    """
    Thread-safe HTTP client pool for managing persistent connections.

    This class provides a singleton pattern for httpx.Client instances
    with connection pooling enabled for better performance.
    """

    _instance: Optional["HTTPClientPool"] = None
    _lock = threading.Lock()
    _clients: dict[str, httpx.Client] = {}
    _client_locks: dict[str, threading.Lock] = {}

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def get_client(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
    ) -> httpx.Client:
        """
        Get or create an HTTP client for a specific base URL.

        Args:
            base_url: Base URL for the client
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
            max_connections: Maximum number of connections in pool
            max_keepalive_connections: Maximum keepalive connections

        Returns:
            httpx.Client instance with connection pooling
        """
        # Create a unique key for this client configuration
        client_key = f"{base_url}:{api_key or 'no-key'}:{timeout}"

        if client_key not in self._clients:
            with self._lock:
                if client_key not in self._clients:
                    # Create client with connection pooling
                    limits = httpx.Limits(
                        max_connections=max_connections,
                        max_keepalive_connections=max_keepalive_connections,
                    )
                    timeout_config = httpx.Timeout(timeout, connect=10.0)

                    headers = {"Content-Type": "application/json"}
                    if api_key and api_key.strip():
                        headers["Authorization"] = f"Bearer {api_key.strip()}"

                    self._clients[client_key] = httpx.Client(
                        base_url=base_url,
                        headers=headers,
                        timeout=timeout_config,
                        limits=limits,
                        http2=True,  # Enable HTTP/2 for better performance
                    )
                    self._client_locks[client_key] = threading.Lock()

        return self._clients[client_key]

    def close_all(self) -> None:
        """Close all HTTP clients and clean up resources."""
        with self._lock:
            for client in self._clients.values():
                try:
                    client.close()
                except Exception:
                    pass
            self._clients.clear()
            self._client_locks.clear()

    @contextmanager
    def request_context(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Context manager for making HTTP requests with proper resource management.

        Usage:
            with http_pool.request_context(url, api_key) as client:
                response = client.get("/endpoint")
        """
        client = self.get_client(base_url, api_key, timeout)
        try:
            yield client
        finally:
            # Client is reused, no cleanup needed
            pass


# Global singleton instance
_http_pool: Optional[HTTPClientPool] = None


def get_http_pool() -> HTTPClientPool:
    """Get the global HTTP client pool instance."""
    global _http_pool
    if _http_pool is None:
        _http_pool = HTTPClientPool()
    return _http_pool
