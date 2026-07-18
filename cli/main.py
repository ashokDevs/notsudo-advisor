from __future__ import annotations

# Load .env before other modules read keys
import core.config  # noqa: F401

import asyncio
import json
from pathlib import Path
from uuid import uuid4

import typer

from core.observability.logging import get_logger

logger = get_logger(__name__)
app = typer.Typer(help="NotSudo Advisor — find reachable vulns and draft fix PRs")


@app.command()
def scan(
    target: str = typer.Argument(
        ...,
        help="Local path, GitHub URL, or owner/repo (e.g. https://github.com/expressjs/express)",
    ),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON"),
    no_preflight: bool = typer.Option(False, "--no-preflight", help="Skip lockfile preflight"),
) -> None:
    """Scan a local path or public GitHub repo: OSV → reachability → preflight."""
    from api.scanner import scan_repo
    from core.analysis.github_clone import cleanup_target, resolve_scan_target
    from core.analysis.pipeline import analyze_repo

    async def _run() -> dict:
        # Always resolve (clone GitHub if needed), then analyze. Preserve metadata.
        t = await resolve_scan_target(target)
        try:
            result = await analyze_repo(str(t.path), run_preflight=not no_preflight)
            if t.source == "github":
                result["repo"] = t.display_name
                result["github_url"] = t.github_url
                result["source"] = "github"
            else:
                result["source"] = "local"
            result["display_name"] = t.display_name
            result["scan_target"] = target
            ads = result.get("advisories") or []
            result["summary"] = {
                "packages": result.get("pkg_count", 0),
                "vulns": result.get("vuln_count", len(ads)),
                "exposed": sum(1 for a in ads if a.get("verdict") == "exposed"),
                "safe": sum(1 for a in ads if a.get("verdict") == "safe"),
                "unsure": sum(1 for a in ads if a.get("verdict") == "unsure"),
                "presence_noise": sum(1 for a in ads if a.get("verdict") in {"safe", "unsure"}),
            }
            return result
        finally:
            cleanup_target(t)

    result = asyncio.run(_run())
    if json_out:
        typer.echo(json.dumps(result, indent=2, default=str))
        return

    summary = result.get("summary") or {}
    typer.secho(
        f"\nRepo: {result.get('repo')}  source={result.get('source', 'local')}  "
        f"ecosystem={result.get('ecosystem')}  "
        f"packages={result.get('pkg_count')}  advisories={result.get('vuln_count')}  "
        f"exposed={summary.get('exposed', result.get('exposed_count', 0))}  "
        f"safe={summary.get('safe', '?')}  unsure={summary.get('unsure', '?')}  "
        f"llm={result.get('llm_enabled')}\n",
        fg=typer.colors.CYAN,
    )
    if summary.get("presence_noise") is not None:
        typer.secho(
            f"  presence-style noise (safe+unsure): {summary['presence_noise']}  ·  "
            f"reachability-confirmed exposed: {summary.get('exposed', 0)}",
            fg=typer.colors.MAGENTA,
        )
    for adv in result.get("advisories") or []:
        color = {
            "exposed": typer.colors.RED,
            "unsure": typer.colors.YELLOW,
            "safe": typer.colors.GREEN,
        }.get(str(adv.get("verdict")), typer.colors.WHITE)
        typer.secho(
            f"[{adv.get('verdict')}] {adv.get('id')}  {adv.get('pkg')}@"
            f"{adv.get('current')} → {adv.get('fix') or '?'}  "
            f"conf={adv.get('confidence')}",
            fg=color,
        )
        sites = adv.get("call_sites") or []
        if sites:
            top = sites[0]
            typer.echo(
                f"  call site: {top.get('file_path')}:{top.get('line')}  {top.get('snippet', '')[:80]}"
            )
        typer.echo(f"  {adv.get('reasoning', '')[:200]}")
        if adv.get("pr_draft"):
            typer.secho(f"  PR draft ready: {adv['pr_draft']['title']}", fg=typer.colors.MAGENTA)


@app.command("analyze")
def analyze_cmd(
    advisory_id: str = typer.Argument(..., help="OSV/GHSA id"),
    directory: Path = typer.Argument(..., help="Local repo path"),
    package: str | None = typer.Option(None, "--package", help="Override package name"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Replay a single advisory against a local repo (deterministic demo path)."""
    from core.analysis.pipeline import analyze_advisory_against_repo

    result = asyncio.run(
        analyze_advisory_against_repo(advisory_id, directory, package_name=package)
    )
    if json_out:
        typer.echo(json.dumps(result, indent=2, default=str))
        return
    verdict = result.get("verdict")
    color = {"exposed": typer.colors.RED, "safe": typer.colors.GREEN}.get(
        str(verdict), typer.colors.YELLOW
    )
    typer.secho(f"\n[{verdict}] {result.get('id')} {result.get('pkg')}", fg=color)
    typer.echo(result.get("reasoning"))
    if result.get("pr_draft"):
        typer.secho("\n--- PR draft ---", fg=typer.colors.MAGENTA)
        typer.echo(result["pr_draft"]["title"])
        typer.echo(result["pr_draft"]["body"])


async def _index_repo_async(dir_path: Path, tenant_name: str, repo_url: str) -> None:
    from core.ingestion.chunker import Chunker
    from core.ingestion.dependency_reader import DependencyReader
    from core.ingestion.repo_ingester import RepoIngester
    from core.retrieval.embedder import Embedder
    from core.storage.database import Database

    db = Database()
    await db.connect()
    try:
        tenant_id = uuid4()
        repo_id = uuid4()
        commit_sha = "local-dev"
        await db.execute(
            """
            INSERT INTO tenants (id, name) VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            """,
            tenant_id,
            tenant_name,
        )
        await db.execute(
            """
            INSERT INTO repos (id, tenant_id, url) VALUES ($1, $2, $3)
            ON CONFLICT DO NOTHING
            """,
            repo_id,
            tenant_id,
            repo_url,
        )
        dep_reader = DependencyReader(db)
        deps_count = await dep_reader.read_manifests(repo_id, commit_sha, dir_path)
        logger.info("Dependencies parsed", count=deps_count)
        chunker = Chunker()
        embedder: Embedder | None
        try:
            embedder = Embedder()
        except Exception as exc:
            logger.warning("Embedder unavailable, indexing without vectors", error=str(exc))
            embedder = None
        ingester = RepoIngester(db, chunker, embedder)
        files_count = await ingester.ingest_directory(repo_id, commit_sha, dir_path)
        logger.info("Files chunked", files_count=files_count, repo_id=str(repo_id))
        typer.echo(f"repo_id={repo_id} commit_sha={commit_sha}")
    finally:
        await db.disconnect()


@app.command()
def index(
    directory: Path = typer.Argument(..., help="Path to the repository to index"),
    tenant: str = typer.Option("local", "--tenant", help="Tenant name"),
    repo_url: str = typer.Option("file://local", "--repo-url", help="Repository URL"),
) -> None:
    """Index a local directory into Postgres (deps + code chunks)."""
    if not directory.exists() or not directory.is_dir():
        typer.secho(f"Error: {directory} is not a valid directory.", fg=typer.colors.RED)
        raise typer.Exit(1)
    asyncio.run(_index_repo_async(directory, tenant, repo_url))
    typer.secho("Indexing complete!", fg=typer.colors.GREEN)


async def _run_pipeline_async(advisory_id: str, repo_path: str) -> None:
    from core.orchestration.graph import build_graph
    from core.orchestration.state import AgentState

    graph = build_graph()
    state: AgentState = {
        "advisory_id": advisory_id,
        "repo_id": "local",
        "commit_sha": "local-dev",
        "repo_path": repo_path,
        "package_name": None,
        "vulnerable_ranges": [],
        "vulnerable_symbols": [],
        "is_exposed": None,
        "reachability_reasoning": None,
        "retrieved_context": [],
        "retrieval_iterations": 0,
        "pr_draft": None,
        "nodes_run": [],
    }
    logger.info("Running pipeline", advisory_id=advisory_id, repo_path=repo_path)
    final_state = await graph.ainvoke(state)

    verdict = final_state.get("verdict")
    if final_state.get("is_exposed"):
        typer.secho(
            f"\n[EXPOSED] {verdict}\n{final_state.get('reachability_reasoning')}",
            fg=typer.colors.RED,
        )
        if pr := final_state.get("pr_draft"):
            typer.secho(f"\nDraft PR:\nTitle: {pr['title']}\n\n{pr['body']}", fg=typer.colors.YELLOW)
    elif verdict == "unsure":
        typer.secho(
            f"\n[UNSURE]\n{final_state.get('reachability_reasoning')}",
            fg=typer.colors.YELLOW,
        )
    else:
        typer.secho(
            f"\n[NOT EXPOSED] Advisory {advisory_id} is not reachable.\n"
            f"{final_state.get('reachability_reasoning')}",
            fg=typer.colors.GREEN,
        )


@app.command("run-pipeline")
def run_pipeline(
    advisory_id: str = typer.Argument(..., help="Advisory ID"),
    repo_path: Path = typer.Argument(..., help="Local path to the target repo"),
) -> None:
    """Run the full LangGraph agent (triage → locate → reason → preflight → act)."""
    if not repo_path.is_dir():
        typer.secho(f"Not a directory: {repo_path}", fg=typer.colors.RED)
        raise typer.Exit(1)
    asyncio.run(_run_pipeline_async(advisory_id, str(repo_path.resolve())))


@app.command("watch-osv")
def watch_osv(
    ecosystem: str = typer.Option("npm", "--ecosystem"),
    hours: int = typer.Option(24, "--hours", help="Look back window"),
) -> None:
    """List recent OSV advisories for an ecosystem (live feed peek)."""
    import datetime as dt

    from core.ingestion.osv_client import OSVClient

    async def _run() -> None:
        client = OSVClient()
        since = dt.datetime.now(dt.UTC) - dt.timedelta(hours=hours)
        ids = await client.list_modified_since(ecosystem, since)
        typer.echo(f"{len(ids)} advisories modified in last {hours}h for {ecosystem}")
        for i in ids[:30]:
            typer.echo(i)

    asyncio.run(_run())


@app.command("demo")
def demo_cmd(
    target: str = typer.Option(
        "demo_app",
        "--target",
        "-t",
        help="Local path or GitHub URL (default: bundled demo_app)",
    ),
) -> None:
    """
    90-second win demo: scan → presence vs exposure split → show call sites → PR drafts.
    Talk track: docs/demo_script.md
    """
    from api.scanner import scan_repo

    typer.secho("\n══ NotSudo · 90s demo ══\n", fg=typer.colors.CYAN, bold=True)
    typer.echo("Dependabot flags packages. NotSudo flags only what your code can actually hit.\n")

    typer.secho(f"→ Scanning {target} …", fg=typer.colors.YELLOW)
    result = asyncio.run(scan_repo(target))
    summary = result.get("summary") or {}
    ads = result.get("advisories") or []

    typer.secho(
        f"\n  packages checked : {summary.get('packages', result.get('pkg_count'))}",
        fg=typer.colors.WHITE,
    )
    typer.secho(
        f"  vulns on OSV     : {summary.get('vulns', len(ads))}  ← presence-style noise ceiling",
        fg=typer.colors.WHITE,
    )
    typer.secho(
        f"  EXPOSED          : {summary.get('exposed', 0)}  ← open fix PRs for these",
        fg=typer.colors.RED,
        bold=True,
    )
    typer.secho(
        f"  safe / unsure    : {summary.get('safe', 0)} / {summary.get('unsure', 0)}  ← don't waste eng time",
        fg=typer.colors.GREEN,
    )

    exposed = [a for a in ads if a.get("verdict") == "exposed"]
    if exposed:
        typer.secho("\n── Reachability-confirmed (call sites) ──", fg=typer.colors.MAGENTA)
        for a in exposed[:5]:
            typer.secho(f"\n  {a.get('pkg')}@{a.get('current')} → {a.get('fix')}  ({a.get('id')})", fg=typer.colors.RED)
            for cs in (a.get("call_sites") or [])[:3]:
                if cs.get("kind") == "call" or True:
                    typer.echo(
                        f"    {cs.get('file_path')}:{cs.get('line')}  {cs.get('snippet', '')[:90]}"
                    )
            if a.get("pr_draft"):
                typer.secho(f"    ✓ fix PR draft ready", fg=typer.colors.GREEN)

    typer.secho(
        "\n── Security ──\n  Advisory text is untrusted. Only the act node can open PRs (capability isolation).\n",
        fg=typer.colors.CYAN,
    )
    typer.echo("Dashboard: http://127.0.0.1:8080/Dashboard.html")
    typer.echo("Full talk track: docs/demo_script.md\n")


if __name__ == "__main__":
    app()
