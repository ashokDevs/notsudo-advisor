from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

# Load .env before any other module reads os.environ for keys.
_ROOT = Path(__file__).resolve().parents[1]
_ENV_FILE = _ROOT / ".env"

try:
    from dotenv import load_dotenv

    # override=False: real process env wins; .env fills gaps
    load_dotenv(_ENV_FILE, override=False)
    load_dotenv(override=False)
except ImportError:
    pass


def _env(name: str, default: str = "") -> str:
    """Read env var and strip whitespace/newlines (Render paste often adds \\n)."""
    return (os.getenv(name, default) or default).strip().strip('"').strip("'")


def _truthy(name: str, default: str = "") -> bool:
    return _env(name, default).lower() in {"1", "true", "yes", "on"}


def _looks_like_secret_key(value: str) -> bool:
    v = value.strip()
    return (
        v.startswith("sk-")
        or v.startswith("sk-or-")
        or v.startswith("ghp_")
        or v.startswith("github_pat_")
        or v.startswith("gho_")
    )


def _looks_like_url(value: str) -> bool:
    v = value.strip().lower()
    return v.startswith("http://") or v.startswith("https://")


def _looks_like_database_url(value: str) -> bool:
    v = value.strip().lower()
    return v.startswith("postgres://") or v.startswith("postgresql://") or v.startswith("mysql://")


def llm_api_key() -> str | None:
    key = _env("OPENAI_API_KEY") or _env("LLM_API_KEY")
    # Common misconfig: key pasted into OPENAI_API_BASE
    base = _env("OPENAI_API_BASE") or _env("OPENAI_BASE_URL") or _env("LLM_BASE_URL")
    if not key and base and _looks_like_secret_key(base):
        key = base
    return key or None


def llm_base_url() -> str | None:
    base = _env("OPENAI_API_BASE") or _env("OPENAI_BASE_URL") or _env("LLM_BASE_URL")
    # Misconfig: API key put in base URL field
    if base and _looks_like_secret_key(base):
        base = ""
    # Misconfig: non-URL garbage
    if base and not _looks_like_url(base):
        base = ""
    base = base.rstrip("/")
    # OpenRouter keys need the OpenRouter base even if user forgot it
    key = llm_api_key() or ""
    if not base and key.startswith("sk-or-"):
        base = "https://openrouter.ai/api/v1"
    return base or None


def llm_models() -> tuple[str, str]:
    frontier = _env("LLM_MODEL") or _env("LLM_FRONTIER_MODEL") or "gpt-4o"
    cheap = _env("LLM_CHEAP_MODEL") or frontier
    return cheap, frontier


def _origin_only(url: str) -> str:
    """Strip path/query so APP_BASE_URL is always scheme://host[:port]."""
    from urllib.parse import urlparse

    raw = url.strip().rstrip("/")
    if not raw:
        return raw
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    if not parsed.scheme or not parsed.netloc:
        return raw
    return f"{parsed.scheme}://{parsed.netloc}"


def app_base_url() -> str:
    """
    Public origin of this deployment.
    Online: APP_BASE_URL=https://notsudo-advisor.onrender.com  (no /Dashboard.html)
    """
    explicit = _env("APP_BASE_URL")
    # Misconfig: DATABASE_URL or secret pasted into APP_BASE_URL
    if explicit and (_looks_like_database_url(explicit) or _looks_like_secret_key(explicit)):
        explicit = ""
    if explicit and _looks_like_url(explicit):
        return _origin_only(explicit)

    render = _env("RENDER_EXTERNAL_URL")
    if render:
        return _origin_only(render)

    railway = _env("RAILWAY_PUBLIC_DOMAIN")
    if railway:
        if railway.startswith("http"):
            return _origin_only(railway)
        return f"https://{railway}"

    service = _env("RENDER_SERVICE_NAME")
    if service:
        return f"https://{service}.onrender.com"

    return "http://localhost:8080"


def is_production() -> bool:
    if _truthy("NOTSUDO_PRODUCTION"):
        return True
    # Render always sets this
    if _env("RENDER") or _env("RENDER_SERVICE_ID") or _env("RENDER_EXTERNAL_URL"):
        return True
    base = app_base_url()
    return base.startswith("https://") and "localhost" not in base


def session_https_only() -> bool:
    if os.getenv("SESSION_HTTPS_ONLY") is not None:
        return _truthy("SESSION_HTTPS_ONLY")
    return is_production()


def session_secret() -> str:
    return _env("SESSION_SECRET") or "notsudo-dev-insecure-change-me"


def github_token() -> str | None:
    tok = _env("GITHUB_TOKEN")
    return tok or None


def github_oauth_credentials() -> tuple[str, str]:
    return (_env("GITHUB_CLIENT_ID"), _env("GITHUB_CLIENT_SECRET"))


def github_demo_repo() -> str:
    return _env("GITHUB_DEMO_REPO") or "ashokDevs/notsudo-demo-app"


def release_version() -> str:
    """Best-effort immutable deployment identifier for operational diagnostics."""
    return _env("RENDER_GIT_COMMIT") or _env("GIT_COMMIT") or "unknown"


def github_auto_merge() -> bool:
    """
    When true, open_fix_pr merges the PR immediately after creation.
    Requires PAT/OAuth with permission to merge (usually Contents write + PR write).
    Env: GITHUB_AUTO_MERGE=1|true|yes
    """
    return _truthy("GITHUB_AUTO_MERGE")


def github_merge_method() -> str:
    """squash | merge | rebase — default squash for clean history."""
    method = _env("GITHUB_MERGE_METHOD", "squash").lower()
    if method not in {"squash", "merge", "rebase"}:
        return "squash"
    return method


def config_warnings() -> list[str]:
    """Human-readable misconfiguration hints (safe to show in /api/health)."""
    warnings: list[str] = []
    raw_base = _env("OPENAI_API_BASE") or _env("OPENAI_BASE_URL") or _env("LLM_BASE_URL")
    if raw_base and _looks_like_secret_key(raw_base):
        warnings.append(
            "OPENAI_API_BASE looks like an API key — set it to https://openrouter.ai/api/v1 "
            "and put the key in OPENAI_API_KEY only"
        )
    raw_app = _env("APP_BASE_URL")
    if raw_app and _looks_like_database_url(raw_app):
        warnings.append(
            "APP_BASE_URL is a database URL — set APP_BASE_URL=https://notsudo-advisor.onrender.com"
        )
    if not llm_api_key():
        warnings.append("OPENAI_API_KEY missing — scans use heuristics only")
    if not github_token() and not (_env("GITHUB_CLIENT_ID") and _env("GITHUB_CLIENT_SECRET")):
        warnings.append("No GITHUB_TOKEN / OAuth — cannot open fix PRs")
    if github_auto_merge():
        warnings.append("GITHUB_AUTO_MERGE is ignored; NotSudo requires human PR review")
    return warnings


@lru_cache(maxsize=1)
def get_settings() -> dict[str, str | bool | None | list[str]]:
    """Snapshot of runtime config — never include secret values."""
    api_key = llm_api_key() or ""
    base = llm_base_url()
    model = llm_models()[1]
    cheap = llm_models()[0]
    provider = _env("LLM_PROVIDER").lower()
    if not provider:
        if (base and "openrouter" in base) or api_key.startswith("sk-or-"):
            provider = "openrouter"
        elif base and ("localhost" in base or "127.0.0.1" in base):
            provider = "local"
        elif base:
            provider = "openai_compatible"
        elif api_key:
            provider = "openai"
        else:
            provider = "none"

    return {
        "llm_provider": provider,
        "llm_configured": bool(api_key),
        # Redacted for public /api/health — never return secrets or full keys
        "llm_base_url": base if base and not _looks_like_secret_key(base) else None,
        "llm_model": model,
        "llm_cheap_model": cheap,
        "github_oauth": bool(_env("GITHUB_CLIENT_ID") and _env("GITHUB_CLIENT_SECRET")),
        "github_client_id_set": bool(_env("GITHUB_CLIENT_ID")),
        "github_client_secret_set": bool(_env("GITHUB_CLIENT_SECRET")),
        "github_pat": bool(github_token()),
        "github_demo_repo": github_demo_repo(),
        "release_version": release_version(),
        "github_auto_merge": github_auto_merge(),
        "github_merge_method": github_merge_method(),
        "app_base_url": app_base_url(),
        "online": is_production(),
        "database_url_set": bool(_env("DATABASE_URL")),
        "hash_embeddings": _truthy("NOTSUDO_HASH_EMBEDDINGS", "1"),
        "env_file": str(_ENV_FILE) if _ENV_FILE.is_file() else None,
        "warnings": config_warnings(),
    }


def reload_settings() -> dict[str, str | bool | None | list[str]]:
    get_settings.cache_clear()
    try:
        from dotenv import load_dotenv

        load_dotenv(_ENV_FILE, override=True)
    except ImportError:
        pass
    return get_settings()
