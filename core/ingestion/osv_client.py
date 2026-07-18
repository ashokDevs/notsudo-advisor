from __future__ import annotations

import typing
from datetime import datetime, timezone
from typing import Any

import httpx

from core.observability.logging import get_logger

logger = get_logger(__name__)


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

    async def list_modified_since(self, ecosystem: str, timestamp: datetime) -> list[str]:
        """
        List advisory IDs modified since timestamp for an ecosystem via OSV query.
        Pages through results best-effort.
        """
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        url = f"{self.base_url}/query"
        payload: dict[str, Any] = {
            "package": {"ecosystem": ecosystem},
            "page_token": "",
        }
        ids: list[str] = []
        seen: set[str] = set()
        for _ in range(10):  # hard page cap
            response = await self._client.post(url, json={k: v for k, v in payload.items() if v != ""})
            response.raise_for_status()
            data = response.json()
            for v in data.get("vulns") or []:
                vid = str(v.get("id", ""))
                modified = v.get("modified")
                if not vid or vid in seen:
                    continue
                if modified:
                    try:
                        mod_dt = datetime.fromisoformat(str(modified).replace("Z", "+00:00"))
                        if mod_dt < timestamp:
                            continue
                    except ValueError:
                        pass
                seen.add(vid)
                ids.append(vid)
            next_token = data.get("next_page_token")
            if not next_token:
                break
            payload["page_token"] = next_token
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
