from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from core.observability.logging import get_logger
from core.security.capability_graph import TOOL_PERMISSIONS, CapabilityGraph

logger = get_logger(__name__)

mcp = FastMCP("notsudo", dependencies=["notsudo"])
capability_graph = CapabilityGraph.from_permissions(TOOL_PERMISSIONS)


def authorize(node: str, tool: str) -> None:
    """Enforce structural capability isolation on tool dispatch."""
    capability_graph.authorize(node, tool)


def run_server() -> None:
    """Run the MCP server via stdio."""
    # Import tools so @mcp.tool registrations attach
    import mcp_server.tools  # noqa: F401

    logger.info("Starting MCP server")
    capability_graph.assert_isolation()
    mcp.run()


if __name__ == "__main__":
    run_server()
