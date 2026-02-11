"""
Configuration management for Lucidity MCP.

This module provides centralized configuration management using environment variables
with sensible defaults for development and production deployment.
"""

import os
from dataclasses import dataclass


# Constants for default values
DEFAULT_CACHE_DIR = "/tmp/lucidity-mcp-repos"
DEFAULT_CLONE_TIMEOUT_SECONDS = 300
DEFAULT_FETCH_TIMEOUT_SECONDS = 60
DEFAULT_CLEANUP_DAYS = 7
DEFAULT_MCP_PORT = 6969
MIN_CODE_CHANGE_BYTES = 10
DEFAULT_CORS_ORIGINS = "*"


@dataclass
class Config:
    """Configuration settings for Lucidity MCP server."""

    # Repository caching configuration
    cache_dir: str
    clone_timeout: int
    fetch_timeout: int
    cleanup_days: int

    # Server configuration
    mcp_port: int
    cors_origins: list[str]

    # Security configuration
    ssh_verify: bool

    @classmethod
    def from_environment(cls) -> "Config":
        """Create configuration from environment variables.

        Returns:
            Config instance populated from environment variables with fallback to defaults
        """
        # Parse CORS origins - can be comma-separated list or "*"
        cors_origins_str = os.environ.get("LUCIDITY_CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
        if cors_origins_str == "*":
            cors_origins = ["*"]
        else:
            cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

        return cls(
            cache_dir=os.environ.get("LUCIDITY_CACHE_DIR", DEFAULT_CACHE_DIR),
            clone_timeout=int(os.environ.get("LUCIDITY_CLONE_TIMEOUT", str(DEFAULT_CLONE_TIMEOUT_SECONDS))),
            fetch_timeout=int(os.environ.get("LUCIDITY_FETCH_TIMEOUT", str(DEFAULT_FETCH_TIMEOUT_SECONDS))),
            cleanup_days=int(os.environ.get("LUCIDITY_CLEANUP_DAYS", str(DEFAULT_CLEANUP_DAYS))),
            mcp_port=int(os.environ.get("LUCIDITY_MCP_PORT", str(DEFAULT_MCP_PORT))),
            cors_origins=cors_origins,
            ssh_verify=os.environ.get("LUCIDITY_SSH_VERIFY", "false").lower() in ("true", "1", "yes"),
        )


# Global configuration instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance.

    Returns:
        Global Config instance, created from environment on first call
    """
    global _config
    if _config is None:
        _config = Config.from_environment()
    return _config
