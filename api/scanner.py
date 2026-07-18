from __future__ import annotations

from typing import Any

from core.analysis.github_clone import cleanup_target, resolve_scan_target
from core.analysis.pipeline import analyze_repo
from core.observability.logging import get_logger

logger = get_logger(__name__)


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
