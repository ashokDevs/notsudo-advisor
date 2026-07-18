from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from core.observability.logging import get_logger

logger = get_logger(__name__)

mcp = FastMCP("notsudo", dependencies=["notsudo"])


def run_server() -> None:
    """Run the MCP server via stdio."""
    logger.info("Starting MCP server")
    mcp.run()

if __name__ == "__main__":
    run_server()
