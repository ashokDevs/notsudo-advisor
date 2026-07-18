from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from core.ingestion.osv_client import OSVClient
from core.storage.database import Database


class AdvisoryIngester:
    def __init__(self, db: Database, osv_client: OSVClient) -> None:
        self.db = db
        self.osv_client = osv_client

    async def run_once(self, ecosystem: str, since: datetime) -> int:
        """Fetch updated advisories and upsert them into the database."""
        advisory_ids = await self.osv_client.list_modified_since(ecosystem, since)
        
        upserted_count = 0
        for osv_id in advisory_ids:
            try:
                data = await self.osv_client.get_by_id(osv_id)
                # Parse OSV format into our schema
                package_name = self._extract_package_name(data)
                affected_ranges = self._extract_ranges(data)
                summary = data.get("summary", "")
                details = data.get("details", "")

                await self.db.execute(
                    """
                    INSERT INTO advisories (id, source_id, package_name, affected_ranges, summary, details)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (source_id) DO UPDATE SET
                        package_name = EXCLUDED.package_name,
                        affected_ranges = EXCLUDED.affected_ranges,
                        summary = EXCLUDED.summary,
                        details = EXCLUDED.details;
                    """,
                    uuid4(),
                    osv_id,
                    package_name,
                    json.dumps(affected_ranges),
                    summary,
                    details
                )
                upserted_count += 1
            except Exception:
                # In real code, we'd log and push to a DLQ row
                pass

        return upserted_count

    def _extract_package_name(self, data: dict[str, Any]) -> str:
        affected = data.get("affected", [])
        if affected:
            return affected[0].get("package", {}).get("name", "unknown")
        return "unknown"

    def _extract_ranges(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        affected = data.get("affected", [])
        ranges = []
        if affected:
            for r in affected[0].get("ranges", []):
                ranges.append({"type": r.get("type", "SEMVER"), "events": r.get("events", [])})
        return ranges
