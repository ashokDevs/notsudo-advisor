from __future__ import annotations

from typing import Any

from itsdangerous import BadData, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel, ConfigDict, Field


class RemediationPlan(BaseModel):
    """A server-authorized, short-lived request to open one dependency-fix PR."""

    model_config = ConfigDict(extra="forbid")

    advisory_ids: list[str] = Field(min_length=1)
    package_name: str = Field(min_length=1)
    current_version: str = Field(min_length=1)
    fixed_version: str = Field(min_length=1)
    target_repo: str = Field(min_length=3)
    reasoning: str = Field(min_length=1)
    entrypoints: list[str] = Field(default_factory=list)
    evidence_quotes: list[dict[str, Any]] = Field(default_factory=list)


_SALT = "notsudo-remediation-plan-v1"


def issue_remediation_token(plan: RemediationPlan, *, secret: str) -> str:
    """Sign immutable scan output before it crosses the browser boundary."""
    serializer = URLSafeTimedSerializer(secret_key=secret, salt=_SALT)
    return serializer.dumps(plan.model_dump(mode="json"))


def load_remediation_token(token: str, *, secret: str, max_age_s: int = 900) -> RemediationPlan:
    """Reject altered or stale browser-submitted remediation plans."""
    serializer = URLSafeTimedSerializer(secret_key=secret, salt=_SALT)
    try:
        raw = serializer.loads(token, max_age=max_age_s)
    except SignatureExpired as exc:
        raise ValueError("Remediation plan expired; run the scan again.") from exc
    except BadData as exc:
        raise ValueError("Invalid remediation plan; run the scan again.") from exc
    return RemediationPlan.model_validate(raw)
