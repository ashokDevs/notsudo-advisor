import json
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from core.ingestion.dependency_reader import DependencyReader
from core.storage.database import Database

pytestmark = pytest.mark.asyncio

async def test_dependency_reader_package_json(tmp_path: Path) -> None:
    db = AsyncMock(spec=Database)
    reader = DependencyReader(db)

    pkg_json = tmp_path / "package.json"
    pkg_json.write_text(json.dumps({
        "dependencies": {"lodash": "^4.17.20"},
        "devDependencies": {"jest": "29.0.0"}
    }))

    pkg_lock = tmp_path / "package-lock.json"
    pkg_lock.write_text(json.dumps({
        "dependencies": {
            "lodash": {"version": "4.17.21"}
        }
    }))

    repo_id = uuid4()
    count = await reader.read_manifests(repo_id, "commit_sha", tmp_path)
    
    assert count == 2
    assert db.execute.call_count == 2
    
    # Check lodash call (first dependency)
    args, _ = db.execute.call_args_list[0]
    # args is query, id, repo_id, commit_sha, package_name, declared, resolved
    assert args[4] == "lodash"
    assert args[5] == "^4.17.20"
    assert args[6] == "4.17.21"
