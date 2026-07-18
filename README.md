# NotSudo Advisor

**Find dependency vulnerabilities that are actually reachable — and open a fix PR with cited evidence.**

Most scanners flag *presence* of a vulnerable package. NotSudo reasons about **reachability**: does your code import and call the vulnerable path from production entry points?

```
OSV advisories → semver match → call-site location → reachability verdict
       → evidence-quote validation → lockfile preflight → fix PR
```

## Features

| Feature | Status |
|--------|--------|
| OSV advisory lookup (npm + PyPI manifests) | ✅ |
| Semver / OSV range matching (not “present ⇒ vulnerable”) | ✅ |
| Import + syntactic call-site finder | ✅ |
| Reachability verdicts: `exposed` / `safe` / `unsure` | ✅ |
| Evidence quote grounding (hallucinated quotes rejected) | ✅ |
| Two-tier LLM client (`cheap` / `frontier`) with heuristic fallback | ✅ |
| Lockfile preflight (`npm install --package-lock-only`) | ✅ |
| Local fix (`/api/fix-local`) + GitHub fix PRs (OAuth or `GITHUB_TOKEN`) | ✅ |
| LangGraph agent: triage → locate → reason → preflight → act | ✅ |
| MCP tool server with **capability isolation** | ✅ |
| CLI: `scan`, `analyze`, `run-pipeline`, `index`, `watch-osv` | ✅ |
| Dashboard UI scan + one-click PR | ✅ |
| Structural capability-isolation tests | ✅ |
| Eval harness with accuracy CI band | ✅ |

## Deploy online (public URL)

Full guide: **[`docs/DEPLOY_ONLINE.md`](docs/DEPLOY_ONLINE.md)**

Short version (Render / Railway / Docker):

1. Push repo to GitHub  
2. Deploy with the included `Dockerfile`  
3. Set env vars on the host: `OPENAI_API_KEY`, `OPENAI_API_BASE`, `GITHUB_TOKEN`, `GITHUB_DEMO_REPO`, `APP_BASE_URL=https://your-service...`, `SESSION_SECRET`  
4. Online scans use **GitHub URLs** (`https://github.com/org/repo`) — not `D:\...` paths  
5. Optional OAuth: callback `https://your-service.../auth/github/callback`  

Quick tunnel from your PC:

```bash
ngrok http 8080
# set APP_BASE_URL to the ngrok https URL and restart
```

## Quick start (local)

### 1. Install

```bash
# Python 3.12+
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -e ".[dev]"
cp .env.example .env
# Optional but recommended for best reachability reasoning:
#   OPENAI_API_KEY=sk-...
# Optional for GitHub PRs without OAuth UI:
#   GITHUB_TOKEN=ghp_...
```

### 2. Scan anything (local path **or** GitHub URL)

```bash
# Bundled demo (outdated lodash/minimist/express + real call sites)
python -m cli.main scan demo_app

# Public GitHub repo — shallow clone → scan → cleanup
python -m cli.main scan https://github.com/expressjs/express
python -m cli.main scan expressjs/express

# 90-second pitch (presence vs exposure + call sites)
python -m cli.main demo
```

Talk track: [`docs/demo_script.md`](docs/demo_script.md).

Example output lines:

```
[exposed] GHSA-...  lodash@4.17.20 → 4.17.21  conf=0.78
  lodash is imported and called from production paths (src/server.js, src/utils.js)...
```

Without `OPENAI_API_KEY`, the system uses a **deterministic heuristic** (imports, call sites, severity, test-path filtering). With a key, the frontier model produces grounded evidence quotes.

### 3. Single-advisory replay

```bash
notsudo analyze GHSA-fvqr-27wr-82fm demo_app --package lodash
```

### 4. Full LangGraph agent

```bash
notsudo run-pipeline GHSA-fvqr-27wr-82fm demo_app
```

### 5. Web UI

```bash
make serve
# open http://localhost:8080/Dashboard.html
# Paste local path OR https://github.com/org/repo → Scan
# Default filter = exposed (reachability-confirmed)
# Expand a row → call sites file:line + evidence
# Sign in with GitHub (OAuth) or set GITHUB_TOKEN to open fix PRs
```

### 6. Apply a local fix (no GitHub)

```bash
curl -X POST http://localhost:8080/api/fix-local \
  -H "Content-Type: application/json" \
  -d "{\"repo_path\": \"D:/Games/NOTSUDO/demo_app\", \"pkg\": \"lodash\", \"fix\": \"4.17.21\"}"
```

## Architecture

```
api/            FastAPI — scan, analyze, OAuth, PR, local fix
cli/            Typer CLI
core/analysis/  semver, call sites, evidence, reachability, preflight, pipeline
core/orchestration/  LangGraph nodes + graph
core/security/  CapabilityGraph + TOOL_PERMISSIONS
core/llm/       two-tier LLM client
mcp_server/     MCP tools (capability-checked)
demo_app/       vulnerable target for demos/eval
eval/           ground-truth harness
frontend/       Landing + Dashboard
```

### Capability isolation

Advisory text is attacker-controlled. Nodes that read advisory content (`triage`, `locate`, `reason`) **cannot** call `pr_create`. Only `act` / `draft_pr` may. Enforced by `core/security/capability_graph.py` and tested in `tests/unit/test_capability_graph.py`.

### Grounded evidence

Reachability answers that cite code must pass `EvidenceQuoteValidator`. Failed quotes trigger one retry, then collapse to `unsure`.

## Environment

See `.env.example`:

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | LLM reachability + structured output |
| `LLM_MODEL` / `LLM_CHEAP_MODEL` | Frontier / cheap models |
| `GITHUB_TOKEN` | Open fix PRs without browser OAuth |
| `GITHUB_CLIENT_ID` / `SECRET` | Dashboard “Sign in with GitHub” |
| `GITHUB_DEMO_REPO` | `owner/name` for fix PRs |
| `DATABASE_URL` | Postgres for index/RAG path |
| `NOTSUDO_HASH_EMBEDDINGS=1` | Skip downloading BGE; use hash vectors |

## Postgres (optional RAG index)

```bash
make up
alembic upgrade head
notsudo index demo_app
```

Scanning and fix flow work **without** Postgres. Indexing enables hybrid vector+FTS MCP `code_search`.

## Tests

```bash
# unit + lightweight tests (no live OSV required for most)
set NOTSUDO_HASH_EMBEDDINGS=1
pytest tests/unit tests/test_smoke.py -q

# live eval against OSV + demo_app (network)
python -m eval.run
```

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/scan` | `{ "repo_path": "..." }` full analysis |
| POST | `/api/analyze` | single advisory replay |
| POST | `/api/fix-local` | bump version on disk |
| POST | `/api/pr` | open GitHub fix PR (session or PAT) |
| GET | `/api/health` | liveness + config flags |
| GET | `/api/me` | OAuth user + config |

## Limitations (honest)

- Call-site finder is **syntactic** (regex/AST-level), not a full JS call graph. Dynamic `obj[name]()` can be missed.
- Without an LLM key, verdicts use severity + import/call heuristics.
- Preflight needs `npm` (or `pip`) installed for full resolution checks; otherwise manifest patch validation only.
- v1 ecosystems: **npm** first-class; **PyPI** manifests supported for scan/fix.
- Auto-merge is intentionally **never** performed.

## Docs

Deeper design lives in `docs/` (`system_design.md`, `idea.md`, `coding_rules.md`, `tdd_design.md`, `commits.md`). `CLAUDE.md` is the operator guide for AI assistants.

## License

See repository owner for license terms.
