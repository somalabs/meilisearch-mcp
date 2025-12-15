"""
Configuration management for production settings.

This module provides centralized configuration with environment variable support
and validation for production deployments.
"""

import os
from typing import Optional, List
from urllib.parse import urlparse


class Config:
    """Application configuration with validation."""

    # Meilisearch connection
    MEILI_HTTP_ADDR: str = os.getenv("MEILI_HTTP_ADDR", "http://localhost:7700")
    MEILI_MASTER_KEY: Optional[str] = os.getenv("MEILI_MASTER_KEY")

    # MCP server settings
    MCP_AUTH_TOKEN: Optional[str] = os.getenv("MCP_AUTH_TOKEN")

    # Parse PORT with error handling
    _port_str = os.getenv("PORT")
    PORT: Optional[int] = None
    if _port_str:
        try:
            PORT = int(_port_str)
        except ValueError:
            PORT = None

    # CORS settings
    CORS_ORIGINS: List[str] = (
        os.getenv("CORS_ORIGINS", "*").split(",")
        if os.getenv("CORS_ORIGINS") != "*"
        else ["*"]
    )

    # Request limits
    MAX_REQUEST_SIZE: int = int(
        os.getenv("MAX_REQUEST_SIZE", "10485760")
    )  # 10MB default
    REQUEST_TIMEOUT: float = float(os.getenv("REQUEST_TIMEOUT", "300.0"))  # 5 minutes

    # HTTP client settings
    HTTP_MAX_CONNECTIONS: int = int(os.getenv("HTTP_MAX_CONNECTIONS", "100"))
    HTTP_MAX_KEEPALIVE: int = int(os.getenv("HTTP_MAX_KEEPALIVE", "20"))
    HTTP_TIMEOUT: float = float(os.getenv("HTTP_TIMEOUT", "30.0"))

    # Logging
    LOG_DIR: Optional[str] = os.getenv(
        "LOG_DIR", os.path.expanduser("~/.meilisearch-mcp/logs")
    )
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # Health check settings
    HEALTH_CHECK_TIMEOUT: float = float(os.getenv("HEALTH_CHECK_TIMEOUT", "5.0"))

    @classmethod
    def validate(cls) -> List[str]:
        """
        Validate configuration and return list of errors.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Validate Meilisearch URL
        try:
            parsed = urlparse(cls.MEILI_HTTP_ADDR)
            if not parsed.scheme or not parsed.netloc:
                errors.append("MEILI_HTTP_ADDR must be a valid URL")
            if parsed.scheme not in ("http", "https"):
                errors.append("MEILI_HTTP_ADDR must use http or https scheme")
        except Exception as e:
            errors.append(f"Invalid MEILI_HTTP_ADDR: {e}")

        # Validate CORS origins
        if cls.CORS_ORIGINS != ["*"]:
            for origin in cls.CORS_ORIGINS:
                try:
                    parsed = urlparse(origin.strip())
                    if not parsed.scheme or not parsed.netloc:
                        errors.append(f"Invalid CORS origin: {origin}")
                except Exception:
                    errors.append(f"Invalid CORS origin format: {origin}")

        # Validate numeric settings (both minimum and maximum values)
        if cls.MAX_REQUEST_SIZE < 1024:  # At least 1KB
            errors.append("MAX_REQUEST_SIZE must be at least 1024 bytes")
        if cls.MAX_REQUEST_SIZE > 1024 * 1024 * 1024:  # Max 1GB
            errors.append("MAX_REQUEST_SIZE exceeds safe limit of 1GB")

        if cls.REQUEST_TIMEOUT < 1.0:
            errors.append("REQUEST_TIMEOUT must be at least 1.0 seconds")
        if cls.REQUEST_TIMEOUT > 3600.0:  # Max 1 hour
            errors.append("REQUEST_TIMEOUT exceeds safe limit of 1 hour")

        if cls.HTTP_MAX_CONNECTIONS < 1:
            errors.append("HTTP_MAX_CONNECTIONS must be at least 1")
        if cls.HTTP_MAX_CONNECTIONS > 10000:  # Reasonable upper limit
            errors.append("HTTP_MAX_CONNECTIONS exceeds safe limit of 10000")

        if cls.HTTP_MAX_KEEPALIVE < 1:
            errors.append("HTTP_MAX_KEEPALIVE must be at least 1")
        if cls.HTTP_MAX_KEEPALIVE > cls.HTTP_MAX_CONNECTIONS:
            errors.append("HTTP_MAX_KEEPALIVE cannot exceed HTTP_MAX_CONNECTIONS")

        if cls.HTTP_TIMEOUT < 0.1:
            errors.append("HTTP_TIMEOUT must be at least 0.1 seconds")
        if cls.HTTP_TIMEOUT > 600.0:  # Max 10 minutes
            errors.append("HTTP_TIMEOUT exceeds safe limit of 10 minutes")

        if cls.HEALTH_CHECK_TIMEOUT < 0.1:
            errors.append("HEALTH_CHECK_TIMEOUT must be at least 0.1 seconds")
        if cls.HEALTH_CHECK_TIMEOUT > 30.0:  # Max 30 seconds
            errors.append("HEALTH_CHECK_TIMEOUT exceeds safe limit of 30 seconds")

        return errors

    @classmethod
    def get_cors_headers(cls, request_origin: Optional[str] = None) -> dict:
        """
        Get CORS headers based on configuration and request origin.

        Args:
            request_origin: The Origin header from the incoming request

        Returns:
            Dictionary of CORS headers, or empty dict if origin not allowed
        """
        if "*" in cls.CORS_ORIGINS:
            # Allow all origins
            return {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Max-Age": "86400",
            }
        elif request_origin and request_origin in cls.CORS_ORIGINS:
            # Allow specific origin that matches
            return {
                "Access-Control-Allow-Origin": request_origin,
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-MCP-Token",
                "Access-Control-Expose-Headers": "Content-Type",
                "Access-Control-Max-Age": "86400",
            }
        else:
            # Origin not allowed, return empty headers
            return {}


# Global config instance
config = Config()
