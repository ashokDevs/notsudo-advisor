
from mcp_server.server import mcp


def test_mcp_server_initializes() -> None:
    assert mcp.name == "notsudo"
    
    # Check that it currently has no tools
    # Actually FastMCP manages tools, let's just assert the instance is created
    assert mcp is not None
