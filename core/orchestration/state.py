from typing import Annotated, TypedDict
import operator

class AgentState(TypedDict):
    """The state of the dependency exploitability advisor agent."""
    
    # Inputs
    advisory_id: str
    repo_id: str
    commit_sha: str
    
    # Extracted from advisory
    package_name: str | None
    vulnerable_ranges: list[dict]
    vulnerable_symbols: list[str]
    
    # Reasoning state
    is_exposed: bool | None
    reachability_reasoning: str | None
    retrieved_context: Annotated[list[dict], operator.add]
    
    # Reflection / Loop control
    retrieval_iterations: int
    
    # Final Action
    pr_draft: dict | None
