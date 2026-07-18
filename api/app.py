from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from api import github_api

load_dotenv()

app = FastAPI(title="NotSudo Advisor")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", secrets.token_hex(32)),
    same_site="lax",
    https_only=False,
)

_FRONTEND = Path(__file__).parent.parent / "frontend"


class ScanRequest(BaseModel, extra="forbid"):
    repo_path: str


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


# ── scanning ─────────────────────────────────────────────────────────────────
@app.post("/api/scan")
async def scan(req: ScanRequest) -> dict[str, Any]:
    from api.scanner import scan_repo
    try:
        return await scan_repo(req.repo_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── GitHub OAuth ─────────────────────────────────────────────────────────────
@app.get("/auth/github/login")
async def github_login(request: Request) -> RedirectResponse:
    if not github_api.is_configured():
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured. Set GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET in .env.")
    state = secrets.token_urlsafe(24)
    request.session["oauth_state"] = state
    return RedirectResponse(url=github_api.authorize_url(state))


@app.get("/auth/github/callback")
async def github_callback(request: Request, code: str = "", state: str = "") -> RedirectResponse:
    expected = request.session.get("oauth_state")
    if not state or state != expected:
        raise HTTPException(status_code=400, detail="OAuth state mismatch")
    request.session.pop("oauth_state", None)
    try:
        token = await github_api.exchange_code(code)
        user = await github_api.get_user(token)
    except (ValueError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail=f"GitHub login failed: {exc}") from exc
    request.session["gh_token"] = token
    request.session["gh_user"] = user
    return RedirectResponse(url="/Dashboard.html")


@app.post("/auth/logout")
async def logout(request: Request) -> dict[str, bool]:
    request.session.clear()
    return {"ok": True}


@app.get("/api/me")
async def me(request: Request) -> JSONResponse:
    user = request.session.get("gh_user")
    return JSONResponse({
        "user": user,
        "configured": github_api.is_configured(),
        "repo": github_api.GITHUB_DEMO_REPO,
    })


# ── PR creation ──────────────────────────────────────────────────────────────
@app.post("/api/pr")
async def create_pr(request: Request, req: PRRequest) -> dict[str, Any]:
    token = request.session.get("gh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Sign in with GitHub first")
    if not req.fix:
        raise HTTPException(status_code=400, detail=f"No fixed version known for {req.pkg}")
    try:
        result = await github_api.open_fix_pr(
            token,
            repo=github_api.GITHUB_DEMO_REPO,
            pkg=req.pkg,
            current=req.current,
            fix=req.fix,
            advisory=req.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — surface GitHub API errors to the demo UI
        raise HTTPException(status_code=502, detail=f"Could not open PR: {exc}") from exc
    return result


@app.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse(url="/Landing.html")


app.mount("/", StaticFiles(directory=_FRONTEND), name="frontend")
