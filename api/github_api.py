from __future__ import annotations

import base64
import json
import os
import re
from typing import Any

import httpx

# ── OAuth / config (from environment) ────────────────────────────────────────
GITHUB_CLIENT_ID: str      = os.environ.get("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET: str  = os.environ.get("GITHUB_CLIENT_SECRET", "")
GITHUB_DEMO_REPO: str      = os.environ.get("GITHUB_DEMO_REPO", "ashokDevs/notsudo-demo-app")
APP_BASE_URL: str          = os.environ.get("APP_BASE_URL", "http://localhost:8080")
OAUTH_SCOPES: str          = "repo"

_AUTHORIZE = "https://github.com/login/oauth/authorize"
_TOKEN     = "https://github.com/login/oauth/access_token"
_API       = "https://api.github.com"

_TIMEOUT = httpx.Timeout(20.0)


def is_configured() -> bool:
    return bool(GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET)


def authorize_url(state: str) -> str:
    from urllib.parse import urlencode
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": f"{APP_BASE_URL}/auth/github/callback",
        "scope": OAUTH_SCOPES,
        "state": state,
    }
    return f"{_AUTHORIZE}?{urlencode(params)}"


async def exchange_code(code: str) -> str:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            _TOKEN,
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": f"{APP_BASE_URL}/auth/github/callback",
            },
        )
        resp.raise_for_status()
        payload = resp.json()
    token = payload.get("access_token")
    if not token:
        raise ValueError(f"GitHub did not return a token: {payload.get('error_description', payload)}")
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
    return {"login": u.get("login"), "name": u.get("name"), "avatar_url": u.get("avatar_url")}


# ── manifest patching ────────────────────────────────────────────────────────
def _bump_manifest(text: str, pkg: str, fix: str) -> str:
    """Replace the pinned version for `pkg`, preserving any ^/~ range prefix."""
    pattern = re.compile(rf'("{re.escape(pkg)}"\s*:\s*")([~^]?)[^"]*(")')
    def repl(m: re.Match[str]) -> str:
        prefix = m.group(2) or ""
        return f"{m.group(1)}{prefix}{fix}{m.group(3)}"
    new_text, n = pattern.subn(repl, text)
    if n == 0:
        raise ValueError(f"{pkg} not found in package.json")
    return new_text


# ── PR creation ──────────────────────────────────────────────────────────────
def _pr_body(advisory: dict[str, Any], pkg: str, current: str, fix: str) -> str:
    quote = advisory.get("quote", "")
    source = advisory.get("quoteSource", advisory.get("id", ""))
    reasoning = advisory.get("reasoning", "")
    conf = advisory.get("confidence")
    conf_str = f"{round(float(conf) * 100)}%" if conf is not None else "n/a"
    entrypoints = advisory.get("entrypoints", []) or []
    ep_lines = "\n".join(f"- `{e}`" for e in entrypoints) or "- (none recorded)"
    return f"""## 🛡️ NotSudo Advisor — reachability-confirmed fix

Bumps **{pkg}** `{current}` → `{fix}` to remediate **{advisory.get('id', '')}**.

**Verdict:** `{advisory.get('verdict', 'exposed')}` · confidence **{conf_str}**

### Why this is actually exposed
{reasoning}

### Reachable entry points
{ep_lines}

### Cited evidence
> {quote}

_Source: {source} · citation validated against the source before this PR was drafted._

---
*Opened automatically by NotSudo Advisor. Reasoning over real call sites, so a fix means the code was actually exposed.*
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
        # 1. default branch + head sha
        r = await client.get(f"{_API}/repos/{repo}")
        r.raise_for_status()
        default_branch = r.json().get("default_branch", "main")

        r = await client.get(f"{_API}/repos/{repo}/git/ref/heads/{default_branch}")
        r.raise_for_status()
        base_sha = r.json()["object"]["sha"]

        # 2. current package.json
        r = await client.get(f"{_API}/repos/{repo}/contents/package.json", params={"ref": default_branch})
        r.raise_for_status()
        file_json = r.json()
        file_sha = file_json["sha"]
        original = base64.b64decode(file_json["content"]).decode("utf-8")

        # 3. patch manifest
        patched = _bump_manifest(original, pkg, fix)
        if patched == original:
            raise ValueError(f"{pkg} is already at {fix}")

        # 4. create the fix branch (idempotent-ish: reuse if it exists)
        ref_resp = await client.post(
            f"{_API}/repos/{repo}/git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": base_sha},
        )
        if ref_resp.status_code == 422:
            # branch already exists — point PUT at it as-is
            pass
        else:
            ref_resp.raise_for_status()

        # 5. commit the bump on the branch
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

        # 6. open the PR
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
            # a PR for this branch may already be open — surface it instead of failing
            existing = await client.get(
                f"{_API}/repos/{repo}/pulls",
                params={"head": f"{repo.split('/')[0]}:{branch}", "state": "open"},
            )
            existing.raise_for_status()
            items = existing.json()
            if items:
                return {"url": items[0]["html_url"], "number": items[0]["number"], "branch": branch, "reused": True}
        pr.raise_for_status()
        data = pr.json()

    return {"url": data["html_url"], "number": data["number"], "branch": branch, "reused": False}
