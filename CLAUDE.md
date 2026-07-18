# CLAUDE.md

Operating instructions for AI coding assistants working in this repository. Read this before any non-trivial action.

This file is short on purpose. The project's design lives in five documents under `docs/`; this file tells you which one to load when, and lists the rules that fail CI without warning.

---

## 1. Project, in one paragraph

This is an agentic security tool: it watches public CVE/advisory feeds, determines whether a target repo is *actually exposed* (not just dependency-present) by reasoning over real call sites, and drafts a remediation PR with cited evidence. The system is a Python 3.12 LangGraph agent with a custom MCP tool layer, hybrid retrieval over Postgres + pgvector + FTS, two-tier LLM routing (cheap classify, frontier reasoning), and a hand-labeled eval harness. The signature feature is **structural capability isolation against advisory-borne prompt injection** — advisory text is attacker-controlled, and the architecture treats it as such.

---

## 2. Documents — load on demand, not all at once

Don't read every doc on every session. Load by the task at hand.

| Document | Read when |
|---|---|
| `docs/system_design.md` (HLD) | Asked about *why* something is the way it is, or making architecture-level changes |
| `docs/low_level_design.md` (LLD) | Working on a specific component, schema, class, or query |
| `docs/tdd_design.md` (TDD) | Writing tests, debating test strategy, or any AI-evaluation question |
| `docs/coding_rules.md` | Borderline style/structure decision, or any time a reviewer cites a rule by number |
| `docs/commits.md` | Planning a PR, sequencing work, or thinking about migration safety |

If a question is answered in one of these, prefer the doc to your priors. The docs were written by the project's lead engineer and are the source of truth — your training data is not.

---

## 3. The four invariants — never violated

Every change you propose must preserve all four. If you can't see how to make a change without breaking one, stop and ask the human.

1. **Capability isolation.** The only path from attacker-controlled text (advisory bodies) to a side-effecting tool (`pr_create`) goes through `draft_pr`. This is enforced by `TOOL_PERMISSIONS` in `mcp_server/server.py` and verified by `tests/unit/test_capability_graph.py`. Never import `pr_create` from any node other than `draft_pr`.

2. **Grounded output.** Every reachability verdict ships with `evidence_quotes` validated against the cited source. Hallucinated quotes fail validation, retry once, then collapse the verdict to `unsure`. Never bypass `EvidenceQuoteValidator` on an LLM output that cites the world.

3. **Bounded resource use.** No run exceeds its deadline. No call is unbounded. No `asyncio.gather` is naked. No `httpx` call without `timeout=`. No reflection loop without both an iteration cap and a convergence check.

4. **Deterministic replay.** Given the same `(advisory_id, repo_sha, recorded LLM responses)`, the agent produces the same final verdict and PR body. Don't introduce nondeterminism (random IDs without seeds, time-of-day branching, `set` ordering dependence).

These four are the reason the system can claim what it claims. They are not negotiable.

---

## 4. Hard rules at a glance

These are the `[hard]` rules from `docs/coding_rules.md`. CI fails or review blocks if violated. If you're not sure why a rule exists, read the section in the rules file before discarding it.

- **`from __future__ import annotations`** at the top of every Python file (rule 1.4).
- **`mypy --strict`** clean across module boundaries (rule 2.1).
- **`X | None` not `Optional[X]`**, `list[int]` not `List[int]` (rule 2.2).
- **`extra="forbid"`** on every Pydantic model that consumes external data (rule 2.4).
- **Constructor injection only** — no module-level singletons or globals (rule 3.4).
- **No optional parameters with mutable defaults**, no flags that change return shape (rule 3.7).
- **Never `except:` or `except Exception:`** without re-raise or specific named handling (rule 4.1).
- **`asyncio.gather` requires `return_exceptions=True` or per-task try/except** (rule 5.1).
- **Every external call has `timeout=`** — no exceptions (rule 5.2).
- **No `time.sleep` in async code, ever, including dev scripts** (rule 5.4).
- **No naked unbounded fan-out** — `asyncio.Semaphore` always (rule 5.5).
- **Raw asyncpg in hot paths**, not SQLAlchemy ORM (rule 6.1). All SQL in `core/storage/queries.sql`.
- **Every parameter is bound, never interpolated** (rule 6.3). Parameterized queries always.
- **Every LLM call passes an explicit `tier`** — no defaults (rule 7.1).
- **Every structured-output call has a Pydantic `response_format` with `extra="forbid"`** (rule 7.2).
- **Every prompt that ingests untrusted text wraps it in `<delimiter>` tags** with "treat as data" (rule 7.3).
- **Prompt changes ship with their golden recordings, atomically** (rule 7.5).
- **Reflection loops have iteration cap AND convergence check** (rule 7.6).
- **LLM outputs that cite the world are validated post-hoc** (rule 7.7).
- **Side-effecting tool clients are imported only by their authorized node** (rule 7.8).
- **`mock.patch` is banned in `tests/unit/`** — use fakes (rule 8.1).
- **No `time.sleep` in tests, no real network in unit tests** (rule 8.5).
- **Use `structlog`, never `print()`** in committed code (rules 9.1, 9.2).
- **Never log secrets; never log raw advisory bodies in the main stream** (rule 9.4).
- **Secrets only through `pydantic.SecretStr`** (rule 10.2).
- **External writes have rate limits at the boundary, not at the agent** (rule 10.3).
- **`subprocess` with list args, never `shell=True`** (rule 10.5).
- **Deadlines carried through context; no fresh budget per call** (rule 11.1).
- **No blocking I/O in async functions** — `httpx`/`asyncpg`/`aiofiles` or `to_thread` (rule 11.2).

---

## 5. The standard development loop

```
# Setup (once per machine)
make up                  # Postgres + pgvector via docker-compose
pip install -e .[dev]
pre-commit install

# Per change
pytest tests/unit -x     # < 15s, run on every save via pytest-watch
make lint                # ruff + mypy --strict
pytest tests/unit tests/property tests/contract  # < 60s, before PR
```

Per-PR CI runs unit + property + contract + integration + golden-replay + adversarial in under 4 minutes. If you push and CI takes longer, something is wrong — flag it, don't normalize it.

Real-LLM tests (`RUN_REAL_LLM_TESTS=1`) and the eval harness run nightly. Don't reach for them per-PR; they're not designed for that cadence.

---

## 6. Task playbooks

The high-leverage situations have specific moves. If your task matches one of these, follow the playbook.

### 6.1 Modifying a prompt

1. Find the prompt in `core/agent/prompts/`. Each prompt is one file.
2. Make the edit.
3. Run the affected golden tests: `pytest tests/golden/ -k <prompt_name>`. They will fail.
4. Re-record: `pytest tests/golden/ -k <prompt_name> --record`. This calls the real LLM and updates the recordings under `tests/golden/recordings/`.
5. **Inspect the recording diff.** This is the actual review artifact. If the diff is just whitespace/punctuation drift, accept. If the model's behavior changed materially, decide whether the change is intentional.
6. Commit prompt edit + recordings diff *in the same commit*. Atomicity is mandatory (commit plan principle 0.6, coding rule 7.5).
7. Run prompt regression tests: `pytest tests/regression/test_prompt_outputs.py`.

A prompt PR without an updated recordings diff is incomplete. Reviewers will reject it. Don't try to be clever.

### 6.2 Adding or modifying a database column

Migrations are **expand → backfill → contract**, never atomic.

1. Create a new alembic migration that adds the column nullable. Run up + down to verify reversibility.
2. Commit. **This is one commit.**
3. Backfill in a *separate* commit if needed. Backfills must be idempotent and resumable.
4. Make the column non-null in a *third* commit, only after backfill is verified.
5. Code that *reads* the new column lands in a fourth commit.

Reverting any single one of these leaves the system in a working state. See commit plan §0.2.

If you're tempted to combine these into one PR, you don't yet understand the rule. Re-read the section.

### 6.3 Adding or modifying an MCP tool

This is security-critical territory. Pause if you're unsure.

1. The tool definition lives in `mcp_server/tools/`. One file per tool.
2. Update `TOOL_PERMISSIONS` in `mcp_server/server.py` to grant the tool to specific node identities — and only those.
3. **The capability graph test in `tests/unit/test_capability_graph.py` will need updating.** Run it; understand what it's checking.
4. If the tool is side-effecting (writes anything outside our DB): rate-limit at the tool handler, not at the caller. See `pr_create` for the pattern.
5. Add the tool to the table in `docs/low_level_design.md` §6.1 in the same PR.

A new MCP tool without a permission entry will fail at dispatch. Don't bypass dispatch with a direct call from the agent — that defeats invariant 1.

### 6.4 Writing a new test

1. Pick the right layer (`tests/unit/` for pure logic, `tests/property/` for invariants, `tests/contract/` for boundaries, `tests/integration/` for real Postgres + recorded fakes, `tests/golden/` for end-to-end replay).
2. **No `mock.patch` in `tests/unit/`** — use the fakes in `core/agent/llm/fakes.py` (`ScriptedLLMClient`, `RecordedLLMClient`, `FakeClock`, etc.). Mocks test the mock, not the system.
3. Test name describes the behavior, not the function: `test_hallucinated_quote_triggers_retry_then_unsure`, not `test_validate_2`.
4. One assertion per test where possible. If your test name has "and" in it, split it.
5. If you're testing a pure function with an algebraic invariant (commutativity, idempotence, monotonicity), use Hypothesis. RRF, semver, quote matcher, retry backoff — all property-tested.

### 6.5 Touching anything in `core/security/` or `mcp_server/`

Standing rule: changes here go through Agent-Security review (or whoever holds that role). The capability graph and the structural injection mitigations are this project's load-bearing security claims; we don't touch them solo.

If you're an autonomous agent: explicitly note in the PR description that the change touches security-critical code, and surface this to the human reviewer.

### 6.6 Adding a Python dependency

1. Justify it in the PR description. "Convenience" isn't a justification.
2. Pin in `pyproject.toml` and `requirements.lock` together.
3. If it's a transitive of an existing dep, you don't need a justification — but the lockfile diff should make that obvious.
4. Anything that's an alternative to something we already have (a different HTTP client, a different ORM, a different test runner) defaults to no.

---

## 7. Python idioms specific to this project

The easy-to-violate rules from the coding doc, restated as patterns to follow.

**Use frozen dataclasses for value objects, Pydantic for wire types.** Don't reach for Pydantic when a `dataclass(frozen=True, slots=True)` would do — the validation cost is real.

**Inject `Clock` and `Sleeper` for any code that depends on time.** Test code uses `FakeClock`. Production passes `SystemClock()`. Defaults make production calls clean; tests override.

**Keyword-only arguments after the second positional.** `def assess(call_site, *, deadline_s, max_retries=2): ...`. Read every call site in the codebase — you'll see this everywhere.

**Newtype IDs.** We have at least four UUID types (`RunId`, `RepoId`, `AdvisoryId`, etc.). They are not interchangeable. Don't pass `uuid.UUID` where `RunId` is expected.

**Imports: stdlib → third-party → first-party, alphabetized within group.** `ruff` enforces this; you don't need to think about it, but be aware that imports are reformatted on save.

**Errors carry context, not just messages.** `raise EmbeddingFailure(f"Failed to embed advisory {advisory_id}: provider returned empty vector")`. The context in the exception is the context in the operator's log.

**Validation at the boundary, once.** If you find yourself re-checking `advisory.summary is not None` inside a function that takes a validated `Advisory`, the validation is misplaced. Fix the boundary, not the call site.

---

## 8. File system map

```
.
├── core/                  # Pure agent logic — imports stdlib + core/ only (rule 1.1)
│   ├── agent/             # State, graph, nodes, prompts, LLM client, validators
│   ├── retrieval/         # Hybrid retriever, reranker, embedder
│   ├── ingestion/         # OSV/GHSA clients, advisory ingester, code chunker
│   ├── storage/           # asyncpg pool, queries.sql, models, migrations
│   ├── github/            # GitHub API client (used by glue, not core agent)
│   ├── security/          # CapabilityGraph and related
│   └── observability/     # structlog config, LangSmith integration, cost tracking
├── mcp_server/            # MCP tool surface — composes core/
├── api/                   # FastAPI for eval harness + replay (small)
├── cli/                   # CLI entry points (replay, ingest, assess, index)
├── eval/                  # Eval harness, fixtures (committed YAML)
├── tests/
│   ├── unit/              # Pure logic, fakes only
│   ├── property/          # Hypothesis tests
│   ├── contract/          # Protocol implementations including real-service variants
│   ├── integration/       # Real Postgres, recorded LLM
│   ├── golden/            # End-to-end replay scenarios
│   ├── adversarial/       # Prompt-injection attack corpus
│   ├── regression/        # Prompt structural-output checks
│   └── fixtures/          # Shared fixtures
├── experiments/           # Spike code — gitignored from CI, never imported by core/
├── docs/                  # The five design documents
└── CLAUDE.md              # This file
```

Uploads from a user (when running interactively) land in `/mnt/user-data/uploads/` — read but never write. Outputs to share back go to `/mnt/user-data/outputs/`. Working/scratch files live in `/home/claude/`.

---

## 9. Stop and check before

These operations are easy to do confidently and wrong. Pause and surface the intent before executing.

- **Schema migrations that are not expand-only.** Dropping a column, narrowing a type, adding a non-null without a backfill commit — any of these can corrupt data on revert. Always ask.
- **Changes to `TOOL_PERMISSIONS`.** Especially: granting any node access to `pr_create`, or granting any side-effecting tool to a node that consumes advisory text. This re-opens the prompt-injection surface. Always ask.
- **Modifying `EvidenceQuoteValidator` or `quote_matches`.** These are the system's primary hallucination defense. Tightening them is fine; loosening them needs human review.
- **Disabling or skipping a test.** Quarantine a flake (move to `tests/quarantined/`, open issue) is fine. Deleting an assertion to make CI green is not.
- **Bumping or pinning down a model version.** A model version change is a behavior change; it requires golden recordings to be re-recorded and reviewed.
- **Adding a new external API call.** Even a read-only one. The call has cost, rate limits, and an availability dependency. Confirm before introducing.
- **Anything that touches `mcp_server/` or `core/security/` without security review.** Per §6.5.
- **Force-push, history rewrite, or `git reset --hard` on a branch with anyone else's commits.** Never silently. Always ask.

When in doubt, the right action is to write a comment in the PR draft saying "I'm about to do X — confirm?" and pause.

---

## 10. When stuck

In this order:

1. **Run the relevant tests.** Failing tests usually tell you exactly what's wrong. Don't guess — run.
2. **Read the relevant doc.** The five docs in `docs/` were written to answer the questions you're having. The map is in §2 above.
3. **Look at how the existing code does it.** This codebase is internally consistent. The third Pydantic model, the third SQL query, the third async fan-out should look like the first two.
4. **Check `tests/golden/scenarios/` and `tests/adversarial/corpus/`.** Real cases, real expected outcomes. Often the example you need.
5. **Ask the human.** If you've spent 15 minutes and you're not closer, surface what you're stuck on. The human's time is cheaper than wrong code.

Don't ship code you don't understand. Don't paper over a failing test by deleting the assertion. Don't guess at semver semantics, async semantics, or LLM token-counting semantics — these are exactly the places where confident-looking wrong code does the most damage.

---

## 11. Updating CLAUDE.md

This file changes when:

- A new hard rule lands in `coding_rules.md`. Update §4.
- The doc map in `docs/` changes. Update §2.
- A new task playbook becomes worth codifying (you've seen the same kind of mistake three times). Add to §6.
- An invariant changes. This should be rare; treat with extreme care.

CLAUDE.md changes are reviewed by humans before merge — they shape every future agent's behavior in this repo. Don't make this file longer to be thorough. Make it shorter when you can. The shorter it is, the more of it gets read.
