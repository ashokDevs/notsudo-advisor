from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict, total=False):
    """State of the dependency exploitability advisor agent."""

    # Inputs
    advisory_id: str
    repo_id: str
    commit_sha: str
    repo_path: str

    # Extracted from advisory / manifests
    package_name: str | None
    current_version: str | None
    fixed_version: str | None
    vulnerable_ranges: list[dict[str, Any]]
    vulnerable_symbols: list[str]
    dep_type: str
    severity: str
    summary: str
    details: str
    ecosystem: str

    # Reasoning state
    is_exposed: bool | None
    verdict: str | None  # exposed | safe | unsure
    confidence: float | None
    reachability_reasoning: str | None
    retrieved_context: Annotated[list[dict[str, Any]], operator.add]
    evidence_quotes: list[dict[str, Any]]
    entrypoints: list[str]
    call_sites: list[dict[str, Any]]

    # Reflection / Loop control
    retrieval_iterations: int
    need_more_context: bool

    # Action
    preflight_ok: bool | None
    preflight_message: str | None
    pr_draft: dict[str, Any] | None
    nodes_run: list[str]
