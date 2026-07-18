from uuid import uuid4

import pytest
from pydantic import ValidationError

from core.storage.models import Advisory


def test_advisory_round_trip() -> None:
    data = {
        "id": str(uuid4()),
        "source_id": "GHSA-1234",
        "package_name": "lodash",
        "affected_ranges": [
            {"type": "SEMVER", "events": [{"introduced": "0"}, {"fixed": "4.17.21"}]}
        ],
        "summary": "Prototype pollution",
        "details": "Details here",
    }
    adv = Advisory.model_validate(data)
    assert adv.source_id == "GHSA-1234"
    assert adv.package_name == "lodash"
    assert len(adv.affected_ranges) == 1

def test_unknown_field_rejected_when_extra_forbid() -> None:
    data = {
        "id": str(uuid4()),
        "source_id": "GHSA-1234",
        "package_name": "lodash",
        "affected_ranges": [],
        "summary": "Prototype pollution",
        "details": "Details here",
        "unknown_field": "should fail",
    }
    with pytest.raises(ValidationError):
        Advisory.model_validate(data)
