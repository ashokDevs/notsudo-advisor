from __future__ import annotations

import typing
from datetime import datetime
from typing import Any

import httpx

from core.observability.logging import get_logger

logger = get_logger(__name__)


class OSVClient:
    def __init__(self, base_url: str = "https://api.osv.dev/v1") -> None:
        self.base_url = base_url.rstrip("/")
        # coding rule 5.2: Every external call has timeout=
        self._client = httpx.AsyncClient(timeout=10.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def get_by_id(self, osv_id: str) -> dict[str, Any]:
        """Fetch a specific advisory by ID."""
        url = f"{self.base_url}/vulns/{osv_id}"
        response = await self._client.get(url)
        response.raise_for_status()
        return typing.cast(dict[str, Any], response.json())

    async def list_modified_since(self, ecosystem: str, timestamp: datetime) -> list[str]:
        """List advisory IDs modified since the given timestamp for an ecosystem.
        Note: OSV API doesn't have a direct 'modified since' endpoint that returns just IDs,
        so we query by events/ecosystem and filter, or use the query API.
        For demonstration, we use a placeholder post query.
        """
        url = f"{self.base_url}/query"
        payload = {
            "ecosystem": ecosystem,
            # In a real implementation we would page through results
        }
        # Simplified query for now, assuming it returns something we can parse
        response = await self._client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        vulns = data.get("vulns", [])
        return [v["id"] for v in vulns]
