from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from core.ingestion.osv_client import OSVClient
from core.retrieval.embedder import Embedder
from core.storage.database import Database


class AdvisoryIngester:
    def __init__(self, db: Database, osv_client: OSVClient, embedder: Embedder | None = None) -> None:
        self.db = db
        self.osv_client = osv_client
        self.embedder = embedder

    async def run_once(self, ecosystem: str, since: datetime) -> int:
        """Fetch updated advisories and upsert them into the database."""
        advisory_ids = await self.osv_client.list_modified_since(ecosystem, since)
        
        upserted_count = 0
        for osv_id in advisory_ids:
            try:
                data = await self.osv_client.get_by_id(osv_id)
                package_name = self._extract_package_name(data)
                affected_ranges = self._extract_ranges(data)
                summary = data.get("summary", "")
                details = data.get("details", "")

                embedding_text = f"{summary}\n{details}".strip()
                embedding = None
                if self.embedder and embedding_text:
                    vectors = await self.embedder.embed_batch([embedding_text])
                    if vectors:
                        embedding = vectors[0]

                await self.db.execute(
                    "insert_advisory",
                    uuid4(),
                    osv_id,
                    package_name,
                    json.dumps(affected_ranges),
                    summary,
                    details,
                    json.dumps(embedding) if embedding else None
                )
                upserted_count += 1
            except Exception:
                pass

        return upserted_count

    def _extract_package_name(self, data: dict[str, Any]) -> str:
        affected = data.get("affected", [])
        if affected:
            pkg = affected[0].get("package", {})
            return str(pkg.get("name", "unknown"))
        return "unknown"

    def _extract_ranges(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        affected = data.get("affected", [])
        ranges = []
        if affected:
            for r in affected[0].get("ranges", []):
                ranges.append({"type": r.get("type", "SEMVER"), "events": r.get("events", [])})
        return ranges
