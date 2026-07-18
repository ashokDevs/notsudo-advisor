from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID, uuid4

from core.ingestion.chunker import Chunker
from core.retrieval.embedder import Embedder
from core.storage.database import Database
from core.observability.logging import get_logger

logger = get_logger(__name__)

class RepoIngester:
    def __init__(self, db: Database, chunker: Chunker, embedder: Embedder | None = None) -> None:
        self.db = db
        self.chunker = chunker
        self.embedder = embedder

    async def ingest_directory(self, repo_id: UUID, commit_sha: str, dir_path: Path) -> int:
        """Scan a directory for JS/TS files, chunk them, embed them, and save to DB."""
        if not dir_path.is_dir():
            raise ValueError(f"Not a directory: {dir_path}")

        processed_files = 0
        
        # In a real implementation we would respect .gitignore
        for file_path in dir_path.rglob("*"):
            if not file_path.is_file():
                continue
            
            if file_path.suffix not in (".js", ".jsx", ".ts", ".tsx"):
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
                chunks = self.chunker.chunk_file(str(file_path), content)
                
                if not chunks:
                    continue

                for chunk in chunks:
                    # Check idempotency
                    existing = await self.db.fetchrow(
                        "SELECT id FROM code_chunks WHERE repo_id = $1 AND file_path = $2 AND content_hash = $3",
                        repo_id, str(file_path), chunk["content_hash"]
                    )
                    
                    if existing:
                        continue # Already up to date

                    # Needs insert
                    embedding_vector = None
                    if self.embedder:
                        vectors = await self.embedder.embed_batch([chunk["content"]])
                        if vectors:
                            embedding_vector = vectors[0]

                    await self.db.execute(
                        """
                        INSERT INTO code_chunks (
                            id, repo_id, commit_sha, file_path, start_line, end_line,
                            symbol, content, content_hash, embedding
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                        """,
                        uuid4(),
                        repo_id,
                        commit_sha,
                        chunk["file_path"],
                        chunk["start_line"],
                        chunk["end_line"],
                        chunk["symbol"],
                        chunk["content"],
                        chunk["content_hash"],
                        json.dumps(embedding_vector) if embedding_vector else None
                    )
                
                processed_files += 1

            except Exception as e:
                logger.error("failed to process file", file=str(file_path), error=str(e))

        return processed_files
