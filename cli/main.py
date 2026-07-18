import asyncio
from pathlib import Path
from uuid import uuid4

import typer

from core.ingestion.chunker import Chunker
from core.ingestion.dependency_reader import DependencyReader
from core.ingestion.repo_ingester import RepoIngester
from core.observability.logging import get_logger
from core.retrieval.embedder import Embedder
from core.storage.database import Database

logger = get_logger(__name__)
app = typer.Typer(help="Dependency Exploitability Advisor CLI")

async def _index_repo_async(dir_path: Path, tenant_name: str, repo_url: str) -> None:
    db = Database()
    await db.connect()
    
    try:
        tenant_id = uuid4()
        repo_id = uuid4()
        commit_sha = "local-dev" # mock commit sha for local runs
        
        # 1. Setup tenant and repo
        await db.execute(
            """
            INSERT INTO tenants (id, name) VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            """,
            tenant_id, tenant_name
        )
        
        await db.execute(
            """
            INSERT INTO repos (id, tenant_id, url) VALUES ($1, $2, $3)
            ON CONFLICT DO NOTHING
            """,
            repo_id, tenant_id, repo_url
        )

        logger.info("Starting ingestion", repo_id=str(repo_id), dir=str(dir_path))
        
        # 2. Read dependencies
        dep_reader = DependencyReader(db)
        deps_count = await dep_reader.read_manifests(repo_id, commit_sha, dir_path)
        logger.info("Dependencies parsed", count=deps_count)
        
        # 3. Chunk and embed code
        chunker = Chunker()
        embedder = Embedder()
        ingester = RepoIngester(db, chunker, embedder)
        
        files_count = await ingester.ingest_directory(repo_id, commit_sha, dir_path)
        logger.info("Files chunked and embedded", files_count=files_count)
        
    finally:
        await db.disconnect()

@app.command()
def index(
    directory: Path = typer.Argument(..., help="Path to the repository to index"),
    tenant: str = typer.Option("local", "--tenant", help="Tenant name"),
    repo_url: str = typer.Option("file://local", "--repo-url", help="Repository URL"),
) -> None:
    """Index a local directory (parse package.json + chunk JS/TS files)."""
    if not directory.exists() or not directory.is_dir():
        typer.secho(f"Error: {directory} is not a valid directory.", fg=typer.colors.RED)
        raise typer.Exit(1)

    asyncio.run(_index_repo_async(directory, tenant, repo_url))
    typer.secho("Indexing complete!", fg=typer.colors.GREEN)

async def _run_pipeline_async(advisory_id: str, repo_id: str) -> None:
    # Build graph and state
    from core.orchestration.graph import build_graph
    from core.orchestration.state import AgentState
    
    graph = build_graph()
    
    state: AgentState = {
        "advisory_id": advisory_id,
        "repo_id": repo_id,
        "commit_sha": "local-dev",
        "package_name": None,
        "vulnerable_ranges": [],
        "vulnerable_symbols": ["template"],
        "is_exposed": None,
        "reachability_reasoning": None,
        "retrieved_context": [],
        "retrieval_iterations": 0,
        "pr_draft": None
    }
    
    logger.info("Running pipeline", advisory_id=advisory_id, repo_id=repo_id)
    final_state = await graph.ainvoke(state)
    
    if final_state.get("is_exposed"):
        typer.secho(f"\n[EXPOSED] Reasoning:\n{final_state.get('reachability_reasoning')}", fg=typer.colors.RED)
        if pr := final_state.get("pr_draft"):
            typer.secho(f"\nDraft PR:\nTitle: {pr['title']}\nBody:\n{pr['body']}", fg=typer.colors.YELLOW)
    else:
        typer.secho(f"\n[NOT EXPOSED] Advisory {advisory_id} is not reachable.", fg=typer.colors.GREEN)

@app.command()
def run_pipeline(
    advisory_id: str = typer.Argument(..., help="Advisory ID to run pipeline for"),
    repo_id: str = typer.Argument(..., help="Repo ID to run pipeline against"),
) -> None:
    """Run the reachability pipeline deterministically for a single advisory and repo."""
    asyncio.run(_run_pipeline_async(advisory_id, repo_id))

if __name__ == "__main__":
    app()
