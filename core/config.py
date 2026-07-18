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
    # Also try cwd (when launched from elsewhere)
    load_dotenv(override=False)
except ImportError:
    pass


def _truthy(name: str, default: str = "") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def get_settings() -> dict[str, str | bool | None]:
    """Snapshot of runtime config (no secrets returned to clients)."""
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY") or ""
    base = (
        os.getenv("OPENAI_API_BASE")
        or os.getenv("OPENAI_BASE_URL")
        or os.getenv("LLM_BASE_URL")
        or ""
    ).rstrip("/")
    model = os.getenv("LLM_MODEL") or os.getenv("LLM_FRONTIER_MODEL") or "gpt-4o"
    cheap = os.getenv("LLM_CHEAP_MODEL") or model
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if not provider:
        if "openrouter" in base or api_key.startswith("sk-or-"):
            provider = "openrouter"
        elif "localhost" in base or "127.0.0.1" in base:
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
        "llm_base_url": base or None,
        "llm_model": model,
        "llm_cheap_model": cheap,
        "github_oauth": bool(os.getenv("GITHUB_CLIENT_ID") and os.getenv("GITHUB_CLIENT_SECRET")),
        "github_client_id_set": bool(os.getenv("GITHUB_CLIENT_ID")),
        "github_client_secret_set": bool(os.getenv("GITHUB_CLIENT_SECRET")),
        "github_pat": bool(os.getenv("GITHUB_TOKEN")),
        "github_demo_repo": os.getenv("GITHUB_DEMO_REPO", "ashokDevs/notsudo-demo-app"),
        "app_base_url": app_base_url(),
        "online": is_production(),
        "database_url_set": bool(os.getenv("DATABASE_URL")),
        "hash_embeddings": _truthy("NOTSUDO_HASH_EMBEDDINGS", "1"),
        "env_file": str(_ENV_FILE) if _ENV_FILE.is_file() else None,
    }


def llm_api_key() -> str | None:
    key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    return key or None


def llm_base_url() -> str | None:
    base = (
        os.getenv("OPENAI_API_BASE")
        or os.getenv("OPENAI_BASE_URL")
        or os.getenv("LLM_BASE_URL")
        or ""
    ).rstrip("/")
    return base or None


def llm_models() -> tuple[str, str]:
    frontier = os.getenv("LLM_MODEL") or os.getenv("LLM_FRONTIER_MODEL") or "gpt-4o"
    cheap = os.getenv("LLM_CHEAP_MODEL") or frontier
    return cheap, frontier


def github_oauth_credentials() -> tuple[str, str]:
    return (
        os.getenv("GITHUB_CLIENT_ID", "").strip(),
        os.getenv("GITHUB_CLIENT_SECRET", "").strip(),
    )


def github_demo_repo() -> str:
    return os.getenv("GITHUB_DEMO_REPO", "ashokDevs/notsudo-demo-app").strip()


def app_base_url() -> str:
    """
    Public origin of this deployment.
    Online: set APP_BASE_URL=https://your-app.onrender.com (required for OAuth).
    """
    explicit = (os.getenv("APP_BASE_URL") or "").strip().rstrip("/")
    if explicit:
        return explicit
    render = (os.getenv("RENDER_EXTERNAL_URL") or "").strip().rstrip("/")
    if render:
        return render
    railway = (os.getenv("RAILWAY_PUBLIC_DOMAIN") or "").strip()
    if railway:
        if railway.startswith("http"):
            return railway.rstrip("/")
        return f"https://{railway}"
    return "http://localhost:8080"


def is_production() -> bool:
    if _truthy("NOTSUDO_PRODUCTION"):
        return True
    base = app_base_url()
    return base.startswith("https://") and "localhost" not in base


def session_https_only() -> bool:
    """Secure cookies on HTTPS deployments."""
    if os.getenv("SESSION_HTTPS_ONLY") is not None:
        return _truthy("SESSION_HTTPS_ONLY")
    return is_production()


def session_secret() -> str:
    return os.getenv("SESSION_SECRET") or "notsudo-dev-insecure-change-me"


def github_token() -> str | None:
    tok = os.getenv("GITHUB_TOKEN", "").strip()
    return tok or None


def reload_settings() -> dict[str, str | bool | None]:
    get_settings.cache_clear()
    try:
        from dotenv import load_dotenv

        load_dotenv(_ENV_FILE, override=True)
    except ImportError:
        pass
    return get_settings()
