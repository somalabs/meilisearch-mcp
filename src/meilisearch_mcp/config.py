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
    PORT: Optional[int] = int(port) if (port := os.getenv("PORT")) else None

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

        # Validate numeric settings
        if cls.MAX_REQUEST_SIZE < 1024:  # At least 1KB
            errors.append("MAX_REQUEST_SIZE must be at least 1024 bytes")
        if cls.REQUEST_TIMEOUT < 1.0:
            errors.append("REQUEST_TIMEOUT must be at least 1.0 seconds")
        if cls.HTTP_MAX_CONNECTIONS < 1:
            errors.append("HTTP_MAX_CONNECTIONS must be at least 1")
        if cls.HEALTH_CHECK_TIMEOUT < 0.1:
            errors.append("HEALTH_CHECK_TIMEOUT must be at least 0.1 seconds")

        return errors

    @classmethod
    def get_cors_headers(cls) -> dict:
        """
        Get CORS headers based on configuration.

        Returns:
            Dictionary of CORS headers
        """
        if "*" in cls.CORS_ORIGINS:
            return {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Max-Age": "86400",
            }
        else:
            # In production, you'd typically check the Origin header
            # For now, return the first origin or use a default
            origin = cls.CORS_ORIGINS[0] if cls.CORS_ORIGINS else "*"
            return {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-MCP-Token",
                "Access-Control-Max-Age": "86400",
            }


# Global config instance
config = Config()
