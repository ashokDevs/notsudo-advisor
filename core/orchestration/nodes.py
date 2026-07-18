import json
from mcp_server.tools import check_vulnerable_dependency, code_search
from core.orchestration.state import AgentState
from core.observability.logging import get_logger

logger = get_logger(__name__)

async def triage_node(state: AgentState) -> AgentState:
    """Triage advisory: extract package and check if present in repo."""
    logger.info("Triaging advisory", advisory_id=state["advisory_id"])
    
    # In a real implementation we'd use an LLM or look up the DB directly.
    # For now we'll simulate the extraction.
    package_name = state.get("package_name") or "lodash"
    
    # Call MCP tool to check dependency
    # Note: FastMCP tools are async functions that we can call directly in python if we pass kwargs
    # but normally they're called over MCP protocol. Since we are in the same process we can just call them.
    # A true MCP client would connect to the server.
    is_present = await check_vulnerable_dependency(
        repo_id=state["repo_id"],
        commit_sha=state["commit_sha"],
        package_name=package_name,
        affected_ranges_json="[]"
    )
    
    return {
        **state,
        "package_name": package_name,
        "is_exposed": False if not is_present else None
    }

async def locate_node(state: AgentState) -> AgentState:
    """Locate call sites of vulnerable symbols."""
    logger.info("Locating call sites", package=state["package_name"])
    
    if state.get("is_exposed") is False:
        return state

    symbols = state.get("vulnerable_symbols", ["merge"])
    query = f"calls to {state['package_name']} {symbols[0]}"
    
    results_str = await code_search(
        repo_id=state["repo_id"],
        commit_sha=state["commit_sha"],
        query=query
    )
    results = json.loads(results_str)
    
    return {
        **state,
        "retrieved_context": results,
        "retrieval_iterations": state.get("retrieval_iterations", 0) + 1
    }

async def reason_node(state: AgentState) -> AgentState:
    """Reason about reachability based on located call sites."""
    logger.info("Reasoning about reachability")
    
    if state.get("is_exposed") is False:
        return state
        
    context = state.get("retrieved_context", [])
    if not context:
        return {
            **state,
            "is_exposed": False,
            "reachability_reasoning": "No call sites found."
        }
        
    # Simulate LLM reasoning
    return {
        **state,
        "is_exposed": True,
        "reachability_reasoning": "Found vulnerable call site in retrieved context."
    }

async def act_node(state: AgentState) -> AgentState:
    """Decide on final action and draft PR if necessary."""
    logger.info("Deciding final action")
    
    if state.get("is_exposed"):
        pr_draft = {
            "title": f"Bump {state['package_name']} to fix {state['advisory_id']}",
            "body": state.get("reachability_reasoning", "")
        }
        return {
            **state,
            "pr_draft": pr_draft
        }
        
    return state
