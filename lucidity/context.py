"""
Lucidity MCP Instance.

This module provides the MCP server instance for the Lucidity application.
It's separated to avoid cyclic imports between server.py and tools/resources modules.
"""

import logging

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("lucidity")


# Create the MCP server with lifespan
mcp = FastMCP(
    name="Lucidity-MCP",
    instructions="AI Powered Code Review Tool for MCP",
    dependencies=["rich", "python-dotenv"],
)

# Explicitly define what should be imported
__all__ = ["mcp"]
