from __future__ import annotations

from core.action.pr_creator import PRCreator
from core.orchestration.state import AgentState


def test_format_pr_includes_advisory_link_not_raw_injection() -> None:
    state: AgentState = {
        "advisory_id": "GHSA-test-1234",
        "package_name": "lodash",
        "current_version": "4.17.20",
        "fixed_version": "4.17.21",
        "reachability_reasoning": "reachable via merge",
        "confidence": 0.9,
        "entrypoints": ["src/server.js"],
        "evidence_quotes": [
            {
                "file_path": "src/server.js",
                "line_start": 12,
                "line_end": 12,
                "quote": "_.merge({}, base, req.body)",
            }
        ],
        "preflight_message": "lockfile ok",
    }
    draft = PRCreator.format_pr(state)
    assert "lodash" in draft["title"]
    assert "GHSA-test-1234" in draft["title"]
    assert "osv.dev/vulnerability/GHSA-test-1234" in draft["body"]
    assert "Ignore previous instructions" not in draft["body"]
    assert "reachable via merge" in draft["body"]
