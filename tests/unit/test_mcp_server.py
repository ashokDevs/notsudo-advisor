from __future__ import annotations

from mcp_server.server import capability_graph, mcp
from mcp_server.tools import list_registered_tools


def test_mcp_server_initializes() -> None:
    assert mcp.name == "notsudo"
    assert mcp is not None


def test_capability_graph_isolation() -> None:
    capability_graph.assert_isolation()


def test_tools_list_covers_mcp_surface() -> None:
    tools = list_registered_tools()
    assert "pr_create" in tools
    assert "locate_call_sites" in tools
    assert "advisory_query" in tools
