from __future__ import annotations

import asyncio
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from core.observability.logging import get_logger

logger = get_logger(__name__)

# github.com/owner/repo or github.com/owner/repo.git (+ optional .git suffix / trailing slash)
_GH_HTTPS = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)
_GH_SSH = re.compile(
    r"^git@github\.com:(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?$",
    re.IGNORECASE,
)
_GH_SHORT = re.compile(
    r"^(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)$",
)


@dataclass(frozen=True)
class ResolvedTarget:
    """Where to scan: local path and optional GitHub metadata."""

    path: Path
    display_name: str
    source: str  # local | github
    github_url: str | None = None
    owner: str | None = None
    repo: str | None = None
    cleanup_dir: Path | None = None  # temp clone root to delete later


def parse_github_ref(raw: str) -> tuple[str, str] | None:
    """Return (owner, repo) if `raw` looks like a GitHub reference."""
    text = raw.strip().rstrip("/")
    if text.endswith(".git"):
        text = text[:-4]
    for pat in (_GH_HTTPS, _GH_SSH, _GH_SHORT):
        m = pat.match(text)
        if m:
            return m.group("owner"), m.group("repo")
    # also accept full URL with path extras stripped
    if "github.com" in text:
        try:
            p = urlparse(text if "://" in text else f"https://{text}")
            parts = [x for x in p.path.split("/") if x]
            if len(parts) >= 2:
                return parts[0], parts[1].removesuffix(".git")
        except ValueError:
            return None
    return None


def is_github_target(raw: str) -> bool:
    return parse_github_ref(raw) is not None


def looks_like_url(raw: str) -> bool:
    t = raw.strip().lower()
    return t.startswith("http://") or t.startswith("https://") or t.startswith("git@") or "github.com" in t


async def clone_github_repo(
    owner: str,
    repo: str,
    *,
    depth: int = 1,
    branch: str | None = None,
    timeout_s: float = 180.0,
) -> ResolvedTarget:
    """Shallow-clone a public GitHub repo into a temp directory."""
    git = shutil.which("git")
    if not git:
        raise ValueError("git is not installed on this machine — cannot clone GitHub URLs")

    url = f"https://github.com/{owner}/{repo}.git"
    tmp = Path(tempfile.mkdtemp(prefix="notsudo-scan-"))
    dest = tmp / repo

    cmd = [git, "clone", f"--depth={depth}", "--single-branch"]
    if branch:
        cmd.extend(["--branch", branch])
    cmd.extend([url, str(dest)])

    logger.info("cloning github repo", owner=owner, repo=repo, dest=str(dest))
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except TimeoutError as exc:
        shutil.rmtree(tmp, ignore_errors=True)
        raise ValueError(f"git clone timed out after {timeout_s}s for {owner}/{repo}") from exc
    except OSError as exc:
        shutil.rmtree(tmp, ignore_errors=True)
        raise ValueError(f"git clone failed: {exc}") from exc

    if proc.returncode != 0:
        err = (stderr or b"").decode("utf-8", errors="replace")[:400]
        shutil.rmtree(tmp, ignore_errors=True)
        raise ValueError(f"git clone failed for {owner}/{repo}: {err}")

    return ResolvedTarget(
        path=dest,
        display_name=f"{owner}/{repo}",
        source="github",
        github_url=f"https://github.com/{owner}/{repo}",
        owner=owner,
        repo=repo,
        cleanup_dir=tmp,
    )


async def resolve_scan_target(raw: str) -> ResolvedTarget:
    """
    Accept a local filesystem path OR a GitHub URL / owner/repo.
    Returns a ResolvedTarget; caller should cleanup cleanup_dir when done.
    """
    text = raw.strip().strip('"').strip("'")
    if not text:
        raise ValueError("Empty scan target")

    gh = parse_github_ref(text)
    # Prefer GitHub parse only when it looks like a URL/short ref, not a Windows path
    # Windows paths like D:\foo\owner\repo should stay local.
    is_win_path = len(text) >= 2 and text[1] == ":"
    is_unix_abs = text.startswith("/") or text.startswith("~")
    is_rel_path = (not looks_like_url(text)) and (
        "\\" in text or text.startswith(".") or Path(text).exists()
    )

    if gh and not is_win_path and not is_unix_abs and (looks_like_url(text) or not is_rel_path):
        # owner/repo short form only if path doesn't exist locally
        owner, repo = gh
        local_guess = Path(text)
        if local_guess.exists() and local_guess.is_dir():
            return ResolvedTarget(
                path=local_guess.resolve(),
                display_name=local_guess.name,
                source="local",
            )
        if "/" in text and not looks_like_url(text) and Path(text).exists():
            return ResolvedTarget(
                path=Path(text).resolve(),
                display_name=Path(text).name,
                source="local",
            )
        return await clone_github_repo(owner, repo)

    path = Path(text).expanduser()
    if not path.exists():
        # last chance: treat as github short ref
        if gh:
            return await clone_github_repo(gh[0], gh[1])
        raise ValueError(f"Not a directory and not a GitHub URL: {raw}")
    if not path.is_dir():
        raise ValueError(f"Not a directory: {raw}")
    return ResolvedTarget(
        path=path.resolve(),
        display_name=path.name,
        source="local",
    )


def cleanup_target(target: ResolvedTarget) -> None:
    if target.cleanup_dir and target.cleanup_dir.exists():
        shutil.rmtree(target.cleanup_dir, ignore_errors=True)
        logger.info("cleaned temp clone", path=str(target.cleanup_dir))
