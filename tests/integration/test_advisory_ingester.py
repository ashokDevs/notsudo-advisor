from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock

from core.ingestion.advisory_ingester import AdvisoryIngester
from core.ingestion.osv_client import OSVClient
from core.storage.database import Database

pytestmark = pytest.mark.asyncio

async def test_ingester_upsert() -> None:
    db = AsyncMock(spec=Database)
    osv_client = AsyncMock(spec=OSVClient)
    
    osv_client.list_modified_since.return_value = ["GHSA-1234"]
    osv_client.get_by_id.return_value = {
        "id": "GHSA-1234",
        "affected": [{"package": {"name": "lodash"}, "ranges": [{"type": "SEMVER", "events": []}]}],
        "summary": "test summary",
        "details": "test details"
    }

    ingester = AdvisoryIngester(db, osv_client)
    
    count = await ingester.run_once("npm", datetime.now(timezone.utc))
    assert count == 1
    db.execute.assert_called_once()
