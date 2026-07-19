from __future__ import annotations

import typing
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

import httpx

from core.observability.logging import get_logger

logger = get_logger(__name__)

_MODIFIED_FEED = "https://storage.googleapis.com/osv-vulnerabilities/{ecosystem}/modified_id.csv"


def parse_modified_ids(rows: Iterable[str], *, since: datetime, limit: int) -> list[str]:
    """Read OSV's reverse-chronological modified_id.csv feed up to a watermark."""
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    ids: list[str] = []
    for row in rows:
        modified_text, separator, advisory_id = row.strip().partition(",")
        if not separator or not advisory_id:
            continue
        try:
            modified = datetime.fromisoformat(modified_text.replace("Z", "+00:00"))
        except ValueError:
            continue
        if modified < since:
            break
        ids.append(advisory_id.strip())
        if len(ids) >= limit:
            break
    return ids


class OSVClient:
    def __init__(self, base_url: str = "https://api.osv.dev/v1") -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        await self._client.aclose()

    async def get_by_id(self, osv_id: str) -> dict[str, Any]:
        """Fetch a specific advisory by ID."""
        url = f"{self.base_url}/vulns/{osv_id}"
        response = await self._client.get(url)
        response.raise_for_status()
        return typing.cast(dict[str, Any], response.json())

    async def list_modified_since(
        self,
        ecosystem: str,
        timestamp: datetime,
        *,
        max_results: int = 1_000,
    ) -> list[str]:
        """
        List advisory IDs changed since timestamp via OSV's modified-id feed.

        The /v1/query API only accepts a concrete package query; it cannot list
        an ecosystem's changed advisories. The CSV is reverse chronological, so
        the watermark lets us stop streaming as soon as older data is reached.
        """
        if max_results < 1:
            raise ValueError("max_results must be at least 1")
        url = _MODIFIED_FEED.format(ecosystem=ecosystem)
        rows: list[str] = []
        async with self._client.stream("GET", url) as response:
            response.raise_for_status()
            async for row in response.aiter_lines():
                rows.append(row)
                if len(rows) >= max_results + 1:
                    break
        ids = parse_modified_ids(rows, since=timestamp, limit=max_results)
        logger.info("osv list_modified_since", ecosystem=ecosystem, count=len(ids))
        return ids

    async def query_package(self, name: str, ecosystem: str, version: str | None = None) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"package": {"name": name, "ecosystem": ecosystem}}
        if version:
            payload["version"] = version
        response = await self._client.post(f"{self.base_url}/query", json=payload)
        response.raise_for_status()
        data = response.json()
        return list(data.get("vulns") or [])
