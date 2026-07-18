from __future__ import annotations

from core.analysis.semver import (
    parse_version,
    version_affected_by_ranges,
    version_in_osv_events,
)


def test_parse_version_basic() -> None:
    v = parse_version("4.17.20")
    assert v is not None
    assert (v.major, v.minor, v.patch) == (4, 17, 20)


def test_parse_version_with_prefix() -> None:
    v = parse_version("^4.17.20")
    assert v is not None
    assert str(v) == "4.17.20"


def test_in_range_introduced_fixed() -> None:
    events = [{"introduced": "0"}, {"fixed": "4.17.21"}]
    assert version_in_osv_events("4.17.20", events) is True
    assert version_in_osv_events("4.17.21", events) is False


def test_version_affected_by_ranges() -> None:
    ranges = [{"type": "SEMVER", "events": [{"introduced": "0"}, {"fixed": "1.2.6"}]}]
    assert version_affected_by_ranges("1.2.5", ranges) is True
    assert version_affected_by_ranges("1.2.6", ranges) is False
