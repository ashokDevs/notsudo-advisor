# NotSudo — 90-second demo script

**One line:** Dependabot flags packages. NotSudo flags only what your code can actually hit — then opens a fix PR with evidence.

---

## Setup (before stage)

```bash
pip install -e ".[dev]"
# optional: OPENAI_API_KEY, GITHUB_TOKEN in .env
make serve   # http://127.0.0.1:8080
```

Terminal backup if UI flakes:

```bash
python -m cli.main demo
# or
python -m cli.main scan demo_app
python -m cli.main scan https://github.com/expressjs/express
```

---

## Live talk track (~90s)

### 0:00–0:15 — Hook
> “Most scanners treat every vulnerable dependency as a fire. Engineers mute them.  
> NotSudo answers a different question: **can production code actually reach the vulnerable path?**”

Open Dashboard → [http://127.0.0.1:8080/Dashboard.html](http://127.0.0.1:8080/Dashboard.html)

### 0:15–0:40 — Scan (any repo)
Paste either:
- Local: `D:\Games\NOTSUDO\demo_app`
- GitHub: `https://github.com/expressjs/express` (public clone)

Click **Scan**.

Point at the **summary strip**:
> “OSV found N advisories — that’s the Dependabot-style ceiling.  
> Only **E exposed** are reachability-confirmed. The rest are safe or unsure — noise you don’t open PRs for.”

Default filter is **exposed**.

### 0:40–1:05 — Evidence
Expand one **exposed** card.
Show:
1. Reasoning (why reachable)
2. **Call sites** with `file:line` and snippet
3. Evidence quote (validated against source)
4. Preflight status if present

> “We’re not guessing from the advisory alone — we found the call site in *their* tree.”

### 1:05–1:20 — Fix
Click **Open fix PR** (needs GitHub auth) **or** show PR draft title from CLI.
> “Version bump only. Human still reviews. Never auto-merge.”

### 1:20–1:30 — Security punchline
Open Security tab or say:
> “Advisory feeds are attacker-controlled. Nodes that read advisory text **cannot** open PRs.  
> Only the act node has `pr_create`. That’s structural isolation — not a prompt.”

---

## Backup one-liners

| Objection | Answer |
|-----------|--------|
| “Snyk already does reachability” | “We’re the fast advisory→evidence→PR loop next to Dependabot, with injection isolation as a first-class claim.” |
| “What about false negatives?” | “Syntactic call sites miss dynamic dispatch — we mark **unsure** and never claim graph completeness.” |
| “No LLM key?” | “Heuristics still run: imports, calls, test-path filter, severity. LLM upgrades quotes when available.” |

---

## Success checklist

- [ ] Stranger can scan in &lt; 2 minutes  
- [ ] At least one **safe/unsure** next to **exposed** (noise vs signal)  
- [ ] Call site `file:line` visible  
- [ ] Fix path shown (PR or draft)  
- [ ] Isolation explained in 20s  

If any box fails, fix that before adding features.
