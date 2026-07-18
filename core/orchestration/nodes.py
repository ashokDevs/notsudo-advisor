from __future__ import annotations

from pathlib import Path
from typing import Any

from core.action.pr_creator import PRCreator
from core.analysis.call_sites import CallSite, CallSiteFinder
from core.analysis.pipeline import detect_packages, fetch_advisory
from core.analysis.preflight import preflight_bump
from core.analysis.reachability import advisory_to_severity, assess_reachability
from core.analysis.semver import first_fixed_version, version_affected_by_ranges
from core.analysis.symbols import extract_vulnerable_symbols
from core.llm.client import get_llm_client
from core.observability.logging import get_logger
from core.orchestration.state import AgentState
from core.security.capability_graph import CapabilityGraph

logger = get_logger(__name__)
_caps = CapabilityGraph.from_permissions()


def _repo(state: AgentState) -> Path:
    path = state.get("repo_path")
    if not path:
        raise ValueError("repo_path is required on AgentState for analysis nodes")
    return Path(path).expanduser().resolve()


async def triage_node(state: AgentState) -> dict[str, Any]:
    """Fetch advisory, match dependency + semver, early no-op when safe."""
    _caps.authorize("triage", "advisory_query")
    logger.info("triage", advisory_id=state.get("advisory_id"))

    advisory_id = state["advisory_id"]
    repo = _repo(state)
    packages, ecosystem = detect_packages(repo)

    vuln = await fetch_advisory(advisory_id)
    package_name = state.get("package_name")
    if not package_name:
        for aff in vuln.get("affected") or []:
            name = (aff.get("package") or {}).get("name")
            if name:
                package_name = str(name)
                break
    package_name = package_name or "unknown"

    summary = str(vuln.get("summary") or "")
    details = str(vuln.get("details") or "")
    sev = advisory_to_severity(vuln)
    ranges: list[dict[str, Any]] = []
    for aff in vuln.get("affected") or []:
        ranges.extend(aff.get("ranges") or [])
    fixed = first_fixed_version(ranges)

    info = packages.get(package_name)
    if info is None:
        for k, v in packages.items():
            if k.lower() == package_name.lower():
                info = v
                package_name = k
                break

    nodes = list(state.get("nodes_run") or [])
    nodes.append("triage")

    if info is None:
        return {
            **state,
            "package_name": package_name,
            "ecosystem": ecosystem,
            "summary": summary,
            "details": details,
            "severity": sev,
            "vulnerable_ranges": ranges,
            "fixed_version": fixed,
            "is_exposed": False,
            "verdict": "safe",
            "confidence": 0.99,
            "reachability_reasoning": f"Package {package_name} is not a direct dependency.",
            "nodes_run": nodes,
            "vulnerable_symbols": extract_vulnerable_symbols(package_name, summary, details, osv=vuln),
        }

    if ranges and not version_affected_by_ranges(info.version, ranges):
        return {
            **state,
            "package_name": package_name,
            "current_version": info.version,
            "fixed_version": fixed,
            "dep_type": info.dep_type,
            "ecosystem": ecosystem,
            "summary": summary,
            "details": details,
            "severity": sev,
            "vulnerable_ranges": ranges,
            "is_exposed": False,
            "verdict": "safe",
            "confidence": 0.95,
            "reachability_reasoning": (
                f"{package_name}@{info.version} is outside the affected range."
            ),
            "nodes_run": nodes + ["match_dependency"],
            "vulnerable_symbols": extract_vulnerable_symbols(package_name, summary, details, osv=vuln),
        }

    symbols = extract_vulnerable_symbols(package_name, summary, details, osv=vuln)
    return {
        **state,
        "package_name": package_name,
        "current_version": info.version,
        "fixed_version": fixed,
        "dep_type": info.dep_type,
        "ecosystem": ecosystem,
        "summary": summary,
        "details": details,
        "severity": sev,
        "vulnerable_ranges": ranges,
        "vulnerable_symbols": symbols,
        "is_exposed": None,
        "verdict": None,
        "nodes_run": nodes + ["match_dependency"],
    }


async def locate_node(state: AgentState) -> dict[str, Any]:
    """Locate import and call sites for the vulnerable package/symbols."""
    _caps.authorize("locate", "locate_call_sites")
    logger.info("locate", package=state.get("package_name"))

    if state.get("is_exposed") is False:
        return dict(state)

    repo = _repo(state)
    package_name = state.get("package_name") or ""
    symbols = list(state.get("vulnerable_symbols") or [])
    finder = CallSiteFinder()
    sites = finder.find(repo, package_name, symbols=symbols)
    nodes = list(state.get("nodes_run") or [])
    nodes.append("locate")

    return {
        **state,
        "call_sites": [s.model_dump() for s in sites],
        "retrieved_context": [s.model_dump() for s in sites],
        "retrieval_iterations": int(state.get("retrieval_iterations") or 0) + 1,
        "nodes_run": nodes,
    }


async def reason_node(state: AgentState) -> dict[str, Any]:
    """Assess reachability with grounded evidence quotes."""
    _caps.authorize("reason", "code_read")
    logger.info("reason", package=state.get("package_name"))

    if state.get("is_exposed") is False:
        return dict(state)

    repo = _repo(state)
    raw_sites = state.get("call_sites") or state.get("retrieved_context") or []
    sites = [CallSite.model_validate(s) for s in raw_sites if isinstance(s, dict)]

    reach = await assess_reachability(
        repo=repo,
        package_name=state.get("package_name") or "unknown",
        advisory_id=state.get("advisory_id") or "",
        summary=state.get("summary") or "",
        details=state.get("details") or "",
        dep_type=state.get("dep_type") or "dep",
        severity=state.get("severity") or "UNKNOWN",
        symbols=list(state.get("vulnerable_symbols") or []),
        sites=sites,
        llm=get_llm_client(),
    )

    nodes = list(state.get("nodes_run") or [])
    nodes.extend([n for n in reach.nodes if n not in nodes])

    is_exposed: bool | None
    if reach.verdict == "exposed":
        is_exposed = True
    elif reach.verdict == "safe":
        is_exposed = False
    else:
        is_exposed = None

    return {
        **state,
        "is_exposed": is_exposed,
        "verdict": reach.verdict,
        "confidence": reach.confidence,
        "reachability_reasoning": reach.reasoning,
        "evidence_quotes": [q.model_dump() for q in reach.evidence_quotes],
        "entrypoints": reach.entrypoints,
        "need_more_context": False,
        "nodes_run": nodes,
    }


async def preflight_node(state: AgentState) -> dict[str, Any]:
    """Run lockfile resolution preflight for the proposed bump."""
    _caps.authorize("preflight", "preflight_lockfile")
    logger.info("preflight", package=state.get("package_name"))

    if state.get("is_exposed") is not True:
        return {**state, "preflight_ok": None, "preflight_message": "skipped (not exposed)"}

    fix = state.get("fixed_version")
    pkg = state.get("package_name")
    if not fix or not pkg:
        return {
            **state,
            "preflight_ok": False,
            "preflight_message": "no fixed version known",
            "nodes_run": list(state.get("nodes_run") or []) + ["preflight"],
        }

    result = await preflight_bump(
        _repo(state),
        pkg,
        fix,
        ecosystem=state.get("ecosystem") or "npm",
    )
    return {
        **state,
        "preflight_ok": result.ok,
        "preflight_message": result.message,
        "nodes_run": list(state.get("nodes_run") or []) + ["preflight"],
    }


async def act_node(state: AgentState) -> dict[str, Any]:
    """Draft PR only when exposed and preflight passed (or preflight skipped/unavailable)."""
    _caps.authorize("act", "pr_create")
    logger.info("act", exposed=state.get("is_exposed"))

    nodes = list(state.get("nodes_run") or [])
    nodes.append("act")

    if state.get("is_exposed") is not True:
        return {**state, "pr_draft": None, "nodes_run": nodes}

    # Allow draft when preflight ok or not run; block only on explicit failure
    if state.get("preflight_ok") is False:
        return {
            **state,
            "pr_draft": None,
            "reachability_reasoning": (
                (state.get("reachability_reasoning") or "")
                + f"\n\nPreflight failed: {state.get('preflight_message')}"
            ),
            "nodes_run": nodes,
        }

    draft = PRCreator.format_pr(state)
    return {**state, "pr_draft": draft, "nodes_run": nodes}
