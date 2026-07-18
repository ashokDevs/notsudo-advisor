from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def apply_local_bump(repo_path: str, pkg: str, fix: str) -> dict[str, Any]:
    """Apply a dependency version bump on a local checkout."""
    repo = Path(repo_path).expanduser().resolve()
    if not repo.is_dir():
        raise ValueError(f"Not a directory: {repo_path}")

    pkg_json = repo / "package.json"
    if pkg_json.is_file():
        return _bump_package_json(pkg_json, pkg, fix)

    req = repo / "requirements.txt"
    if req.is_file():
        return _bump_requirements(req, pkg, fix)

    raise ValueError("No package.json or requirements.txt found")


def _bump_package_json(path: Path, pkg: str, fix: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(rf'("{re.escape(pkg)}"\s*:\s*")([~^]?)[^"]*(")')
    new_text, n = pattern.subn(lambda m: f"{m.group(1)}{m.group(2) or ''}{fix}{m.group(3)}", text)
    if n == 0:
        raise ValueError(f"{pkg} not found in package.json")
    path.write_text(new_text, encoding="utf-8")
    return {"ok": True, "file": str(path), "pkg": pkg, "fix": fix, "replacements": n}


def _bump_requirements(path: Path, pkg: str, fix: str) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    found = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            out.append(line)
            continue
        name = re.split(r"[>=<!~\[]", stripped, maxsplit=1)[0].strip()
        if name.lower() == pkg.lower():
            out.append(f"{pkg}=={fix}")
            found = True
        else:
            out.append(line)
    if not found:
        raise ValueError(f"{pkg} not found in requirements.txt")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return {"ok": True, "file": str(path), "pkg": pkg, "fix": fix, "replacements": 1}
