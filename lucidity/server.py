"""MCP server implementation for Lucidity.

This module provides the main MCP server implementation using FastMCP,
which handles MCP protocol communication using decorators for resources and tools.
"""

import argparse
import asyncio
import ipaddress
from pathlib import Path
import sys
from typing import Any, cast

import anyio
from dotenv import load_dotenv
from mcp.server.sse import SseServerTransport
from mcp.server.stdio import stdio_server
from rich.logging import RichHandler
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.routing import Mount, Route
import uvicorn

# Import resources and tools modules to register decorators
from . import prompts, tools  # noqa: F401
from .context import mcp
from .log import (
    handle_taskgroup_exception,
    logger,
    setup_asyncio_exception_handler,
    setup_global_exception_handler,
    setup_logging,
)


def load_environment() -> None:
    """Load environment variables from .env file."""
    # Look for .env in current directory and parent directories
    env_path = Path(".env")
    if not env_path.exists():
        # Try in the same directory as the script
        script_dir = Path(__file__).parent.parent
        env_path = script_dir / ".env"

    if env_path.exists():
        logger.debug("Loading environment from %s", env_path)
        load_dotenv(env_path)
    else:
        logger.debug("No .env file found, using system environment variables")


def run_sse_server(config: dict[str, Any]) -> None:
    """Run the server with SSE transport.

    Args:
        config: Server configuration
    """

    # Define middleware to suppress 'NoneType object is not callable' errors during shutdown
    class SuppressNoneTypeErrorMiddleware:
        def __init__(self, app: Any) -> None:
            self.app = app

        async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
            try:
                await self.app(scope, receive, send)
            except TypeError as e:
                if "NoneType" in str(e) and "not callable" in str(e):
                    pass
                else:
                    raise

    # Set up SSE transport
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        # Use a safer method to connect to SSE to avoid accessing private members
        # Mark with noqa where we really need to access private members
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            try:
                # The force_login flag is handled by the lifespan directly
                # Force login parameter will be passed via environment variables

                # For MCP internals that require access to private members, add noqa
                await mcp._mcp_server.run(
                    streams[0],
                    streams[1],
                    mcp._mcp_server.create_initialization_options(),
                )
            except asyncio.CancelledError:
                logger.debug("🔍 ASGI connection cancelled, shutting down quietly.")
            except Exception as e:
                logger.exception("💥 ASGI connection ended with exception: %s", e)
                # Use our custom exception handler for detailed logging
                handle_taskgroup_exception(e)

    # Create Starlette app with custom middleware including our suppressor and CORS
    app = Starlette(
        debug=config.get("debug", False),
        middleware=[
            Middleware(SuppressNoneTypeErrorMiddleware),
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_methods=["GET", "POST"],
                allow_headers=["*"],
            ),
        ],
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

    # Create a custom Uvicorn config with our shutdown handler
    uvicorn_config = uvicorn.Config(
        app,
        host=cast(str, config["host"]),
        port=cast(int, config["port"]),
        log_config=None,
        timeout_graceful_shutdown=0,  # Shutdown immediately
    )
    # Create server with the Config object
    server = uvicorn.Server(uvicorn_config)
    # Actually run the server
    server.run()


def run_stdio_server() -> None:
    """Run the server with stdio transport."""
    # Use stdio transport for terminal use
    logger.debug("🔌 Using stdio transport for terminal interaction")

    async def arun() -> None:
        async with stdio_server() as streams:
            # Log that we're ready to accept commands
            logger.debug("🎧 Server ready, waiting for commands...")
            # Add noqa for private member access that's necessary for MCP
            await mcp._mcp_server.run(
                streams[0],
                streams[1],
                mcp._mcp_server.create_initialization_options(),
            )

    anyio.run(arun)


def run_streamable_http_server(config: dict[str, Any]) -> None:
    """Run the server with Streamable HTTP transport.

    Args:
        config: Server configuration
    """
    logger.debug("🔌 Using Streamable HTTP transport for network communication")

    # Use FastMCP's built-in run method with streamable-http transport
    # This provides a single /mcp endpoint for all MCP communication
    mcp.run(
        transport="streamable-http",
        host=cast(str, config["host"]),
        port=cast(int, config["port"]),
    )


def run_combined_server(config: dict[str, Any]) -> None:
    """Run the server with both SSE and Streamable HTTP transports.

    Args:
        config: Server configuration
    """
    logger.debug("🔌 Using combined SSE + Streamable HTTP transports for network communication")

    # Define middleware to suppress 'NoneType object is not callable' errors during shutdown
    class SuppressNoneTypeErrorMiddleware:
        def __init__(self, app: Any) -> None:
            self.app = app

        async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
            try:
                await self.app(scope, receive, send)
            except TypeError as e:
                if "NoneType" in str(e) and "not callable" in str(e):
                    pass
                else:
                    raise

    # Get the ASGI apps for both transports from FastMCP
    try:
        # Get SSE app from FastMCP
        sse_app = mcp.sse_app()
        # Get Streamable HTTP app from FastMCP
        streamable_app = mcp.streamable_http_app()
    except AttributeError as e:
        logger.error("FastMCP version may not support sse_app() or streamable_http_app() methods")
        logger.error("Falling back to manual SSE setup with streamable HTTP mounted")
        # Fallback: use manual SSE setup and mount streamable HTTP
        sse = SseServerTransport("/messages/")

        async def handle_sse(request: Request) -> None:
            async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
                try:
                    await mcp._mcp_server.run(
                        streams[0],
                        streams[1],
                        mcp._mcp_server.create_initialization_options(),
                    )
                except asyncio.CancelledError:
                    logger.debug("🔍 ASGI connection cancelled, shutting down quietly.")
                except Exception as e:
                    logger.exception("💥 ASGI connection ended with exception: %s", e)
                    handle_taskgroup_exception(e)

        # Create app with both SSE and streamable HTTP endpoints
        app = Starlette(
            debug=config.get("debug", False),
            middleware=[
                Middleware(SuppressNoneTypeErrorMiddleware),
                Middleware(
                    CORSMiddleware,
                    allow_origins=["*"],
                    allow_methods=["GET", "POST"],
                    allow_headers=["*"],
                ),
            ],
            routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
                Mount("/mcp", app=mcp.streamable_http_app()),
            ],
        )
    else:
        # Create combined Starlette app with both transports mounted
        app = Starlette(
            debug=config.get("debug", False),
            middleware=[
                Middleware(SuppressNoneTypeErrorMiddleware),
                Middleware(
                    CORSMiddleware,
                    allow_origins=["*"],
                    allow_methods=["GET", "POST"],
                    allow_headers=["*"],
                ),
            ],
            routes=[
                # Mount SSE at /sse (with /messages/ for posting)
                Mount("/sse", app=sse_app),
                # Mount Streamable HTTP at /mcp
                Mount("/mcp", app=streamable_app),
            ],
        )

    # Create and run Uvicorn server
    uvicorn_config = uvicorn.Config(
        app,
        host=cast(str, config["host"]),
        port=cast(int, config["port"]),
        log_config=None,
        timeout_graceful_shutdown=0,
    )
    server = uvicorn.Server(uvicorn_config)
    server.run()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Lucidity MCP Server",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind the server to (use 0.0.0.0 for all interfaces)",
    )
    parser.add_argument(
        "--port",
        default=6969,  # spicy!
        type=int,
        help="Port to listen on for network connections",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http", "both"],
        default="stdio",
        help="""Transport type to use:
                        - stdio: for terminal interaction
                        - sse: for network (legacy, SSE-based)
                        - streamable-http: for network (recommended, modern HTTP)
                        - both: SSE + Streamable HTTP simultaneously""",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging for HTTP requests",
    )
    parser.add_argument(
        "--log-file",
        help="Path to log file (required for stdio transport if logs enabled)",
    )
    parser.add_argument(
        "--cleanup-cache",
        action="store_true",
        help="Clean up inactive repository caches and exit",
    )
    parser.add_argument(
        "--cleanup-days",
        type=int,
        default=7,
        help="Number of days of inactivity before removing cached repositories (default: 7)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cleaned up without actually deleting (only with --cleanup-cache)",
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point for the Lucidity MCP server."""
    # Parse arguments
    args = parse_args()

    # Set up global exception handler
    setup_global_exception_handler()

    # Set log level based on arguments
    log_level = args.log_level if not args.debug else "DEBUG"

    # Handle cleanup mode
    if args.cleanup_cache:
        # Set up simple logging for cleanup
        from .tools.git_utils import cleanup_inactive_repositories
        
        handler = RichHandler(rich_tracebacks=True, markup=True)
        setup_logging(log_level, args.debug, handler, args.log_file, True, False)
        
        logger.info("Running repository cache cleanup")
        result = cleanup_inactive_repositories(days=args.cleanup_days, dry_run=args.dry_run)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"Repository Cache Cleanup {'(DRY RUN)' if args.dry_run else ''}")
        print(f"{'='*60}")
        print(f"Cache Directory: {result['cache_dir']}")
        print(f"Repositories Scanned: {result['scanned']}")
        print(f"Repositories {'to Remove' if args.dry_run else 'Removed'}: {result['removed']}")
        print(f"Space {'to Free' if args.dry_run else 'Freed'}: {result['freed_bytes'] / (1024 * 1024):.2f} MB")
        if result['repositories']:
            print(f"\nRepositories:")
            for repo in result['repositories']:
                print(f"  - {repo}")
        print(f"{'='*60}\n")
        
        return 0

    # Determine logging mode:
    # 1. Normal console logging (for sse or non-terminal use)
    # 2. File-only logging (for stdio with log file)
    # 3. Stderr-only logging (for stdio without log file)
    console_enabled = True
    stderr_only = False

    if args.transport == "stdio":
        if args.log_file:
            # For stdio with a log file: disable console, log to file
            console_enabled = False
        else:
            # For stdio without a log file: use stderr for warnings/errors only
            console_enabled = False
            stderr_only = True

    # Set up logging
    if console_enabled:
        # Normal rich console logging
        handler = RichHandler(rich_tracebacks=True, markup=True)
        setup_logging(log_level, args.debug or args.verbose, handler, args.log_file, console_enabled, stderr_only)
    else:
        # Either file-only or stderr-only logging
        setup_logging(log_level, args.debug or args.verbose, None, args.log_file, console_enabled, stderr_only)

    # Setup asyncio exception handler
    setup_asyncio_exception_handler()

    # We no longer need this warning since we now handle stderr
    # logging properly for stdio mode without interfering with stdout

    try:
        # Ensure environment variables are loaded
        load_environment()

        # Log startup message - only if we have full console logging or a log file
        if console_enabled or args.log_file:
            logger.info("✨ Lucidity MCP Server - AI powered code review tool")

        # Prepare server configuration
        config = {
            "transport": args.transport.upper(),
            "host": args.host,
            "port": args.port,
            "debug": args.debug,
            "log_level": log_level,
        }

        # Validate host
        try:
            ipaddress.ip_address(args.host)
        except ValueError:
            if args.host != "localhost":
                config["host"] = "127.0.0.1"
                logger.warning("⚠️ Invalid host address '%s', using 127.0.0.1 instead", args.host)

        # Run the appropriate server based on transport
        if args.transport == "sse":
            logger.info("🚀 Starting SSE server on %s:%s", config["host"], config["port"])
            run_sse_server(config)
        elif args.transport == "streamable-http":
            logger.info("🚀 Starting Streamable HTTP server on %s:%s", config["host"], config["port"])
            run_streamable_http_server(config)
        elif args.transport == "both":
            logger.info("🚀 Starting combined SSE + Streamable HTTP server on %s:%s", config["host"], config["port"])
            logger.info("   SSE endpoint: http://%s:%s/sse", config["host"], config["port"])
            logger.info("   Streamable HTTP endpoint: http://%s:%s/mcp", config["host"], config["port"])
            run_combined_server(config)
        else:
            run_stdio_server()

    except KeyboardInterrupt:
        logger.info("👋 Server shutdown requested")
    except Exception as e:
        logger.exception("💥 Server error: %s", e)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
