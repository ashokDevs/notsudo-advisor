from core.action.pr_creator import PRCreator
from core.orchestration.state import AgentState

def test_pr_creator_formats_safely() -> None:
    state: AgentState = {
        "advisory_id": "GHSA-123",
        "repo_id": "repo_1",
        "commit_sha": "sha1",
        "package_name": "lodash",
        "vulnerable_ranges": [],
        "vulnerable_symbols": [],
        "is_exposed": True,
        "reachability_reasoning": "Call to merge() found in utils.js",
        "retrieved_context": [],
        "retrieval_iterations": 1,
        "pr_draft": None
    }
    
    draft = PRCreator.format_pr(state)
    
    assert "Bump `lodash` to fix GHSA-123" in draft["title"]
    assert "Call to merge() found in utils.js" in draft["body"]
    assert "https://osv.dev/vulnerability/GHSA-123" in draft["body"]
