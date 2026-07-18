from __future__ import annotations

from pathlib import Path

from core.orchestration.graph import route_reason, route_triage
from core.orchestration.nodes import act_node, locate_node, reason_node
from core.orchestration.state import AgentState


def _base_state(**overrides: object) -> AgentState:
    demo = Path(__file__).resolve().parents[2] / "demo_app"
    state: AgentState = {
        "advisory_id": "GHSA-1234-5678",
        "repo_id": "repo-abc",
        "commit_sha": "deadbeef",
        "repo_path": str(demo),
        "package_name": "lodash",
        "vulnerable_ranges": [],
        "vulnerable_symbols": ["merge"],
        "is_exposed": None,
        "reachability_reasoning": None,
        "retrieved_context": [],
        "retrieval_iterations": 0,
        "pr_draft": None,
        "dep_type": "dep",
        "severity": "HIGH",
        "summary": "Prototype pollution via merge",
        "details": "lodash merge is vulnerable",
        "nodes_run": [],
    }
    state.update(overrides)  # type: ignore[typeddict-item]
    return state


async def test_reason_node_no_context_concludes_safe() -> None:
    state = _base_state(call_sites=[], retrieved_context=[])
    result = await reason_node(state)
    assert result["is_exposed"] is False
    assert result.get("verdict") == "safe"


async def test_reason_node_already_resolved_passes_through() -> None:
    state = _base_state(is_exposed=False, reachability_reasoning="prior conclusion")
    result = await reason_node(state)
    assert result["is_exposed"] is False
    assert result["reachability_reasoning"] == "prior conclusion"


async def test_locate_node_skips_search_when_already_resolved() -> None:
    state = _base_state(is_exposed=False, retrieval_iterations=0)
    result = await locate_node(state)
    assert result.get("retrieval_iterations", 0) == 0


async def test_act_node_exposed_creates_pr_draft() -> None:
    state = _base_state(
        is_exposed=True,
        reachability_reasoning="merge() called in utils.js",
        current_version="4.17.20",
        fixed_version="4.17.21",
        preflight_ok=True,
        preflight_message="ok",
        confidence=0.9,
        evidence_quotes=[],
        entrypoints=["src/utils.js"],
    )
    result = await act_node(state)
    assert result["pr_draft"] is not None
    assert "lodash" in result["pr_draft"]["title"]
    assert "GHSA-1234-5678" in result["pr_draft"]["title"]


async def test_act_node_not_exposed_no_pr_draft() -> None:
    state = _base_state(is_exposed=False)
    result = await act_node(state)
    assert result.get("pr_draft") is None


async def test_act_node_uncertain_no_pr_draft() -> None:
    state = _base_state(is_exposed=None)
    result = await act_node(state)
    assert result.get("pr_draft") is None


async def test_act_node_blocks_on_failed_preflight() -> None:
    state = _base_state(
        is_exposed=True,
        preflight_ok=False,
        preflight_message="npm install failed",
        fixed_version="4.17.21",
    )
    result = await act_node(state)
    assert result.get("pr_draft") is None


def test_route_triage_unexposed_goes_to_act() -> None:
    state = _base_state(is_exposed=False)
    assert route_triage(state) == "act"


def test_route_triage_uncertain_goes_to_locate() -> None:
    state = _base_state(is_exposed=None)
    assert route_triage(state) == "locate"


def test_route_reason_needs_more_context_loops_back() -> None:
    state = _base_state(retrieval_iterations=1, need_more_context=True)
    assert route_reason(state) == "locate"


def test_route_reason_exposed_goes_to_preflight() -> None:
    state = _base_state(retrieval_iterations=0, is_exposed=True, need_more_context=False)
    assert route_reason(state) == "preflight"


def test_route_reason_default_proceeds_to_act() -> None:
    state = _base_state(retrieval_iterations=0, is_exposed=False, need_more_context=False)
    assert route_reason(state) == "act"
