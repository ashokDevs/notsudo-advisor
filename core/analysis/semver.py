from __future__ import annotations

import re
from dataclasses import dataclass

_VERSION_RE = re.compile(
    r"""
    ^v?
    (?P<major>0|[1-9]\d*)
    \.
    (?P<minor>0|[1-9]\d*)
    \.
    (?P<patch>0|[1-9]\d*)
    (?:-(?P<prerelease>[0-9A-Za-z.-]+))?
    (?:\+(?P<build>[0-9A-Za-z.-]+))?
    $
    """,
    re.VERBOSE,
)


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            return f"{base}-{'.'.join(self.prerelease)}"
        return base


def parse_version(raw: str) -> Version | None:
    """Parse a semver-ish version string. Returns None if unparseable."""
    text = raw.strip()
    text = re.sub(r"^[\^~>=<\s]+", "", text)
    text = text.split(" ")[0].split(",")[0].strip()
    m = _VERSION_RE.match(text)
    if not m:
        parts = re.split(r"[.\-+]", text)
        try:
            major = int(parts[0]) if parts and parts[0].isdigit() else None
            minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            patch = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
            if major is None:
                return None
            return Version(major, minor, patch)
        except (ValueError, IndexError):
            return None
    pre = tuple(m.group("prerelease").split(".")) if m.group("prerelease") else ()
    return Version(int(m.group("major")), int(m.group("minor")), int(m.group("patch")), pre)


def strip_version(raw: str) -> str:
    cleaned = re.sub(r"^[\^~>=<v\s]+", "", raw.strip())
    return cleaned.split(" ")[0].split(",")[0]


def _in_window(ver: Version, introduced: Version, fixed: Version | None, last_affected: Version | None) -> bool:
    if ver < introduced:
        return False
    if fixed is not None:
        return ver < fixed
    if last_affected is not None:
        return ver <= last_affected
    # open-ended: everything >= introduced is affected
    return True


def version_in_osv_events(version: str, events: list[dict[str, str]]) -> bool:
    """
    OSV range events are ordered introduced / fixed / last_affected markers.
    A version is affected if it falls in any [introduced, fixed) or
    [introduced, last_affected] window.
    """
    ver = parse_version(version)
    if ver is None:
        return True  # conservative

    windows: list[tuple[Version, Version | None, Version | None]] = []
    current_introduced: Version | None = None
    current_fixed: Version | None = None
    current_last: Version | None = None

    def flush() -> None:
        nonlocal current_introduced, current_fixed, current_last
        if current_introduced is not None:
            windows.append((current_introduced, current_fixed, current_last))
        current_introduced = None
        current_fixed = None
        current_last = None

    for ev in events:
        if "introduced" in ev:
            # starting a new window — flush previous open one
            if current_introduced is not None:
                flush()
            intro_raw = str(ev["introduced"])
            current_introduced = parse_version(intro_raw) if intro_raw not in {"0", "0.0.0"} else Version(0, 0, 0)
            if current_introduced is None:
                current_introduced = Version(0, 0, 0)
            current_fixed = None
            current_last = None
        if "fixed" in ev and current_introduced is not None:
            current_fixed = parse_version(str(ev["fixed"]))
            flush()
        if "last_affected" in ev and current_introduced is not None:
            current_last = parse_version(str(ev["last_affected"]))
            flush()

    if current_introduced is not None:
        flush()

    for introduced, fixed, last_affected in windows:
        if _in_window(ver, introduced, fixed, last_affected):
            return True
    return False


def version_affected_by_ranges(version: str, ranges: list[dict]) -> bool:
    """True if version is in any OSV-style range object."""
    if not ranges:
        return True
    any_events = False
    for r in ranges:
        events = r.get("events") or []
        if not events:
            continue
        any_events = True
        norm = [{k: str(v) for k, v in ev.items()} for ev in events if isinstance(ev, dict)]
        if version_in_osv_events(version, norm):
            return True
    # If ranges exist but had no events, be conservative
    return not any_events


def first_fixed_version(ranges: list[dict]) -> str | None:
    for r in ranges:
        for ev in r.get("events") or []:
            if isinstance(ev, dict) and "fixed" in ev:
                return str(ev["fixed"])
    return None


def compare_versions(a: str, b: str) -> int:
    va, vb = parse_version(a), parse_version(b)
    if va is None or vb is None:
        return 0
    if va < vb:
        return -1
    if va > vb:
        return 1
    return 0
