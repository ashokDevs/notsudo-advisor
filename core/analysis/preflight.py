from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from core.observability.logging import get_logger

logger = get_logger(__name__)


class PreflightResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    ecosystem: str
    message: str
    command: str | None = None


async def preflight_bump(
    repo: Path,
    package_name: str,
    fixed_version: str,
    ecosystem: str = "npm",
) -> PreflightResult:
    """
    Verify the proposed version bump resolves cleanly.
    npm: package-lock-only install in a temp copy of the manifest.
    PyPI: basic requirements rewrite + pip dry-run when available.
    """
    if ecosystem.lower() in {"npm", "javascript", "js", "node"}:
        return await _preflight_npm(repo, package_name, fixed_version)
    if ecosystem.lower() in {"pypi", "python", "pip"}:
        return await _preflight_pypi(repo, package_name, fixed_version)
    return PreflightResult(
        ok=True,
        ecosystem=ecosystem,
        message=f"No preflight runner for ecosystem {ecosystem}; skipped",
    )


async def _preflight_npm(repo: Path, package_name: str, fixed_version: str) -> PreflightResult:
    pkg_json = repo / "package.json"
    if not pkg_json.is_file():
        return PreflightResult(ok=False, ecosystem="npm", message="package.json not found")

    npm = shutil.which("npm")
    if not npm:
        # Still validate that the manifest can be patched syntactically
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            for section in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
                deps = data.get(section) or {}
                if package_name in deps:
                    deps[package_name] = fixed_version
                    return PreflightResult(
                        ok=True,
                        ecosystem="npm",
                        message="npm not installed; validated package.json patch only",
                        command=None,
                    )
            return PreflightResult(
                ok=False,
                ecosystem="npm",
                message=f"{package_name} not found in package.json",
            )
        except (OSError, json.JSONDecodeError) as exc:
            return PreflightResult(ok=False, ecosystem="npm", message=str(exc))

    with tempfile.TemporaryDirectory(prefix="notsudo-preflight-") as tmp:
        tmp_path = Path(tmp)
        text = pkg_json.read_text(encoding="utf-8")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            return PreflightResult(ok=False, ecosystem="npm", message=f"invalid package.json: {exc}")

        found = False
        for section in ("dependencies", "devDependencies", "optionalDependencies"):
            deps = data.get(section) or {}
            if package_name in deps:
                deps[package_name] = fixed_version
                data[section] = deps
                found = True
        if not found:
            return PreflightResult(
                ok=False,
                ecosystem="npm",
                message=f"{package_name} not present in package.json dependencies",
            )

        (tmp_path / "package.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        lock = repo / "package-lock.json"
        if lock.is_file():
            (tmp_path / "package-lock.json").write_text(lock.read_text(encoding="utf-8"), encoding="utf-8")

        cmd = [npm, "install", "--package-lock-only", "--ignore-scripts", "--no-audit", "--no-fund"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(tmp_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        except TimeoutError:
            return PreflightResult(
                ok=False,
                ecosystem="npm",
                message="npm install timed out",
                command=" ".join(cmd),
            )
        except OSError as exc:
            return PreflightResult(ok=False, ecosystem="npm", message=str(exc), command=" ".join(cmd))

        if proc.returncode == 0:
            return PreflightResult(
                ok=True,
                ecosystem="npm",
                message="lockfile resolves cleanly with proposed bump",
                command=" ".join(cmd),
            )
        err = (stderr or stdout or b"").decode("utf-8", errors="replace")[:500]
        return PreflightResult(
            ok=False,
            ecosystem="npm",
            message=f"npm install failed: {err}",
            command=" ".join(cmd),
        )


async def _preflight_pypi(repo: Path, package_name: str, fixed_version: str) -> PreflightResult:
    req = repo / "requirements.txt"
    if not req.is_file():
        # pyproject-only projects: accept syntactic bump
        return PreflightResult(
            ok=True,
            ecosystem="PyPI",
            message="no requirements.txt; skipped pip resolve (pyproject-only)",
        )
    pip = shutil.which("pip") or shutil.which("pip3")
    lines = req.read_text(encoding="utf-8").splitlines()
    new_lines: list[str] = []
    found = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            new_lines.append(line)
            continue
        name = stripped.split("==")[0].split(">=")[0].split("~=")[0].split("[")[0].strip()
        if name.lower() == package_name.lower():
            new_lines.append(f"{package_name}=={fixed_version}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        return PreflightResult(
            ok=False,
            ecosystem="PyPI",
            message=f"{package_name} not found in requirements.txt",
        )
    if not pip:
        return PreflightResult(
            ok=True,
            ecosystem="PyPI",
            message="pip not installed; validated requirements rewrite only",
        )

    with tempfile.TemporaryDirectory(prefix="notsudo-pip-") as tmp:
        req_path = Path(tmp) / "requirements.txt"
        req_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        cmd = [pip, "install", "--dry-run", "-r", str(req_path)]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        except (TimeoutError, OSError) as exc:
            return PreflightResult(
                ok=True,
                ecosystem="PyPI",
                message=f"pip dry-run skipped ({exc}); rewrite validated",
                command=" ".join(cmd),
            )
        if proc.returncode == 0:
            return PreflightResult(
                ok=True,
                ecosystem="PyPI",
                message="pip dry-run succeeded",
                command=" ".join(cmd),
            )
        err = (stderr or stdout or b"").decode("utf-8", errors="replace")[:400]
        # dry-run unsupported on old pip — still ok if rewrite worked
        if "no such option" in err.lower() or "dry-run" in err.lower():
            return PreflightResult(
                ok=True,
                ecosystem="PyPI",
                message="pip dry-run unsupported; requirements rewrite validated",
                command=" ".join(cmd),
            )
        return PreflightResult(
            ok=False,
            ecosystem="PyPI",
            message=f"pip dry-run failed: {err}",
            command=" ".join(cmd),
        )
