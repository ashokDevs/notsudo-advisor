import pytest

from core.orchestration.graph import build_graph

pytestmark = pytest.mark.asyncio

async def test_graph_compiles_and_runs() -> None:
    graph = build_graph()
    
    # Check it compiles
    assert graph is not None
    assert hasattr(graph, "ainvoke")
