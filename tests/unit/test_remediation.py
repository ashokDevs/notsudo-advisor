from __future__ import annotations

import pytest

from api.remediation import RemediationPlan, issue_remediation_token, load_remediation_token


def _plan() -> RemediationPlan:
    return RemediationPlan(
        advisory_ids=["GHSA-one", "GHSA-two"],
        package_name="lodash",
        current_version="4.17.20",
        fixed_version="4.17.21",
        target_repo="owner/repo",
        reasoning="The reachable merge call accepts request data.",
        entrypoints=["src/server.js"],
        evidence_quotes=[],
    )


def test_signed_remediation_plan_round_trips_without_browser_fields() -> None:
    token = issue_remediation_token(_plan(), secret="test-secret")

    result = load_remediation_token(token, secret="test-secret")

    assert result == _plan()


def test_tampered_remediation_plan_is_rejected() -> None:
    token = issue_remediation_token(_plan(), secret="test-secret")

    with pytest.raises(ValueError, match="Invalid remediation plan"):
        load_remediation_token(f"{token}tampered", secret="test-secret")
