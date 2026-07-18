from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from core.orchestration.nodes import act_node, locate_node, preflight_node, reason_node, triage_node
from core.orchestration.state import AgentState


def route_triage(state: AgentState) -> Literal["locate", "act"]:
    """Early exit when triage already marked not exposed."""
    if state.get("is_exposed") is False:
        return "act"
    return "locate"


def route_reason(state: AgentState) -> Literal["locate", "preflight", "act"]:
    """Self-RAG style loop (capped) or proceed to preflight/act."""
    iterations = int(state.get("retrieval_iterations") or 0)
    if state.get("need_more_context") and iterations < 2:
        return "locate"
    if state.get("is_exposed") is True:
        return "preflight"
    return "act"


def build_graph() -> CompiledStateGraph[AgentState, Any, Any]:
    """Compile the LangGraph state machine with capability-isolated nodes."""
    workflow: StateGraph[AgentState] = StateGraph(AgentState)

    workflow.add_node("triage", triage_node)
    workflow.add_node("locate", locate_node)
    workflow.add_node("reason", reason_node)
    workflow.add_node("preflight", preflight_node)
    workflow.add_node("act", act_node)

    workflow.set_entry_point("triage")

    workflow.add_conditional_edges(
        "triage",
        route_triage,
        {"locate": "locate", "act": "act"},
    )
    workflow.add_edge("locate", "reason")
    workflow.add_conditional_edges(
        "reason",
        route_reason,
        {"locate": "locate", "preflight": "preflight", "act": "act"},
    )
    workflow.add_edge("preflight", "act")
    workflow.add_edge("act", END)

    return workflow.compile()
