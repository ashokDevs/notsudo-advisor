from __future__ import annotations

import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from core.analysis.call_sites import CallSiteFinder
from core.analysis.preflight import PreflightResult, preflight_bump
from core.analysis.reachability import advisory_to_severity, assess_reachability
from core.analysis.semver import first_fixed_version, strip_version, version_affected_by_ranges
from core.analysis.symbols import extract_vulnerable_symbols
from core.action.pr_creator import PRCreator
from core.llm.client import LLMClient, get_llm_client
from core.observability.logging import get_logger

logger = get_logger(__name__)

_OSV_BATCH = "https://api.osv.dev/v1/querybatch"
_OSV_VULN = "https://api.osv.dev/v1/vulns"
_OSV_GET = "https://api.osv.dev/v1/vulns/{id}"

_CVSS_MAP: dict[str, float] = {
    "CRITICAL": 9.5,
    "HIGH": 8.0,
    "MODERATE": 6.0,
    "MEDIUM": 6.0,
    "LOW": 3.5,
    "UNKNOWN": 5.0,
}


class PackageInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    dep_type: str  # dep | dev
    declared: str


def detect_packages(repo: Path) -> tuple[dict[str, PackageInfo], str]:
    pkg_json = repo / "package.json"
    if pkg_json.is_file():
        return _parse_package_json(pkg_json), "npm"
    req = repo / "requirements.txt"
    if req.is_file():
        return _parse_requirements(req), "PyPI"
    pyproj = repo / "pyproject.toml"
    if pyproj.is_file():
        return _parse_pyproject(pyproj), "PyPI"
    return {}, "npm"


def _parse_package_json(path: Path) -> dict[str, PackageInfo]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, PackageInfo] = {}
    resolved = _read_npm_lock(path.parent)
    for name, ver in (data.get("dependencies") or {}).items():
        resolved_ver = resolved.get(str(name), strip_version(str(ver)))
        out[str(name)] = PackageInfo(
            name=str(name), version=resolved_ver, dep_type="dep", declared=str(ver)
        )
    for name, ver in (data.get("devDependencies") or {}).items():
        if str(name) in out:
            continue
        resolved_ver = resolved.get(str(name), strip_version(str(ver)))
        out[str(name)] = PackageInfo(
            name=str(name), version=resolved_ver, dep_type="dev", declared=str(ver)
        )
    return out


def _read_npm_lock(repo: Path) -> dict[str, str]:
    lock = repo / "package-lock.json"
    if not lock.is_file():
        return {}
    try:
        data = json.loads(lock.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, str] = {}
    for key, val in (data.get("packages") or {}).items():
        if not key.startswith("node_modules/"):
            continue
        pkg_name = key[len("node_modules/") :]
        if isinstance(val, dict) and "version" in val:
            out[pkg_name] = str(val["version"])
    for pkg_name, val in (data.get("dependencies") or {}).items():
        if isinstance(val, dict) and "version" in val and pkg_name not in out:
            out[pkg_name] = str(val["version"])
    return out


def _parse_requirements(path: Path) -> dict[str, PackageInfo]:
    out: dict[str, PackageInfo] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-", "git+")):
            continue
        m = re.match(r"^([A-Za-z0-9_.-]+)\s*([>=<!~]=?|==)\s*([0-9][0-9a-zA-Z.*+_-]*)", line)
        if m:
            out[m.group(1)] = PackageInfo(
                name=m.group(1), version=m.group(3), dep_type="dep", declared=line
            )
    return out


def _parse_pyproject(path: Path) -> dict[str, PackageInfo]:
    out: dict[str, PackageInfo] = {}
    text = path.read_text(encoding="utf-8")
    for m in re.finditer(
        r'["\']([A-Za-z0-9_.-]+)\s*([>=<!~]=?|==)\s*([0-9][0-9a-zA-Z.*+_-]*)["\']',
        text,
    ):
        out[m.group(1)] = PackageInfo(
            name=m.group(1), version=m.group(3), dep_type="dep", declared=m.group(0)
        )
    return out


async def query_osv_for_packages(
    packages: dict[str, PackageInfo],
    ecosystem: str,
    *,
    max_vulns_per_pkg: int = 3,
    max_total_ids: int = 40,
) -> list[tuple[PackageInfo, list[dict[str, Any]]]]:
    names = list(packages.keys())
    if not names:
        return []
    queries = [
        {
            "package": {"name": n, "ecosystem": ecosystem},
            "version": packages[n].version,
        }
        for n in names
    ]
    async with httpx.AsyncClient(timeout=30.0) as client:
        batch = await client.post(_OSV_BATCH, json={"queries": queries})
        batch.raise_for_status()
        results: list[dict[str, Any]] = batch.json().get("results", [])

        pkg_vids: list[tuple[PackageInfo, list[str]]] = []
        all_vids: list[str] = []
        for i, res in enumerate(results):
            if i >= len(names):
                break
            vids = [str(v["id"]) for v in res.get("vulns", []) if "id" in v][:max_vulns_per_pkg]
            if vids:
                pkg_vids.append((packages[names[i]], vids))
                all_vids.extend(vids)

        unique_vids = list(dict.fromkeys(all_vids))[:max_total_ids]
        responses = await asyncio.gather(
            *[client.get(f"{_OSV_VULN}/{vid}", timeout=15.0) for vid in unique_vids],
            return_exceptions=True,
        )

    details: dict[str, dict[str, Any]] = {}
    for vid, resp in zip(unique_vids, responses, strict=False):
        if isinstance(resp, Exception) or not isinstance(resp, httpx.Response):
            continue
        if resp.status_code == 200:
            details[vid] = resp.json()

    out: list[tuple[PackageInfo, list[dict[str, Any]]]] = []
    for info, vids in pkg_vids:
        full = [details[v] for v in vids if v in details]
        if full:
            out.append((info, full))
    return out


async def fetch_advisory(advisory_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(_OSV_GET.format(id=advisory_id))
        resp.raise_for_status()
        return resp.json()  # type: ignore[no-any-return]


def _ranges_for_package(vuln: dict[str, Any], package_name: str) -> list[dict[str, Any]]:
    ranges: list[dict[str, Any]] = []
    for aff in vuln.get("affected") or []:
        pkg = (aff.get("package") or {}).get("name")
        if pkg and str(pkg).lower() != package_name.lower():
            # still include if only one affected package
            if len(vuln.get("affected") or []) > 1:
                continue
        for r in aff.get("ranges") or []:
            ranges.append(r)
    return ranges


def _affected_range_label(ranges: list[dict[str, Any]]) -> str:
    fixed = first_fixed_version(ranges)
    if fixed:
        return f"<{fixed}"
    return "affected versions"


def _package_from_advisory(vuln: dict[str, Any]) -> str:
    for aff in vuln.get("affected") or []:
        name = (aff.get("package") or {}).get("name")
        if name:
            return str(name)
    return "unknown"


async def build_advisory_result(
    *,
    repo: Path,
    info: PackageInfo,
    vuln: dict[str, Any],
    ecosystem: str,
    llm: LLMClient | None = None,
    run_preflight: bool = True,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    vid = str(vuln.get("id", ""))
    summary = str(vuln.get("summary") or f"Vulnerability in {info.name}")
    details = str(vuln.get("details") or "")
    sev = advisory_to_severity(vuln)
    severity_label = {"MODERATE": "moderate", "MEDIUM": "moderate"}.get(sev, sev.lower())
    ranges = _ranges_for_package(vuln, info.name)
    fix = first_fixed_version(ranges)

    # Semver gate — if not in range, safe
    if ranges and not version_affected_by_ranges(info.version, ranges):
        elapsed = int((time.perf_counter() - t0) * 1000)
        return {
            "id": vid,
            "pkg": info.name,
            "current": info.version,
            "fix": fix,
            "range": _affected_range_label(ranges),
            "cvss": _CVSS_MAP.get(sev, 5.0),
            "severity": severity_label,
            "title": summary[:80],
            "function": f"{info.name}()",
            "callsites": 0,
            "verdict": "safe",
            "confidence": 0.95,
            "cost": 0.01,
            "elapsed": max(elapsed, 5),
            "reasoning": (
                f"{info.name}@{info.version} is outside the affected range "
                f"({_affected_range_label(ranges)}). Killed at dependency match."
            ),
            "quote": (details or summary)[:220],
            "quoteSource": f"{vid} · advisory details",
            "entrypoints": [],
            "nodes": ["triage", "match_dependency"],
            "preflight": None,
            "evidence_quotes": [],
            "symbols": [],
            "pr_draft": None,
        }

    symbols = extract_vulnerable_symbols(info.name, summary, details, osv=vuln)
    finder = CallSiteFinder()
    sites = finder.find(repo, info.name, symbols=symbols)
    reach = await assess_reachability(
        repo=repo,
        package_name=info.name,
        advisory_id=vid,
        summary=summary,
        details=details,
        dep_type=info.dep_type,
        severity=sev,
        symbols=symbols,
        sites=sites,
        llm=llm,
    )

    preflight: PreflightResult | None = None
    pr_draft: dict[str, str] | None = None
    if reach.verdict == "exposed" and fix and run_preflight:
        preflight = await preflight_bump(repo, info.name, fix, ecosystem=ecosystem)
        if preflight.ok:
            pr_draft = PRCreator.format_from_scan(
                advisory_id=vid,
                package_name=info.name,
                current=info.version,
                fix=fix,
                reasoning=reach.reasoning,
                evidence_quotes=[q.model_dump() for q in reach.evidence_quotes],
                entrypoints=reach.entrypoints,
                confidence=reach.confidence,
                preflight_message=preflight.message,
            )

    quote = ""
    quote_source = f"{vid} · advisory details"
    if reach.evidence_quotes:
        q0 = reach.evidence_quotes[0]
        quote = q0.quote
        quote_source = f"{q0.file_path}:{q0.line_start}"
    else:
        text = (details or summary).strip()
        quote = text[:220] + ("…" if len(text) > 220 else "")

    elapsed = int((time.perf_counter() - t0) * 1000)
    callsites = len([s for s in sites if s.kind == "call"]) or (
        len(sites) if reach.verdict != "safe" else 0
    )

    return {
        "id": vid,
        "pkg": info.name,
        "current": info.version,
        "fix": fix,
        "range": _affected_range_label(ranges),
        "cvss": _CVSS_MAP.get(sev, 5.0),
        "severity": severity_label,
        "title": summary[:80] if len(summary) > 80 else summary,
        "function": (symbols[0] + "()") if symbols else f"{info.name}()",
        "callsites": callsites,
        "verdict": reach.verdict,
        "confidence": reach.confidence,
        "cost": round(0.05 + (0.15 if llm and llm.available else 0.02), 2),
        "elapsed": max(elapsed, 10),
        "reasoning": reach.reasoning,
        "quote": quote,
        "quoteSource": quote_source,
        "entrypoints": reach.entrypoints,
        "nodes": reach.nodes,
        "preflight": preflight.model_dump() if preflight else None,
        "evidence_quotes": [q.model_dump() for q in reach.evidence_quotes],
        "symbols": symbols,
        "pr_draft": pr_draft,
        "call_sites": [s.model_dump() for s in sites[:15]],
    }


async def analyze_repo(
    repo_path: str | Path,
    *,
    llm: LLMClient | None = None,
    run_preflight: bool = True,
    max_advisories: int = 20,
) -> dict[str, Any]:
    """Full local-repo analysis used by the API and CLI."""
    repo = Path(repo_path).expanduser().resolve()
    if not repo.is_dir():
        raise ValueError(f"Not a directory: {repo_path}")

    packages, ecosystem = detect_packages(repo)
    if not packages:
        return {
            "advisories": [],
            "repo": repo.name,
            "ecosystem": ecosystem,
            "pkg_count": 0,
            "vuln_count": 0,
            "path": str(repo),
        }

    llm = llm or get_llm_client()
    hits = await query_osv_for_packages(packages, ecosystem)

    advisories: list[dict[str, Any]] = []
    seen: set[str] = set()
    # Analyze sequentially for rate limits / cost; could fan-out later
    for info, vulns in hits:
        for vuln in vulns:
            vid = str(vuln.get("id", ""))
            if not vid or vid in seen:
                continue
            seen.add(vid)
            result = await build_advisory_result(
                repo=repo,
                info=info,
                vuln=vuln,
                ecosystem=ecosystem,
                llm=llm,
                run_preflight=run_preflight,
            )
            advisories.append(result)
            if len(advisories) >= max_advisories:
                break
        if len(advisories) >= max_advisories:
            break

    order = {"exposed": 0, "unsure": 1, "safe": 2}
    advisories.sort(key=lambda a: (order.get(str(a["verdict"]), 3), -float(a.get("cvss") or 0)))

    return {
        "advisories": advisories,
        "repo": repo.name,
        "ecosystem": ecosystem,
        "pkg_count": len(packages),
        "vuln_count": len(advisories),
        "path": str(repo),
        "exposed_count": sum(1 for a in advisories if a["verdict"] == "exposed"),
        "llm_enabled": llm.available,
    }


async def analyze_advisory_against_repo(
    advisory_id: str,
    repo_path: str | Path,
    *,
    package_name: str | None = None,
    llm: LLMClient | None = None,
    run_preflight: bool = True,
) -> dict[str, Any]:
    """Replay-mode: single advisory vs a local repo."""
    repo = Path(repo_path).expanduser().resolve()
    if not repo.is_dir():
        raise ValueError(f"Not a directory: {repo_path}")

    vuln = await fetch_advisory(advisory_id)
    packages, ecosystem = detect_packages(repo)
    pkg_name = package_name or _package_from_advisory(vuln)

    info = packages.get(pkg_name)
    if info is None:
        # try case-insensitive
        for k, v in packages.items():
            if k.lower() == pkg_name.lower():
                info = v
                pkg_name = k
                break
    if info is None:
        return {
            "id": advisory_id,
            "pkg": pkg_name,
            "current": None,
            "fix": first_fixed_version(
                _ranges_for_package(vuln, pkg_name)
            ),
            "verdict": "safe",
            "confidence": 0.99,
            "reasoning": f"Package {pkg_name} is not a direct dependency of this repo.",
            "nodes": ["triage", "match_dependency"],
            "entrypoints": [],
            "evidence_quotes": [],
            "preflight": None,
            "pr_draft": None,
            "repo": repo.name,
            "ecosystem": ecosystem,
        }

    llm = llm or get_llm_client()
    result = await build_advisory_result(
        repo=repo,
        info=info,
        vuln=vuln,
        ecosystem=ecosystem,
        llm=llm,
        run_preflight=run_preflight,
    )
    result["repo"] = repo.name
    result["ecosystem"] = ecosystem
    return result
