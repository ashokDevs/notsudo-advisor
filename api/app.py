from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

# Load .env BEFORE any other local imports that read secrets
import core.config  # noqa: F401
from api import github_api
from core.config import (
    app_base_url,
    get_settings,
    github_auto_merge,
    github_demo_repo,
    is_production,
    session_https_only,
    session_secret,
)
from core.llm.client import get_llm_client, reset_llm_client
from core.observability.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(title="NotSudo Advisor", version="0.4.0")

# Behind Render/Railway/ngrok TLS terminators
try:
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")  # type: ignore[arg-type]
except Exception:
    pass

app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret(),
    same_site="lax",
    https_only=session_https_only(),
    max_age=60 * 60 * 24 * 7,
)

# Allow the public origin (and localhost for mixed dev)
_origins = {
    app_base_url(),
    "http://localhost:8080",
    "http://127.0.0.1:8080",
}
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_FRONTEND = Path(__file__).parent.parent / "frontend"


class ScanRequest(BaseModel, extra="forbid"):
    repo_path: str | None = None
    target: str | None = None


class AnalyzeRequest(BaseModel, extra="forbid"):
    advisory_id: str
    repo_path: str
    package_name: str | None = None


class PRRequest(BaseModel, extra="forbid"):
    id: str
    pkg: str
    current: str
    fix: str
    verdict: str | None = None
    confidence: float | None = None
    reasoning: str | None = None
    quote: str | None = None
    quoteSource: str | None = None
    entrypoints: list[str] | None = None
    evidence_quotes: list[dict[str, Any]] | None = None
    target_repo: str | None = None
    # When true, merge immediately after opening (overrides GITHUB_AUTO_MERGE if set)
    auto_merge: bool | None = None


class LocalFixRequest(BaseModel, extra="forbid"):
    repo_path: str
    pkg: str
    fix: str


@app.on_event("startup")
async def _startup() -> None:
    s = get_settings()
    logger.info(
        "notsudo started",
        public_url=app_base_url(),
        production=is_production(),
        llm_provider=s["llm_provider"],
        llm=s["llm_configured"],
        github_oauth=s["github_oauth"],
        github_pat=s["github_pat"],
        demo_repo=s["github_demo_repo"],
    )
    reset_llm_client()
    client = get_llm_client()
    if client.available:
        logger.info(
            "llm ready",
            model=client.frontier_model,
            base_url=client.base_url or "default-openai",
        )


def _public_base(request: Request) -> str:
    """Prefer configured APP_BASE_URL (origin only); else request host."""
    # Always use origin-normalized config — never .../Dashboard.html
    configured = app_base_url()
    if configured and "localhost" not in configured:
        return configured
    # Fall back to the request the browser actually used (strip path)
    origin = str(request.base_url).rstrip("/")
    try:
        from urllib.parse import urlparse

        p = urlparse(origin)
        if p.scheme and p.netloc:
            return f"{p.scheme}://{p.netloc}"
    except Exception:
        pass
    return origin


@app.post("/api/scan")
async def scan(req: ScanRequest) -> dict[str, Any]:
    from api.scanner import scan_repo

    target = (req.target or req.repo_path or "").strip()
    if not target:
        raise HTTPException(
            status_code=400,
            detail="Provide target: GitHub URL (https://github.com/org/repo) or owner/repo",
        )
    # On cloud hosts, Windows paths don't exist — nudge users
    if len(target) >= 2 and target[1] == ":" and is_production():
        raise HTTPException(
            status_code=400,
            detail=(
                "Local disk paths don't work on the online server. "
                "Paste a public GitHub URL like https://github.com/OWASP/NodeGoat"
            ),
        )
    try:
        result = await scan_repo(target)
        result["llm_enabled"] = get_llm_client().available
        result["llm_provider"] = get_settings()["llm_provider"]
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"OSV request failed: {exc}") from exc


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest) -> dict[str, Any]:
    from core.analysis.pipeline import analyze_advisory_against_repo

    try:
        return await analyze_advisory_against_repo(
            req.advisory_id,
            req.repo_path,
            package_name=req.package_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"OSV request failed: {exc}") from exc


@app.post("/api/fix-local")
async def fix_local(req: LocalFixRequest) -> dict[str, Any]:
    if is_production():
        raise HTTPException(
            status_code=400,
            detail="Local file fixes are disabled online. Use Open fix PR (GitHub) instead.",
        )
    from api.local_fix import apply_local_bump

    try:
        return apply_local_bump(req.repo_path, req.pkg, req.fix)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _safe_next(raw: str | None) -> str:
    """Only allow same-site relative redirects after OAuth."""
    if not raw:
        return "/Dashboard.html"
    path = raw.strip()
    if not path.startswith("/") or path.startswith("//"):
        return "/Dashboard.html"
    # block weird schemes
    if ":" in path.split("?", 1)[0]:
        return "/Dashboard.html"
    return path


def _oauth_error_redirect(message: str, next_path: str = "/Dashboard.html") -> RedirectResponse:
    from urllib.parse import quote

    dest = _safe_next(next_path)
    sep = "&" if "?" in dest else "?"
    return RedirectResponse(url=f"{dest}{sep}oauth_error={quote(message[:300])}")


@app.get("/auth/github/login")
async def github_login(request: Request, next: str = "/Dashboard.html") -> RedirectResponse:
    next_path = _safe_next(next)
    if not github_api.is_configured():
        return _oauth_error_redirect(
            "OAuth not configured. Set GITHUB_CLIENT_ID + GITHUB_CLIENT_SECRET on Render, "
            "or use GITHUB_TOKEN for PRs without Sign in.",
            next_path,
        )
    state = secrets.token_urlsafe(24)
    request.session["oauth_state"] = state
    request.session["oauth_next"] = next_path
    base = _public_base(request)
    logger.info("oauth login start", base=base, callback=f"{base}/auth/github/callback", next=next_path)
    return RedirectResponse(url=github_api.authorize_url(state, base_url=base))


@app.get("/auth/github/callback")
async def github_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    error_description: str = "",
) -> RedirectResponse:
    next_path = _safe_next(request.session.get("oauth_next"))
    if error:
        return _oauth_error_redirect(error_description or error, next_path)
    expected = request.session.get("oauth_state")
    if not state or not expected or state != expected:
        return _oauth_error_redirect(
            "OAuth state mismatch (session cookie lost). "
            "Set APP_BASE_URL=https://notsudo-advisor.onrender.com, "
            "OAuth callback=https://notsudo-advisor.onrender.com/auth/github/callback, "
            "then try Sign in again in the same browser.",
            next_path,
        )
    request.session.pop("oauth_state", None)
    request.session.pop("oauth_next", None)
    base = _public_base(request)
    try:
        token = await github_api.exchange_code(code, base_url=base)
        user = await github_api.get_user(token)
    except (ValueError, httpx.HTTPError) as exc:
        logger.error("oauth callback failed", error=str(exc))
        return _oauth_error_redirect(f"GitHub login failed: {exc}", next_path)
    request.session["gh_token"] = token
    request.session["gh_user"] = user
    sep = "&" if "?" in next_path else "?"
    return RedirectResponse(url=f"{next_path}{sep}oauth=ok")


@app.post("/auth/logout")
@app.post("/api/logout")
async def logout(request: Request) -> dict[str, bool]:
    request.session.clear()
    return {"ok": True}


@app.get("/api/me")
async def me(request: Request) -> JSONResponse:
    s = get_settings()
    user = request.session.get("gh_user")
    return JSONResponse(
        {
            "user": user,
            "configured": github_api.is_configured(),
            "oauth_client_id_set": s["github_client_id_set"],
            "oauth_secret_set": s["github_client_secret_set"],
            "repo": s["github_demo_repo"],
            "pat_configured": s["github_pat"],
            "llm_configured": s["llm_configured"],
            "llm_provider": s["llm_provider"],
            "llm_model": s["llm_model"],
            "can_open_pr": bool(user) or bool(s["github_pat"]),
            "public_url": app_base_url(),
            "online": is_production(),
            "oauth_callback": f"{app_base_url()}/auth/github/callback",
            "auto_merge": bool(s.get("github_auto_merge")),
            "merge_method": s.get("github_merge_method") or "squash",
        }
    )


@app.get("/api/github/status")
async def github_status(request: Request) -> dict[str, Any]:
    """Diagnose whether the PAT/OAuth token can open PRs on GITHUB_DEMO_REPO."""
    token = github_api.resolve_write_token(request.session.get("gh_token"))
    if not token:
        return {
            "ok": False,
            "error": "No token — set GITHUB_TOKEN on Render or Sign in with GitHub",
            "repo": github_demo_repo(),
        }
    return await github_api.verify_write_access(token)


@app.post("/api/pr")
async def create_pr(request: Request, req: PRRequest) -> dict[str, Any]:
    token = github_api.resolve_write_token(request.session.get("gh_token"))
    if not token:
        raise HTTPException(
            status_code=401,
            detail=(
                "No GitHub credentials for writing PRs. Set GITHUB_TOKEN on Render "
                "(fine-grained: Contents + Pull requests write on the demo repo), "
                "or Sign in with GitHub."
            ),
        )
    if not req.fix:
        raise HTTPException(status_code=400, detail=f"No fixed version known for {req.pkg}")
    target = req.target_repo or github_demo_repo()
    # Request can force merge; otherwise use GITHUB_AUTO_MERGE env
    do_merge = github_auto_merge() if req.auto_merge is None else req.auto_merge
    try:
        result = await github_api.open_fix_pr(
            str(token),
            repo=target,
            pkg=req.pkg,
            current=req.current,
            fix=req.fix,
            advisory=req.model_dump(),
            auto_merge=do_merge,
        )
    except ValueError as exc:
        # Permission / validation errors — surface as 400 with clear text
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Could not open PR: {exc}") from exc
    return result


@app.get("/api/health")
async def health() -> dict[str, Any]:
    s = get_settings()
    raw_warnings = s.get("warnings") or []
    warnings: list[str] = (
        list(raw_warnings) if isinstance(raw_warnings, list) else []
    )
    return {
        "ok": True,
        "dynamic": True,
        "online": is_production(),
        "public_url": app_base_url(),
        "llm": s["llm_configured"],
        "llm_provider": s["llm_provider"],
        "llm_model": s["llm_model"],
        # Never expose raw secrets — base URL only if it is a real http(s) URL
        "llm_base_url": s["llm_base_url"],
        "github_oauth": s["github_oauth"],
        "github_oauth_partial": bool(
            s["github_client_id_set"] and not s["github_client_secret_set"]
        ),
        "github_pat": s["github_pat"],
        "demo_repo": s["github_demo_repo"],
        "auto_merge": bool(s.get("github_auto_merge")),
        "merge_method": s.get("github_merge_method") or "squash",
        "env_loaded": bool(s["env_file"]),
        "warnings": warnings,
        "config_ok": len(warnings) == 0,
    }


@app.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse(url="/Dashboard.html")


app.mount("/", StaticFiles(directory=_FRONTEND), name="frontend")
