from __future__ import annotations

import httpx

from core.observability.logging import get_logger

logger = get_logger(__name__)

class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        self.token = token
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"
            
        self._client = httpx.AsyncClient(
            base_url="https://api.github.com",
            headers=headers,
            timeout=10.0
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def verify_pat(self) -> bool:
        """Verify the Personal Access Token is valid."""
        if not self.token:
            return False
            
        response = await self._client.get("/user")
        return response.status_code == 200

    async def draft_pr(self, repo: str, title: str, body: str, head: str, base: str = "main") -> str | None:
        """Draft a pull request on GitHub. If no token, log and no-op locally."""
        if not self.token:
            logger.info("Local run, skipping PR creation", repo=repo, title=title)
            return None
            
        logger.info("Drafting PR", repo=repo, title=title)
        
        response = await self._client.post(
            f"/repos/{repo}/pulls",
            json={
                "title": title,
                "body": body,
                "head": head,
                "base": base
            }
        )
        response.raise_for_status()
        data = response.json()
        return data.get("html_url")
