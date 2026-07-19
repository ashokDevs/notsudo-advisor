from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import UUID

from core.analysis.call_sites import CallSiteFinder
from core.analysis.pipeline import detect_packages, fetch_advisory
from core.analysis.preflight import preflight_bump
from core.analysis.semver import version_affected_by_ranges
from core.observability.logging import get_logger
from core.retrieval.embedder import Embedder
from core.security.capability_graph import CapabilityGraph
from core.storage.database import Database
from mcp_server.server import authorize, mcp

logger = get_logger(__name__)
_caps = CapabilityGraph.from_permissions()

_db: Database | None = None
_embedder: Embedder | None = None


def _side_effect_node_identity() -> str:
    """Read node identity from server configuration, never MCP client input."""
    return os.getenv("NOTSUDO_MCP_NODE_ID", "").strip()


async def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
        await _db.connect()
    return _db


async def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


@mcp.tool()
async def advisory_query(advisory_id: str, node: str = "triage") -> str:
    """Fetch an OSV/GHSA advisory by id (read-only)."""
    authorize(node, "advisory_query")
    data = await fetch_advisory(advisory_id)
    # Return sanitized subset — not full attacker-controlled body to every caller
    return json.dumps(
        {
            "id": data.get("id"),
            "summary": data.get("summary"),
            "affected": data.get("affected"),
            "references": data.get("references"),
            "severity": data.get("severity"),
        },
        indent=2,
        default=str,
    )


@mcp.tool()
async def dep_manifest_read(repo_path: str, node: str = "triage") -> str:
    """Read dependency manifests from a local repo path."""
    authorize(node, "dep_manifest_read")
    packages, ecosystem = detect_packages(Path(repo_path))
    return json.dumps(
        {
            "ecosystem": ecosystem,
            "packages": {k: v.model_dump() for k, v in packages.items()},
        },
        indent=2,
    )


@mcp.tool()
async def check_vulnerable_dependency(
    repo_id: str,
    commit_sha: str,
    package_name: str,
    affected_ranges_json: str,
    node: str = "triage",
) -> bool:
    """Check if package is present at a vulnerable version (semver-aware)."""
    authorize(node, "check_vulnerable_dependency")
    db = await get_db()
    res = await db.fetchrow(
        "SELECT resolved_version FROM repo_dependencies WHERE repo_id = $1 AND commit_sha = $2 AND package_name = $3",
        UUID(repo_id),
        commit_sha,
        package_name,
    )
    if not res:
        return False
    version = str(res["resolved_version"])
    try:
        ranges = json.loads(affected_ranges_json) if affected_ranges_json else []
    except json.JSONDecodeError:
        ranges = []
    if not ranges:
        return True
    return version_affected_by_ranges(version, ranges)


@mcp.tool()
async def code_search(
    repo_id: str,
    commit_sha: str,
    query: str,
    limit: int = 5,
    node: str = "locate",
) -> str:
    """Search code chunks using hybrid vector + FTS retrieval when DB is available."""
    authorize(node, "code_search")
    db = await get_db()
    embedder = await get_embedder()

    vectors = await embedder.embed_batch([query])
    if not vectors:
        return "[]"

    query_embedding = json.dumps(vectors[0])
    sql = """
    WITH vector_search AS (
        SELECT id, file_path, start_line, end_line, content, symbol,
               ROW_NUMBER() OVER (ORDER BY embedding <=> $3::vector) as rank
        FROM code_chunks
        WHERE repo_id = $1 AND commit_sha = $2
        ORDER BY embedding <=> $3::vector
        LIMIT 50
    ),
    fts_search AS (
        SELECT id, file_path, start_line, end_line, content, symbol,
               ROW_NUMBER() OVER (ORDER BY ts_rank(fts, websearch_to_tsquery('english', $4)) DESC) as rank
        FROM code_chunks
        WHERE repo_id = $1 AND commit_sha = $2 AND fts @@ websearch_to_tsquery('english', $4)
        ORDER BY ts_rank(fts, websearch_to_tsquery('english', $4)) DESC
        LIMIT 50
    ),
    combined AS (
        SELECT
            COALESCE(v.id, f.id) as id,
            COALESCE(v.file_path, f.file_path) as file_path,
            COALESCE(v.start_line, f.start_line) as start_line,
            COALESCE(v.end_line, f.end_line) as end_line,
            COALESCE(v.content, f.content) as content,
            COALESCE(v.symbol, f.symbol) as symbol,
            COALESCE(1.0 / (60 + v.rank), 0.0) + COALESCE(1.0 / (60 + f.rank), 0.0) as rrf_score
        FROM vector_search v
        FULL OUTER JOIN fts_search f ON v.id = f.id
    )
    SELECT file_path, start_line, end_line, symbol, content
    FROM combined
    ORDER BY rrf_score DESC
    LIMIT $5;
    """
    results = await db.fetch(sql, UUID(repo_id), commit_sha, query_embedding, query, limit)
    return json.dumps([dict(r) for r in results], indent=2)


@mcp.tool()
async def code_read(repo_path: str, file_path: str, start_line: int = 1, end_line: int = 50, node: str = "reason") -> str:
    """Read a file range from a local repository."""
    authorize(node, "code_read")
    root = Path(repo_path).resolve()
    target = (root / file_path).resolve()
    if not str(target).startswith(str(root)) or not target.is_file():
        return json.dumps({"error": "file not found or outside repo"})
    lines = target.read_text(encoding="utf-8", errors="ignore").splitlines()
    start = max(1, start_line)
    end = min(len(lines), end_line)
    snippet = "\n".join(f"{i}| {lines[i-1]}" for i in range(start, end + 1))
    return json.dumps({"file_path": file_path, "start_line": start, "end_line": end, "content": snippet})


@mcp.tool()
async def locate_call_sites(
    repo_path: str,
    package_name: str,
    symbols_json: str = "[]",
    node: str = "locate",
) -> str:
    """Find import and call sites for a package / symbols."""
    authorize(node, "locate_call_sites")
    try:
        symbols = json.loads(symbols_json)
        if not isinstance(symbols, list):
            symbols = []
    except json.JSONDecodeError:
        symbols = []
    finder = CallSiteFinder()
    sites = finder.find(Path(repo_path), package_name, symbols=[str(s) for s in symbols])
    return json.dumps([s.model_dump() for s in sites], indent=2)


@mcp.tool()
async def dep_registry_query(package_name: str, ecosystem: str = "npm", node: str = "triage") -> str:
    """Query registry metadata (npm) for latest version hints."""
    authorize(node, "dep_registry_query")
    import httpx

    if ecosystem.lower() != "npm":
        return json.dumps({"error": f"ecosystem {ecosystem} not supported yet"})
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"https://registry.npmjs.org/{package_name}")
        if resp.status_code != 200:
            return json.dumps({"error": f"registry status {resp.status_code}"})
        data = resp.json()
        return json.dumps(
            {
                "name": data.get("name"),
                "latest": (data.get("dist-tags") or {}).get("latest"),
                "description": data.get("description"),
            }
        )


@mcp.tool()
async def git_blame(repo_path: str, file_path: str, line: int, node: str = "locate") -> str:
    """Best-effort git blame for a line (requires git)."""
    authorize(node, "git_blame")
    import asyncio

    root = Path(repo_path).resolve()
    proc = await asyncio.create_subprocess_exec(
        "git",
        "blame",
        "-L",
        f"{line},{line}",
        "--",
        file_path,
        cwd=str(root),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        return json.dumps({"error": stderr.decode("utf-8", errors="replace")[:300]})
    return json.dumps({"blame": stdout.decode("utf-8", errors="replace").strip()})


@mcp.tool()
async def preflight_lockfile(
    repo_path: str,
    package_name: str,
    fixed_version: str,
    ecosystem: str = "npm",
    node: str = "preflight",
) -> str:
    """Run package manager preflight for a proposed bump."""
    authorize(node, "preflight_lockfile")
    result = await preflight_bump(Path(repo_path), package_name, fixed_version, ecosystem=ecosystem)
    return result.model_dump_json()


@mcp.tool()
async def pr_create(
    title: str,
    body: str,
) -> str:
    """
    Side-effecting tool: create a PR draft description record.
    Actual GitHub API write is done by the API layer with user OAuth token.
    This tool only formats / records intent and is restricted to draft_pr/act.
    """
    node = _side_effect_node_identity()
    if node not in {"draft_pr", "act"}:
        raise PermissionError(
            "pr_create requires NOTSUDO_MCP_NODE_ID=draft_pr or act on the server"
        )
    authorize(node, "pr_create")
    return json.dumps(
        {
            "status": "draft_ready",
            "title": title,
            "body": body,
            "note": "Open via /api/pr with GitHub OAuth for the real PR.",
        }
    )


def list_registered_tools() -> list[str]:
    return [
        "advisory_query",
        "dep_manifest_read",
        "check_vulnerable_dependency",
        "code_search",
        "code_read",
        "locate_call_sites",
        "dep_registry_query",
        "git_blame",
        "preflight_lockfile",
        "pr_create",
    ]
