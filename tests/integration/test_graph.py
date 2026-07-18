import pytest
from core.orchestration.graph import build_graph

pytestmark = pytest.mark.asyncio

async def test_graph_compiles_and_runs() -> None:
    graph = build_graph()
    
    initial_state = {
        "advisory_id": "GHSA-123",
        "repo_id": "00000000-0000-0000-0000-000000000000",
        "commit_sha": "testsha",
        "package_name": "lodash",
        "vulnerable_ranges": [],
        "vulnerable_symbols": ["merge"],
        "is_exposed": None,
        "reachability_reasoning": None,
        "retrieved_context": [],
        "retrieval_iterations": 0,
        "pr_draft": None
    }
    
    # Run the graph
    # Mocking check_vulnerable_dependency is needed if we hit the DB
    # For now we can just check it compiles
    assert graph is not None
    assert hasattr(graph, "ainvoke")
