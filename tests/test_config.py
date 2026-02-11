"""
Tests for configuration management.
"""

import os
from unittest.mock import patch

from lucidity.config import (
    DEFAULT_CACHE_DIR,
    DEFAULT_CLONE_TIMEOUT_SECONDS,
    DEFAULT_CORS_ORIGINS,
    DEFAULT_FETCH_TIMEOUT_SECONDS,
    DEFAULT_MCP_PORT,
    Config,
    get_config,
)


def test_default_config():
    """Test that default configuration values are used when environment variables are not set."""
    with patch.dict(os.environ, {}, clear=True):
        config = Config.from_environment()

        assert config.cache_dir == DEFAULT_CACHE_DIR
        assert config.clone_timeout == DEFAULT_CLONE_TIMEOUT_SECONDS
        assert config.fetch_timeout == DEFAULT_FETCH_TIMEOUT_SECONDS
        assert config.cleanup_days == 7
        assert config.mcp_port == DEFAULT_MCP_PORT
        assert config.cors_origins == [DEFAULT_CORS_ORIGINS]
        assert config.ssh_verify is False


def test_config_from_environment():
    """Test that configuration values are loaded from environment variables."""
    env_vars = {
        "LUCIDITY_CACHE_DIR": "/custom/cache/dir",
        "LUCIDITY_CLONE_TIMEOUT": "600",
        "LUCIDITY_FETCH_TIMEOUT": "120",
        "LUCIDITY_CLEANUP_DAYS": "14",
        "LUCIDITY_MCP_PORT": "8080",
        "LUCIDITY_CORS_ORIGINS": "http://localhost:3000,http://example.com",
        "LUCIDITY_SSH_VERIFY": "true",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        config = Config.from_environment()

        assert config.cache_dir == "/custom/cache/dir"
        assert config.clone_timeout == 600
        assert config.fetch_timeout == 120
        assert config.cleanup_days == 14
        assert config.mcp_port == 8080
        assert config.cors_origins == ["http://localhost:3000", "http://example.com"]
        assert config.ssh_verify is True


def test_cors_wildcard():
    """Test that CORS wildcard is handled correctly."""
    with patch.dict(os.environ, {"LUCIDITY_CORS_ORIGINS": "*"}, clear=True):
        config = Config.from_environment()
        assert config.cors_origins == ["*"]


def test_cors_empty_string():
    """Test that empty CORS string results in empty list (not wildcard)."""
    with patch.dict(os.environ, {"LUCIDITY_CORS_ORIGINS": ""}, clear=True):
        config = Config.from_environment()
        # Empty string should result in empty list, not ["*"]
        assert config.cors_origins == []


def test_ssh_verify_variations():
    """Test different values for SSH verification flag."""
    # Test true values
    for true_value in ["true", "True", "TRUE", "1", "yes", "Yes"]:
        with patch.dict(os.environ, {"LUCIDITY_SSH_VERIFY": true_value}, clear=True):
            config = Config.from_environment()
            assert config.ssh_verify is True, f"Failed for value: {true_value}"

    # Test false values
    for false_value in ["false", "False", "FALSE", "0", "no", "No", ""]:
        with patch.dict(os.environ, {"LUCIDITY_SSH_VERIFY": false_value}, clear=True):
            config = Config.from_environment()
            assert config.ssh_verify is False, f"Failed for value: {false_value}"


def test_get_config_singleton():
    """Test that get_config returns a singleton instance."""
    # Clear any existing config
    import lucidity.config
    lucidity.config._config = None

    with patch.dict(os.environ, {"LUCIDITY_MCP_PORT": "9999"}, clear=True):
        config1 = get_config()
        config2 = get_config()

        # Should be the same instance
        assert config1 is config2
        assert config1.mcp_port == 9999
