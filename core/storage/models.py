from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AffectedRange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    type: str
    events: list[dict[str, str]]


class Reference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    type: str
    url: str


class Advisory(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    id: UUID
    source_id: str
    package_name: str
    affected_ranges: list[AffectedRange]
    summary: str
    details: str
    embedding: list[float] | None = None
