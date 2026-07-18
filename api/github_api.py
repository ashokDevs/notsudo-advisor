from __future__ import annotations

import base64
import re
from typing import Any
from urllib.parse import urlencode

import httpx

from core.config import (
    app_base_url,
    github_auto_merge,
    github_demo_repo,
    github_merge_method,
    github_oauth_credentials,
    github_token,
)
from core.observability.logging import get_logger

logger = get_logger(__name__)

OAUTH_SCOPES: str = "repo"

_AUTHORIZE = "https://github.com/login/oauth/authorize"
_TOKEN = "https://github.com/login/oauth/access_token"
_API = "https://api.github.com"
_TIMEOUT = httpx.Timeout(30.0)


def _client_id() -> str:
    return github_oauth_credentials()[0]


def _client_secret() -> str:
    return github_oauth_credentials()[1]


def __getattr__(name: str) -> Any:
    if name == "GITHUB_CLIENT_ID":
        return _client_id()
    if name == "GITHUB_CLIENT_SECRET":
        return _client_secret()
    if name == "GITHUB_DEMO_REPO":
        return github_demo_repo()
    if name == "APP_BASE_URL":
        return app_base_url()
    raise AttributeError(name)


def is_configured() -> bool:
    cid, secret = github_oauth_credentials()
    return bool(cid and secret)


def authorize_url(state: str, base_url: str | None = None) -> str:
    cid, _ = github_oauth_credentials()
    origin = (base_url or app_base_url()).rstrip("/")
    params = {
        "client_id": cid,
        "redirect_uri": f"{origin}/auth/github/callback",
        "scope": OAUTH_SCOPES,
        "state": state,
    }
    return f"{_AUTHORIZE}?{urlencode(params)}"


async def exchange_code(code: str, base_url: str | None = None) -> str:
    cid, secret = github_oauth_credentials()
    if not cid or not secret:
        raise ValueError(
            "GitHub OAuth incomplete: set both GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET"
        )
    origin = (base_url or app_base_url()).rstrip("/")
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            _TOKEN,
            headers={"Accept": "application/json"},
            data={
                "client_id": cid,
                "client_secret": secret,
                "code": code,
                "redirect_uri": f"{origin}/auth/github/callback",
            },
        )
        resp.raise_for_status()
        payload = resp.json()
    token = payload.get("access_token")
    if not token:
        err = payload.get("error_description") or payload.get("error") or payload
        raise ValueError(f"GitHub did not return a token: {err}")
    return str(token)


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "NotSudo-Advisor",
    }


def _http_error_detail(resp: httpx.Response, action: str) -> str:
    """Turn GitHub HTTP errors into actionable messages."""
    body: dict[str, Any] = {}
    try:
        parsed = resp.json()
        if isinstance(parsed, dict):
            body = parsed
    except Exception:
        body = {}
    msg = str(body.get("message") or resp.text or resp.reason_phrase)[:300]
    if resp.status_code == 401:
        return (
            f"{action}: GitHub 401 Unauthorized — token invalid/expired. "
            f"Create a new fine-grained PAT or re-do OAuth sign-in. ({msg})"
        )
    if resp.status_code == 403:
        return (
            f"{action}: GitHub 403 Forbidden — token cannot write to this repo. "
            f"For fine-grained PATs grant on {github_demo_repo()}: "
            f"Contents=Read and write, Pull requests=Read and write. "
            f"Classic PATs need the `repo` scope. ({msg})"
        )
    if resp.status_code == 404:
        return (
            f"{action}: GitHub 404 — repo or file not found (or token cannot see it). "
            f"Check GITHUB_DEMO_REPO={github_demo_repo()} exists and has package.json. ({msg})"
        )
    return f"{action}: GitHub HTTP {resp.status_code}: {msg}"


async def get_user(token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(f"{_API}/user", headers=_auth_headers(token))
        if resp.status_code >= 400:
            raise ValueError(_http_error_detail(resp, "get user"))
        u = resp.json()
    return {
        "login": u.get("login"),
        "name": u.get("name"),
        "avatar_url": u.get("avatar_url"),
    }


async def verify_write_access(token: str, repo: str | None = None) -> dict[str, Any]:
    """Check whether the token can read the target repo and likely open PRs."""
    target = repo or github_demo_repo()
    out: dict[str, Any] = {
        "repo": target,
        "ok": False,
        "login": None,
        "can_read": False,
        "can_push": False,
        "has_package_json": False,
        "default_branch": None,
        "error": None,
    }
    headers = _auth_headers(token)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=headers) as client:
            u = await client.get(f"{_API}/user")
            if u.status_code >= 400:
                out["error"] = _http_error_detail(u, "verify token")
                return out
            out["login"] = u.json().get("login")

            r = await client.get(f"{_API}/repos/{target}")
            if r.status_code >= 400:
                out["error"] = _http_error_detail(r, f"read repo {target}")
                return out
            data = r.json()
            out["can_read"] = True
            out["default_branch"] = data.get("default_branch")
            perms = data.get("permissions") or {}
            out["can_push"] = bool(perms.get("push") or perms.get("admin"))
            out["permissions"] = perms

            pkg = await client.get(
                f"{_API}/repos/{target}/contents/package.json",
                params={"ref": out["default_branch"] or "main"},
            )
            out["has_package_json"] = pkg.status_code == 200
            if pkg.status_code == 404:
                out["error"] = (
                    f"{target} has no package.json on the default branch — "
                    "PRs need a package.json to bump versions."
                )
                return out
            if pkg.status_code >= 400:
                out["error"] = _http_error_detail(pkg, "read package.json")
                return out

            if not out["can_push"]:
                out["error"] = (
                    f"Token user @{out['login']} cannot push to {target}. "
                    "Fine-grained PAT: Contents + Pull requests = Read and write on this repo. "
                    "Or use a classic PAT with `repo` scope."
                )
                return out
            out["ok"] = True
    except httpx.HTTPError as exc:
        out["error"] = f"network error talking to GitHub: {exc}"
    return out


def _bump_manifest(text: str, pkg: str, fix: str) -> str:
    pattern = re.compile(rf'("{re.escape(pkg)}"\s*:\s*")([~^]?)[^"]*(")')

    def repl(m: re.Match[str]) -> str:
        prefix = m.group(2) or ""
        return f"{m.group(1)}{prefix}{fix}{m.group(3)}"

    new_text, n = pattern.subn(repl, text)
    if n == 0:
        raise ValueError(
            f"{pkg} not found in package.json of the PR target repo. "
            f"Scan a GitHub URL that actually contains `{pkg}`, or set GITHUB_DEMO_REPO "
            f"to a repo whose package.json includes that dependency."
        )
    return new_text


def _pr_body(advisory: dict[str, Any], pkg: str, current: str, fix: str) -> str:
    quote = advisory.get("quote", "")
    source = advisory.get("quoteSource", advisory.get("id", ""))
    reasoning = advisory.get("reasoning", "")
    conf = advisory.get("confidence")
    conf_str = f"{round(float(conf) * 100)}%" if conf is not None else "n/a"
    entrypoints = advisory.get("entrypoints", []) or []
    ep_lines = "\n".join(f"- `{e}`" for e in entrypoints) or "- (none recorded)"
    eq = advisory.get("evidence_quotes") or []
    eq_lines = []
    for item in eq[:5]:
        if isinstance(item, dict):
            eq_lines.append(
                f"- `{item.get('file_path')}:{item.get('line_start')}` — "
                f"`{str(item.get('quote', ''))[:160]}`"
            )
    if not eq_lines and quote:
        eq_lines.append(f"> {quote}\n\n_Source: {source}_")
    evidence_block = "\n".join(eq_lines) if eq_lines else "_no code quotes_"
    return f"""## NotSudo Advisor — reachability-confirmed fix

**TL;DR:** Bump **{pkg}** `{current}` → `{fix}` for **{advisory.get('id', '')}**.

| Field | Value |
|------|--------|
| Verdict | `{advisory.get('verdict', 'exposed')}` |
| Confidence | {conf_str} |

### Why this is actually exposed
{reasoning}

### Reachable entry points
{ep_lines}

### Cited evidence (validated)
{evidence_block}

### Advisory
- https://osv.dev/vulnerability/{advisory.get('id', '')}

---
*Opened by NotSudo Advisor.*
"""


async def _merge_pull_request(
    client: httpx.AsyncClient,
    *,
    repo: str,
    number: int,
    title: str,
    method: str,
) -> dict[str, Any]:
    """Merge an open PR. Returns merge API payload."""
    resp = await client.put(
        f"{_API}/repos/{repo}/pulls/{number}/merge",
        json={
            "commit_title": title[:255],
            "merge_method": method,
        },
    )
    if resp.status_code >= 400:
        raise ValueError(
            _http_error_detail(
                resp,
                "auto-merge PR (needs permission to merge — Contents write + no branch protection blocking)",
            )
        )
    return resp.json() if resp.content else {"merged": True}


async def open_fix_pr(
    token: str,
    *,
    repo: str,
    pkg: str,
    current: str,
    fix: str,
    advisory: dict[str, Any],
    auto_merge: bool | None = None,
    merge_method: str | None = None,
) -> dict[str, Any]:
    """
    Open a version-bump fix PR. When auto_merge is true (or GITHUB_AUTO_MERGE=1),
    merges the PR immediately after creation.
    """
    do_merge = github_auto_merge() if auto_merge is None else auto_merge
    method = merge_method or github_merge_method()

    headers = _auth_headers(token)
    advisory_id = str(advisory.get("id", "fix"))
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", advisory_id).strip("-").lower()[:24]
    # package names can include @scope/
    safe_pkg = re.sub(r"[^a-zA-Z0-9._-]+", "-", pkg).strip("-")[:40]
    branch = f"notsudo/fix-{safe_pkg}-{slug}"[:100]

    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=headers) as client:
        r = await client.get(f"{_API}/repos/{repo}")
        if r.status_code >= 400:
            raise ValueError(_http_error_detail(r, f"open PR on {repo}"))
        default_branch = r.json().get("default_branch", "main")

        r = await client.get(f"{_API}/repos/{repo}/git/ref/heads/{default_branch}")
        if r.status_code >= 400:
            raise ValueError(_http_error_detail(r, f"read branch {default_branch}"))
        base_sha = r.json()["object"]["sha"]

        r = await client.get(
            f"{_API}/repos/{repo}/contents/package.json",
            params={"ref": default_branch},
        )
        if r.status_code >= 400:
            raise ValueError(_http_error_detail(r, "read package.json"))
        file_json = r.json()
        file_sha = file_json["sha"]
        original = base64.b64decode(file_json["content"]).decode("utf-8")

        patched = _bump_manifest(original, pkg, fix)
        if patched == original:
            raise ValueError(f"{pkg} is already at {fix}")

        ref_resp = await client.post(
            f"{_API}/repos/{repo}/git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": base_sha},
        )
        if ref_resp.status_code == 422:
            # branch exists — update ref to latest base then continue
            pass
        elif ref_resp.status_code >= 400:
            raise ValueError(_http_error_detail(ref_resp, "create branch (needs Contents: write)"))

        # If branch already exists, get package.json sha on that branch for update
        branch_pkg = await client.get(
            f"{_API}/repos/{repo}/contents/package.json",
            params={"ref": branch},
        )
        if branch_pkg.status_code == 200:
            file_sha = branch_pkg.json()["sha"]

        put = await client.put(
            f"{_API}/repos/{repo}/contents/package.json",
            json={
                "message": f"fix({pkg}): bump {current} -> {fix} for {advisory_id}",
                "content": base64.b64encode(patched.encode("utf-8")).decode("ascii"),
                "branch": branch,
                "sha": file_sha,
            },
        )
        if put.status_code >= 400:
            raise ValueError(_http_error_detail(put, "commit package.json bump (Contents: write)"))

        pr_title = f"fix({pkg}): bump to {fix} — remediate {advisory_id}"
        pr = await client.post(
            f"{_API}/repos/{repo}/pulls",
            json={
                "title": pr_title,
                "head": branch,
                "base": default_branch,
                "body": _pr_body(advisory, pkg, current, fix),
            },
        )
        reused = False
        if pr.status_code == 422:
            owner = repo.split("/")[0]
            existing = await client.get(
                f"{_API}/repos/{repo}/pulls",
                params={"head": f"{owner}:{branch}", "state": "open"},
            )
            if existing.status_code == 200:
                items = existing.json()
                if items:
                    data = items[0]
                    reused = True
                else:
                    raise ValueError(_http_error_detail(pr, "create pull request"))
            else:
                raise ValueError(_http_error_detail(pr, "create pull request"))
        elif pr.status_code >= 400:
            raise ValueError(_http_error_detail(pr, "create pull request (Pull requests: write)"))
        else:
            data = pr.json()

        number = int(data["number"])
        url = str(data["html_url"])
        result: dict[str, Any] = {
            "url": url,
            "number": number,
            "branch": branch,
            "reused": reused,
            "merged": False,
            "merge_commit_sha": None,
            "auto_merge": do_merge,
            "base_branch": default_branch,
        }

        if do_merge:
            merge_title = f"fix({pkg}): bump {current} -> {fix} ({advisory_id})"
            merge_data = await _merge_pull_request(
                client,
                repo=repo,
                number=number,
                title=merge_title,
                method=method,
            )
            result["merged"] = bool(merge_data.get("merged", True))
            result["merge_commit_sha"] = merge_data.get("sha")
            result["merge_method"] = method
            logger.info(
                "auto-merged fix PR",
                repo=repo,
                number=number,
                method=method,
                sha=result["merge_commit_sha"],
            )

    return result


def resolve_write_token(session_token: str | None = None) -> str | None:
    """Prefer OAuth session token; fall back to GITHUB_TOKEN PAT."""
    if session_token:
        return session_token
    return github_token()
