from __future__ import annotations

import re
from typing import Any


_SYMBOL_HINTS = re.compile(
    r"""
    (?:function|method|API|via|through|in)\s+
    [`'"]?
    (?P<sym>[A-Za-z_][\w.]{1,60})
    [`'"]?
    """,
    re.IGNORECASE | re.VERBOSE,
)

_BACKTICK = re.compile(r"`([A-Za-z_][\w.]{1,60})`")
_CODE_SPAN = re.compile(r"(?:^|\s)([A-Za-z_][\w]*\.[A-Za-z_][\w]*)(?:\s|\(|$)")


def extract_vulnerable_symbols(
    package_name: str,
    summary: str,
    details: str,
    osv: dict[str, Any] | None = None,
) -> list[str]:
    """Best-effort symbol extraction from advisory text and OSV metadata."""
    found: list[str] = []
    seen: set[str] = set()

    def add(sym: str) -> None:
        sym = sym.strip().strip("`'\"")
        if not sym or len(sym) < 2:
            return
        # drop noise words
        if sym.lower() in {
            "the",
            "and",
            "with",
            "from",
            "this",
            "that",
            "function",
            "method",
            "versions",
            "prior",
            "when",
            "user",
            "input",
            "http",
            "https",
            package_name.lower(),
            package_name.split("/")[-1].lower(),
        }:
            return
        key = sym.lower()
        if key not in seen:
            seen.add(key)
            found.append(sym)

    # OSV database_specific / affected ecosystem_specific
    if osv:
        for aff in osv.get("affected") or []:
            eco = aff.get("ecosystem_specific") or {}
            for key in ("exports", "functions", "symbols", "affected_functions"):
                val = eco.get(key)
                if isinstance(val, list):
                    for item in val:
                        add(str(item))
                elif isinstance(val, dict):
                    for k in val:
                        add(str(k))
            db = aff.get("database_specific") or {}
            for key in ("cwes",):
                _ = key
            if "functions" in db and isinstance(db["functions"], list):
                for item in db["functions"]:
                    add(str(item))

    text = f"{summary}\n{details}"
    for m in _BACKTICK.finditer(text):
        add(m.group(1))
    for m in _SYMBOL_HINTS.finditer(text):
        add(m.group("sym"))
    for m in _CODE_SPAN.finditer(text):
        add(m.group(1))

    # package-common defaults
    bare = package_name.split("/")[-1]
    if bare.lower() == "lodash" and not found:
        for s in ("merge", "mergeWith", "defaultsDeep", "set", "template", "zipObjectDeep"):
            add(s)
    if bare.lower() in {"minimist", "yargs-parser"} and not found:
        add("setKey")
    if bare.lower() == "express" and not found:
        add("redirect")

    return found[:12]
