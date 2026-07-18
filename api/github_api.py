from __future__ import annotations

import base64
import os
import re
from typing import Any
from urllib.parse import urlencode

import httpx

from core.config import (
    app_base_url,
    github_demo_repo,
    github_oauth_credentials,
    github_token,
)

OAUTH_SCOPES: str = "repo"

_AUTHORIZE = "https://github.com/login/oauth/authorize"
_TOKEN = "https://github.com/login/oauth/access_token"
_API = "https://api.github.com"
_TIMEOUT = httpx.Timeout(30.0)


def _client_id() -> str:
    return github_oauth_credentials()[0]


def _client_secret() -> str:
    return github_oauth_credentials()[1]


# Dynamic aliases (not frozen at import time)
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
        raise ValueError(
            f"GitHub did not return a token: {payload.get('error_description', payload)}"
        )
    return str(token)


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def get_user(token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(f"{_API}/user", headers=_auth_headers(token))
        resp.raise_for_status()
        u = resp.json()
    return {
        "login": u.get("login"),
        "name": u.get("name"),
        "avatar_url": u.get("avatar_url"),
    }


def _bump_manifest(text: str, pkg: str, fix: str) -> str:
    pattern = re.compile(rf'("{re.escape(pkg)}"\s*:\s*")([~^]?)[^"]*(")')

    def repl(m: re.Match[str]) -> str:
        prefix = m.group(2) or ""
        return f"{m.group(1)}{prefix}{fix}{m.group(3)}"

    new_text, n = pattern.subn(repl, text)
    if n == 0:
        raise ValueError(f"{pkg} not found in package.json")
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
*Opened by NotSudo Advisor. Human review required — never auto-merged.*
"""


async def open_fix_pr(
    token: str,
    *,
    repo: str,
    pkg: str,
    current: str,
    fix: str,
    advisory: dict[str, Any],
) -> dict[str, Any]:
    headers = _auth_headers(token)
    advisory_id = str(advisory.get("id", "fix"))
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", advisory_id).strip("-").lower()[:24]
    branch = f"notsudo/fix-{pkg}-{slug}"

    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=headers) as client:
        r = await client.get(f"{_API}/repos/{repo}")
        r.raise_for_status()
        default_branch = r.json().get("default_branch", "main")

        r = await client.get(f"{_API}/repos/{repo}/git/ref/heads/{default_branch}")
        r.raise_for_status()
        base_sha = r.json()["object"]["sha"]

        r = await client.get(
            f"{_API}/repos/{repo}/contents/package.json",
            params={"ref": default_branch},
        )
        r.raise_for_status()
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
        if ref_resp.status_code != 422:
            ref_resp.raise_for_status()

        put = await client.put(
            f"{_API}/repos/{repo}/contents/package.json",
            json={
                "message": f"fix({pkg}): bump {current} -> {fix} for {advisory_id}",
                "content": base64.b64encode(patched.encode("utf-8")).decode("ascii"),
                "branch": branch,
                "sha": file_sha,
            },
        )
        put.raise_for_status()

        pr = await client.post(
            f"{_API}/repos/{repo}/pulls",
            json={
                "title": f"fix({pkg}): bump to {fix} — remediate {advisory_id}",
                "head": branch,
                "base": default_branch,
                "body": _pr_body(advisory, pkg, current, fix),
            },
        )
        if pr.status_code == 422:
            existing = await client.get(
                f"{_API}/repos/{repo}/pulls",
                params={"head": f"{repo.split('/')[0]}:{branch}", "state": "open"},
            )
            existing.raise_for_status()
            items = existing.json()
            if items:
                return {
                    "url": items[0]["html_url"],
                    "number": items[0]["number"],
                    "branch": branch,
                    "reused": True,
                }
        pr.raise_for_status()
        data = pr.json()

    return {
        "url": data["html_url"],
        "number": data["number"],
        "branch": branch,
        "reused": False,
    }


def resolve_write_token(session_token: str | None = None) -> str | None:
    """Prefer OAuth session token; fall back to GITHUB_TOKEN PAT."""
    if session_token:
        return session_token
    return github_token()
