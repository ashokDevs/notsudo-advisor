# Dependency Exploitability Advisor

> Agentic security tool that watches public CVE/advisory feeds, determines whether a target repo is *actually exposed* (not just dependency-present) by reasoning over real call sites, and drafts a remediation PR with cited evidence.

---

## Framing

- **Project type:** Portfolio project, framed as production-style.
- **Target audience:** AI engineering / applied AI hiring managers in 2026.
- **Resume narrative:** Autonomous reliability/security system that detects, diagnoses, and patches dependency vulnerabilities using grounded retrieval and agentic reasoning over real call sites.
- **Core differentiation:** Snyk/Dependabot are rule-based and flag *presence* of a vulnerable dependency. This system reasons about *reachability* — does your code actually invoke the vulnerable function, with real input? That's the AI value-add and the demo's wow moment.

---

## Demo Scenario

Replay-mode trigger fires on a curated CVE → agent identifies it hits `lodash@4.17.20` in the demo repo → ast-grep finds 3 call sites → reachability reasoning judges only 1 reaches the vulnerable path → preflight verifies the proposed bump resolves cleanly → PR opens with citations to the advisory and the call site. Total wallclock: < 90 seconds.

---

## Architecture

See the eraser.io diagram (`architecture.eraser` / rendered PNG in repo).

### Trigger
- **Live mode:** hourly cron over OSV deltas (+ GHSA supplementary). Persisted high-watermark, deltas only.
- **Replay mode:** explicit `advisory_id` injected for deterministic demos and eval. Same downstream pipeline.

### RAG layer (Postgres + pgvector + FTS)
- **Advisory corpus:** OSV-primary, GHSA supplementary, normalized to one schema with affected ranges and references. Bootstrap via OSV daily-dump (~250k records, ~$25 one-time embed).
- **Code corpus:** target repo, chunked by function/class with file/line metadata. Re-chunked on each main-branch update.
- **Hybrid retrieval:** vector similarity + Postgres FTS (BM25-equivalent) merged via reciprocal rank fusion. Symbol names like `_.template` are exactly the high-precision lexical match that pure vector search underweights.
- **HyDE query generation:** advisory text and code live in different domains. Cheap LLM generates a hypothetical vulnerable function signature/snippet from the advisory; embed that for retrieval.
- **Cross-encoder reranker:** top-50 retrieved → top-5 reranked. Local BGE or Cohere Rerank.

### LangGraph orchestration
Nodes (genuine branches and loops):
1. `classify_advisory` — severity, ecosystem, affected versions (cheap)
2. `extract_vulnerable_symbols` — structured extraction, prompt-injection hardened (cheap)
3. `match_dependency` — semver math, no LLM
4. `HyDE_generate` — hypothetical vulnerable code snippet (cheap)
5. `hybrid_retrieval` — pgvector + FTS + RRF
6. `rerank` — cross-encoder
7. `locate_call_sites` — ast-grep, no LLM
8. `assess_reachability` — async fan-out, one task per call site (frontier)
9. `relevance_critique` — Self-RAG loop back to (5) on low confidence (cheap)
10. `decide_action` — bump / pin / no-op / escalate (cheap)
11. `preflight` — `npm install --package-lock-only` resolves cleanly
12. `draft_pr` — PR body with citations (frontier)

### MCP tool layer (custom MCP server, ≥7 tools)
- `advisory_query` (OSV / GHSA)
- `dep_manifest_read` (package.json / package-lock.json)
- `dep_registry_query` (npm registry — what patched versions exist)
- `code_search` (hybrid retrieval over code corpus)
- `code_read` (file ranges)
- `git_blame` (when did this call site land?)
- `pr_create` (GitHub API)

### LLM tier (two-tier, prompt-cached)
| Node | Tier | Reason |
|---|---|---|
| `classify_advisory` | cheap | structured extraction |
| `extract_vulnerable_symbols` | cheap | structured extraction |
| `HyDE_generate` | cheap | bounded creative task |
| `relevance_critique` | cheap | binary judgment, high volume |
| `decide_action` | cheap | rule application |
| `assess_reachability` | **frontier** | the actual reasoning — value prop |
| `draft_pr` | **frontier** | user-facing prose |

Single provider (OpenAI *or* Anthropic) behind one `LLMClient` with `cheap()` / `frontier()` methods. Prompt caching on the long shared context (advisory text + repo overview) used by per-call-site reasoning.

### Output surface
GitHub PR only. Single-repo PAT for v1 (multi-tenant App is v2). Eval harness calls internal Python entry points directly — that's plumbing, not a second surface.

PR body structure:
1. **TL;DR** — `pkg@oldver` → `pkg@newver`, X of Y call sites reachable
2. **Advisory citation** — OSV/GHSA link, severity, affected ranges
3. **Reachability evidence** — file:line per call site + per-site verdict + reasoning
4. **Pre-flight check** — lockfile resolution success
5. **Diff explanation** — why this version, why not a higher major

### Observability
LangSmith for end-to-end agent tracing and replay. Spans on every node, retry counters, token cost per run.

### State
Stateless reasoning + `(advisory_id, repo_sha) → verdict` memoization cache. No cross-run learning (would create circular feedback against the eval).

---

## Demo & Eval Targets

- **Demo target (must look real):** ~1.5k-line Express + Postgres notes/blog app I build, ~15 deps deliberately pinned to versions from ~18 months ago so real CVEs land naturally. README is honest about the methodology.
- **Eval target (must have ground truth):** [NodeGoat](https://github.com/OWASP/NodeGoat) — known-vulnerable call sites give labeled exploitable/non-exploitable cases. Lives in eval harness, never in demo footage.

Demo and eval kept separate on purpose: one repo for both is a trap.

---

## Evaluation

Two-layer eval — task accuracy on hand-labeled ground truth, retrieval quality via Ragas.

- **Eval set:** ~30 `(advisory_id, repo_snapshot_sha, expected_verdict, expected_call_sites)` tuples. Half NodeGoat (known truth), half real CVEs vs. the demo app (manually verified).
- **Metrics:**
  - **Reachability precision / recall / F1** — hand-labeled comparison
  - **Retrieval context_precision / context_recall** — Ragas, on the retrieval sub-step only
  - **Cost / latency** per case
- **`run_eval.py`** outputs a confusion matrix + per-case markdown showing where the agent disagreed with ground truth (the gold for the README).
- **CI hook:** eval runs on every push; README badge shows current F1.

Why not Ragas for the verdict: classification with verifiable ground truth wants direct F1, not LLM-as-judge. Using Ragas only where it actually fits (retrieval) is itself the senior signal.

---

## Tech Stack

**Languages / runtime:** Python 3.12 (agent), Node.js (target apps only). v1 ecosystem support: **JS/TS only** — npm has the highest CVE volume; ecosystem-agnostic claim is a v2.

**Stack keywords:**
Python · LangGraph · MCP (custom server) · OpenAI / Anthropic SDK · Postgres + pgvector · Postgres FTS · Cohere Rerank (or local BGE) · LangSmith · asyncio · Pydantic · Ragas · GitHub API · ast-grep · Docker.

**Technique keywords:**
Agentic RAG · Self-RAG / reflection loops · HyDE · hybrid retrieval (BM25 + vector) with reciprocal rank fusion · cross-encoder reranking · two-tier model routing · prompt caching · structured extraction · prompt-injection hardening on untrusted advisory text · hand-labeled F1 evaluation · retrieval evaluation · CI-integrated agent eval · end-to-end tracing.

---

## Out of Scope for v1

Explicitly *not* doing — tempting but add risk without demo value:

- Multi-tenant / multi-repo dashboards
- Sandbox execution / dynamic analysis (preflight only goes as far as `--package-lock-only`)
- Past-incident RAG (no real history corpus exists yet)
- Embedding-based anomaly detection on the trigger side
- Cross-run learning (circular feedback risk vs. eval)
- Python ecosystem support (v2)
- Multi-provider LLM routing (v2)
- Transitive call-graph reachability (v1.5 stretch)
- GitHub App / OAuth (v2 — single-repo PAT for v1)
- Kafka, Kubernetes, BullMQ
- Auto-merge — always human-in-the-loop on the PR

---

## Build Order (rough)

1. Ingestion + advisory corpus + embed pipeline
2. Code chunker + code corpus + hybrid retrieval (no agent yet)
3. ast-grep call-site finder + standalone reachability prompt (frontier model, manual)
4. Wrap as LangGraph nodes, add reflection loop
5. MCP server exposing the tools
6. PR drafting + preflight + GitHub integration
7. HyDE + reranker (quality boost, measure delta in eval)
8. LangSmith tracing, prompt caching, two-tier routing (measure cost delta)
9. Eval harness + Ragas + CI badge
10. Demo target app + record video

Each step ships a measurable improvement against the eval — that's the README narrative.

---

## Goal

Demonstrate end-to-end agentic AI engineering — grounded retrieval over a real corpus, non-trivial control flow, multi-tool orchestration, cost-aware inference, measurable evaluation — on a problem where reasoning genuinely beats rules.
