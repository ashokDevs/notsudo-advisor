# Deploy NotSudo online (public URL)

Goal: anyone (or you from any device) opens `https://your-app...` → scans GitHub repos → optional fix PRs.

---

## What “online” needs

| Piece | Why |
|--------|-----|
| Public HTTPS URL | Browser + GitHub OAuth callback |
| `git` on the server | Clone public repos for scan |
| Secrets in host env | OpenRouter + GitHub (never commit `.env`) |
| `APP_BASE_URL=https://...` | OAuth redirects + cookies |

Local paths like `D:\...` **won’t exist** on the cloud box. Online, always scan:

```text
https://github.com/org/repo
```
or
```text
owner/repo
```

`demo_app` is bundled in the Docker image so that quick demo still works.

---

## Fastest path: Render (free tier)

### 1. Push this repo to GitHub

```bash
git add .
git commit -m "feat: online deploy"
git push origin main
```

### 2. Create Web Service on Render

1. [https://dashboard.render.com](https://dashboard.render.com) → **New** → **Web Service**
2. Connect your `notsudo-advisor` repo
3. **Runtime:** Docker (uses our `Dockerfile`)
4. **Instance:** Free is fine for demos

### 3. Environment variables (Render → Environment)

| Key | Value |
|-----|--------|
| `APP_BASE_URL` | `https://YOUR-SERVICE.onrender.com` (set after first deploy, then redeploy) |
| `SESSION_SECRET` | long random string |
| `NOTSUDO_HASH_EMBEDDINGS` | `1` |
| `OPENAI_API_KEY` | your OpenRouter key `sk-or-...` |
| `OPENAI_API_BASE` | `https://openrouter.ai/api/v1` |
| `LLM_MODEL` | e.g. `openrouter/auto` or `openai/gpt-4o-mini` |
| `GITHUB_TOKEN` | fine-grained PAT (repo contents + PRs write) |
| `GITHUB_DEMO_REPO` | `youruser/your-repo` that the PAT can write |
| `GITHUB_CLIENT_ID` | optional OAuth App client id |
| `GITHUB_CLIENT_SECRET` | optional OAuth App secret |

### 4. GitHub OAuth App (only if you want “Sign in with GitHub”)

1. [https://github.com/settings/developers](https://github.com/settings/developers) → **OAuth Apps** → **New**
2. **Homepage URL:** `https://YOUR-SERVICE.onrender.com`
3. **Authorization callback URL:**  
   `https://YOUR-SERVICE.onrender.com/auth/github/callback`
4. Generate **Client secret** → put in Render env as `GITHUB_CLIENT_SECRET`
5. Put Client ID in `GITHUB_CLIENT_ID`
6. Set `APP_BASE_URL` to the same HTTPS origin

If you only set `GITHUB_TOKEN`, Sign-in is optional — **Open fix PR** still works with the PAT.

### 5. Open the site

```text
https://YOUR-SERVICE.onrender.com/Dashboard.html
```

Scan e.g. `https://github.com/OWASP/NodeGoat`

---

## Alternative: Railway

1. [railway.app](https://railway.app) → New Project → Deploy from GitHub  
2. Add variables (same table as above)  
3. Generate domain → set `APP_BASE_URL=https://your-app.up.railway.app`  
4. Redeploy  

---

## Alternative: Fly.io

```bash
fly launch
fly secrets set OPENAI_API_KEY=... OPENAI_API_BASE=https://openrouter.ai/api/v1 \
  LLM_MODEL=openrouter/auto GITHUB_TOKEN=... GITHUB_DEMO_REPO=you/repo \
  APP_BASE_URL=https://YOUR-APP.fly.dev SESSION_SECRET=...
fly deploy
```

---

## Quick “online on your PC” (ngrok) — no cloud host

Good for demos when you already run locally:

```powershell
# Terminal 1
python -m uvicorn api.app:app --host 0.0.0.0 --port 8080

# Terminal 2 (install: https://ngrok.com)
ngrok http 8080
```

ngrok prints `https://abc123.ngrok-free.app`. Then:

1. In `.env`:
   ```env
   APP_BASE_URL=https://abc123.ngrok-free.app
   ```
2. OAuth App callback (if used):  
   `https://abc123.ngrok-free.app/auth/github/callback`
3. Restart uvicorn  
4. Share the ngrok URL

---

## Checklist after deploy

| Check | URL / action |
|-------|----------------|
| Health | `GET https://your-app/api/health` → `"ok": true` |
| LLM | `"llm": true`, `"llm_provider": "openrouter"` |
| UI | `/Dashboard.html` loads |
| Scan | Paste `OWASP/NodeGoat` → live results |
| PR | Needs `GITHUB_TOKEN` or OAuth session |

---

## Security notes (online)

- Never commit `.env` or tokens  
- Prefer fine-grained PAT limited to one demo repo  
- Free Render spins down when idle — first request may be slow  
- Don’t enable auto-merge; always human-review PRs  

---

## Local Docker smoke test

```bash
docker build -t notsudo .
docker run --rm -p 8080:8080 \
  -e OPENAI_API_KEY=sk-or-... \
  -e OPENAI_API_BASE=https://openrouter.ai/api/v1 \
  -e LLM_MODEL=openrouter/auto \
  -e GITHUB_TOKEN=github_pat_... \
  -e GITHUB_DEMO_REPO=you/repo \
  -e APP_BASE_URL=http://localhost:8080 \
  -e SESSION_SECRET=dev \
  notsudo
```

Open http://localhost:8080
