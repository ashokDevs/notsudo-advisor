import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict):
    """The state of the dependency exploitability advisor agent."""
    
    # Inputs
    advisory_id: str
    repo_id: str
    commit_sha: str
    
    # Extracted from advisory
    package_name: str | None
    vulnerable_ranges: list[dict[str, Any]]
    vulnerable_symbols: list[str]
    
    # Reasoning state
    is_exposed: bool | None
    reachability_reasoning: str | None
    retrieved_context: Annotated[list[dict[str, Any]], operator.add]
    
    # Reflection / Loop control
    retrieval_iterations: int
    
    # Final Action
    pr_draft: dict[str, Any] | None
