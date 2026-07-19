from __future__ import annotations

from typing import Any

from api.remediation import RemediationPlan, issue_remediation_token
from core.analysis.github_clone import cleanup_target, resolve_scan_target
from core.analysis.pipeline import analyze_repo
from core.analysis.semver import compare_versions
from core.config import session_secret
from core.observability.logging import get_logger

logger = get_logger(__name__)


def _attach_remediation_plans(result: dict[str, Any], target_repo: str) -> None:
    """Expose one signed PR plan per dependency, never client-editable PR fields."""
    if result.get("ecosystem") != "npm":
        result["remediation_plans"] = []
        return
    advisories = result.get("advisories")
    if not isinstance(advisories, list):
        return

    by_package: dict[str, list[dict[str, Any]]] = {}
    for advisory in advisories:
        if not isinstance(advisory, dict):
            continue
        preflight = advisory.get("preflight")
        if (
            advisory.get("verdict") != "exposed"
            or not advisory.get("fix")
            or not isinstance(preflight, dict)
            or preflight.get("ok") is not True
        ):
            continue
        package_name = advisory.get("pkg")
        if isinstance(package_name, str):
            by_package.setdefault(package_name, []).append(advisory)

    plans: list[dict[str, Any]] = []
    for package_name, affected in by_package.items():
        selected = affected[0]
        for candidate in affected[1:]:
            if compare_versions(str(candidate["fix"]), str(selected["fix"])) > 0:
                selected = candidate

        advisory_ids = [str(item["id"]) for item in affected if item.get("id")]
        quotes: list[dict[str, Any]] = []
        for item in affected:
            raw_quotes = item.get("evidence_quotes")
            if isinstance(raw_quotes, list):
                quotes.extend(q for q in raw_quotes if isinstance(q, dict))

        plan = RemediationPlan(
            advisory_ids=advisory_ids,
            package_name=package_name,
            current_version=str(selected["current"]),
            fixed_version=str(selected["fix"]),
            target_repo=target_repo,
            reasoning=str(selected["reasoning"]),
            entrypoints=[str(e) for e in selected.get("entrypoints") or []],
            evidence_quotes=quotes[:5],
        )
        token = issue_remediation_token(plan, secret=session_secret())
        selected["remediation_token"] = token
        selected["grouped_advisory_ids"] = advisory_ids
        plans.append(
            {
                "package": package_name,
                "current": plan.current_version,
                "fix": plan.fixed_version,
                "advisory_ids": advisory_ids,
                "result_id": selected.get("id"),
            }
        )
    result["remediation_plans"] = plans


async def scan_repo(repo_path: str) -> dict[str, Any]:
    """
    Public API entry — accepts a local path OR GitHub URL / owner/repo.
    Clones public GitHub repos into a temp dir, scans, then cleans up.
    """
    from core.config import github_demo_repo

    target = await resolve_scan_target(repo_path)
    try:
        result = await analyze_repo(str(target.path), run_preflight=True)
        # Prefer GitHub-style display name when we cloned
        if target.source == "github":
            result["repo"] = target.display_name
            result["github_url"] = target.github_url
            result["source"] = "github"
            # Fix PRs should open on the *scanned* GitHub repo (not GITHUB_DEMO_REPO)
            if target.owner and target.repo:
                result["pr_target_repo"] = f"{target.owner}/{target.repo}"
            else:
                result["pr_target_repo"] = target.display_name
        else:
            result["source"] = "local"
            result.setdefault("github_url", None)
            # Local / demo_app scans fall back to configured demo repo for PRs
            result["pr_target_repo"] = github_demo_repo()
        _attach_remediation_plans(result, str(result["pr_target_repo"]))
        result["display_name"] = target.display_name
        result["scan_target"] = repo_path
        # Summary helpers for the win-demo UI
        ads = result.get("advisories") or []
        result["summary"] = {
            "packages": result.get("pkg_count", 0),
            "vulns": result.get("vuln_count", len(ads)),
            "exposed": sum(1 for a in ads if a.get("verdict") == "exposed"),
            "safe": sum(1 for a in ads if a.get("verdict") == "safe"),
            "unsure": sum(1 for a in ads if a.get("verdict") == "unsure"),
            "presence_noise": sum(1 for a in ads if a.get("verdict") in {"safe", "unsure"}),
            "tagline": "Dependabot-style noise vs reachability-confirmed exposure",
        }
        return result
    finally:
        cleanup_target(target)
