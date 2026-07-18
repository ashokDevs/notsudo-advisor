import os

import pytest
from httpx import HTTPStatusError

from core.ingestion.osv_client import OSVClient

pytestmark = pytest.mark.asyncio

@pytest.fixture
async def osv_client() -> OSVClient:
    client = OSVClient()
    yield client
    await client.close()

async def test_get_by_id_real(osv_client: OSVClient) -> None:
    if not os.getenv("RUN_REAL_HTTP"):
        pytest.skip("Skipping real HTTP test")
    
    # Real OSV record
    data = await osv_client.get_by_id("GHSA-39hc-v8j9-pqp4")
    assert data["id"] == "GHSA-39hc-v8j9-pqp4"

async def test_get_by_id_not_found(osv_client: OSVClient) -> None:
    if not os.getenv("RUN_REAL_HTTP"):
        pytest.skip("Skipping real HTTP test")
    
    with pytest.raises(HTTPStatusError) as exc:
        await osv_client.get_by_id("FAKE-1234")
    assert exc.value.response.status_code == 404
