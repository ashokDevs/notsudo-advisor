from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from core.ingestion.chunker import Chunker
from core.ingestion.repo_ingester import RepoIngester
from core.storage.database import Database

pytestmark = pytest.mark.asyncio

async def test_repo_ingester_skips_existing(tmp_path: Path) -> None:
    db = AsyncMock(spec=Database)
    # Simulate that chunk already exists in DB
    db.fetchrow.return_value = {"id": uuid4()}
    
    chunker = Chunker()
    ingester = RepoIngester(db, chunker)

    # Create dummy js file
    test_file = tmp_path / "test.js"
    test_file.write_text("function add(a, b) { return a + b; }")

    processed = await ingester.ingest_directory(uuid4(), "sha123", tmp_path)
    
    assert processed == 1
    # fetchrow should be called, but execute should NOT be called because it already exists
    db.fetchrow.assert_called_once()
    db.execute.assert_not_called()

async def test_repo_ingester_inserts_new(tmp_path: Path) -> None:
    db = AsyncMock(spec=Database)
    # Simulate that chunk doesn't exist
    db.fetchrow.return_value = None
    
    chunker = Chunker()
    ingester = RepoIngester(db, chunker)

    test_file = tmp_path / "test.js"
    test_file.write_text("function sub(a, b) { return a - b; }")

    processed = await ingester.ingest_directory(uuid4(), "sha123", tmp_path)
    
    assert processed == 1
    db.fetchrow.assert_called_once()
    db.execute.assert_called_once()
