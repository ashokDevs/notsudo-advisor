import os
import pytest

from core.action.github_client import GitHubClient

pytestmark = pytest.mark.asyncio

async def test_github_client_no_op_locally() -> None:
    client = GitHubClient(token=None)
    url = await client.draft_pr("owner/repo", "Test PR", "Body", "patch-1")
    assert url is None
    
    is_valid = await client.verify_pat()
    assert is_valid is False
    
    await client.close()

async def test_github_client_invalid_token() -> None:
    client = GitHubClient(token="invalid_token")
    is_valid = await client.verify_pat()
    assert is_valid is False
    await client.close()
