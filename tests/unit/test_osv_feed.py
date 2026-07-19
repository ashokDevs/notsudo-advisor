from __future__ import annotations

from datetime import UTC, datetime

from core.ingestion.osv_client import parse_modified_ids


def test_modified_feed_stops_at_the_persisted_watermark() -> None:
    rows = [
        "2026-07-19T09:00:00Z,GHSA-new",
        "2026-07-19T08:00:00Z,GHSA-same",
        "2026-07-19T07:59:59Z,GHSA-old",
    ]

    result = parse_modified_ids(
        rows,
        since=datetime(2026, 7, 19, 8, 0, tzinfo=UTC),
        limit=10,
    )

    assert result == ["GHSA-new", "GHSA-same"]


def test_modified_feed_respects_the_run_cap() -> None:
    rows = [
        "2026-07-19T09:00:00Z,GHSA-one",
        "2026-07-19T08:30:00Z,GHSA-two",
    ]

    result = parse_modified_ids(
        rows,
        since=datetime(2026, 7, 19, 8, 0, tzinfo=UTC),
        limit=1,
    )

    assert result == ["GHSA-one"]
