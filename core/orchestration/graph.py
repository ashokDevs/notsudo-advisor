from langgraph.graph import StateGraph, END
from core.orchestration.state import AgentState
from core.orchestration.nodes import triage_node, locate_node, reason_node, act_node

def route_triage(state: AgentState) -> str:
    """Decide whether to proceed to locate or end based on triage."""
    if state.get("is_exposed") is False:
        return "act"
    return "locate"

def route_reason(state: AgentState) -> str:
    """Decide whether to retry retrieval or proceed to act."""
    # We could implement a self-RAG reflection loop here
    if state.get("retrieval_iterations", 0) < 2 and state.get("reachability_reasoning") == "Need more context":
        return "locate"
    return "act"

def build_graph() -> StateGraph:
    """Compile the LangGraph state machine with capability-isolated nodes."""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("triage", triage_node)
    workflow.add_node("locate", locate_node)
    workflow.add_node("reason", reason_node)
    workflow.add_node("act", act_node)
    
    # Define edges
    workflow.set_entry_point("triage")
    
    workflow.add_conditional_edges(
        "triage",
        route_triage,
        {
            "locate": "locate",
            "act": "act"
        }
    )
    
    workflow.add_edge("locate", "reason")
    
    workflow.add_conditional_edges(
        "reason",
        route_reason,
        {
            "locate": "locate",
            "act": "act"
        }
    )
    
    workflow.add_edge("act", END)
    
    return workflow.compile()
