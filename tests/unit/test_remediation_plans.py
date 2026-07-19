from __future__ import annotations

from typing import Any

from api.remediation import load_remediation_token
from api.scanner import _attach_remediation_plans
from core.config import session_secret


def _advisory(advisory_id: str, fix: str) -> dict[str, Any]:
    return {
        "id": advisory_id,
        "pkg": "lodash",
        "current": "4.17.20",
        "fix": fix,
        "verdict": "exposed",
        "reasoning": "A request handler invokes merge.",
        "entrypoints": ["src/server.js"],
        "evidence_quotes": [],
        "preflight": {"ok": True},
    }


def test_grouped_plan_uses_one_highest_safe_fix_per_dependency() -> None:
    result: dict[str, Any] = {
        "ecosystem": "npm",
        "advisories": [
            _advisory("GHSA-low", "4.17.21"),
            _advisory("GHSA-high", "4.18.0"),
        ]
    }

    _attach_remediation_plans(result, "owner/repo")

    plans = result["remediation_plans"]
    assert plans == [
        {
            "package": "lodash",
            "current": "4.17.20",
            "fix": "4.18.0",
            "advisory_ids": ["GHSA-low", "GHSA-high"],
            "result_id": "GHSA-high",
        }
    ]
    selected = result["advisories"][1]
    token = load_remediation_token(selected["remediation_token"], secret=session_secret())
    assert token.fixed_version == "4.18.0"
    assert "remediation_token" not in result["advisories"][0]


def test_python_scan_does_not_offer_an_npm_only_fix_plan() -> None:
    result: dict[str, Any] = {
        "ecosystem": "PyPI",
        "advisories": [_advisory("PYSEC-test", "2.0.0")],
    }

    _attach_remediation_plans(result, "owner/repo")

    assert result["remediation_plans"] == []
