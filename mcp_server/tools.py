import json
from uuid import UUID

from core.retrieval.embedder import Embedder
from core.storage.database import Database
from mcp_server.server import mcp

# Simple semver check could go here, but for demonstration we check presence
# and optionally do naive string comparison or rely on an external semver library.

_db: Database | None = None
_embedder: Embedder | None = None

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
async def check_vulnerable_dependency(
    repo_id: str, commit_sha: str, package_name: str, affected_ranges_json: str
) -> bool:
    """Check if the given package is present in the repo dependencies at a vulnerable version."""
    db = await get_db()
    
    # For v1 we check if it is declared at all. A real implementation would parse SemVer.
    res = await db.fetchrow(
        "SELECT resolved_version FROM repo_dependencies WHERE repo_id = $1 AND commit_sha = $2 AND package_name = $3",
        UUID(repo_id), commit_sha, package_name
    )
    
    if not res:
        return False
        
    # res["resolved_version"] contains the version.
    # We would parse affected_ranges_json and compare resolved_version against the ranges.
    # For the sake of this prototype, we'll assume it's vulnerable if the package exists.
    # In a complete implementation, we'd use the `semver` python package.
    
    return True

@mcp.tool()
async def code_search(repo_id: str, commit_sha: str, query: str, limit: int = 5) -> str:
    """Search code chunks using hybrid vector + FTS retrieval."""
    db = await get_db()
    embedder = await get_embedder()
    
    # Embed query
    vectors = await embedder.embed_batch([query])
    if not vectors:
        return "[]"
    
    query_embedding = json.dumps(vectors[0])
        
    # We perform a CTE with RRF on vector and fts results.
    # Postgres 16 + pgvector supports vector_cosine_ops
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
