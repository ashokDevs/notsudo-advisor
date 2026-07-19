from __future__ import annotations

import pytest

from mcp_server.server import capability_graph, mcp
from mcp_server.tools import list_registered_tools, pr_create


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


async def test_pr_draft_cannot_spoof_an_authorized_node_from_the_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NOTSUDO_MCP_NODE_ID", raising=False)

    with pytest.raises(PermissionError, match="NOTSUDO_MCP_NODE_ID"):
        await pr_create("title", "body")
