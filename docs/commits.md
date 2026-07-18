# Commit Plan

**Companion to:** HLD, LLD, TDD doc, Coding Rules.
**What this is:** the build sequence as a series of commits, organized into phases. Each commit is atomic — it leaves the system in a state that's tested, deployable, and revertable.
**What this is not:** a Gantt chart. There are no week numbers. The unit is *what's true after this commit* and *what's safe to revert to*. Calendar time is whatever it ends up being.

---

## 0. Principles that govern the plan

These are the rules the commit list answers to. If a proposed commit can't satisfy all eight, it gets split.

**0.1 — Every commit on `main` is deployable.** Tests pass at that commit. The system works at that commit, within the scope of capability that exists at that commit. Revert is `git revert` and nothing else.

**0.2 — Migrations are expand → backfill → contract, never atomic.** A schema change that requires a code change is at least three commits: add column nullable, backfill it, make it non-null. Each is independently revertable. Reverting commit N+2 doesn't strand commit N's data; reverting N still leaves N+1 working against the (now nullable again) column.

**0.3 — Reverting code does not unwind data.** Some commits add data (ingestion runs, embeddings written). Reverting the commit doesn't delete the data — the data is just orphaned and the schema still holds it. "Revert safety" means "the system can roll forward from here," not "the universe returns to its prior state."

**0.4 — Tests ship with the code they cover, in the same commit.** Never "tests in a follow-up." A revert that drops tested code drops the tests that prove it works; a follow-up tests commit means there's a window where the code is on `main` untested. Both atomic.

**0.5 — Feature flags gate risky behavior changes.** Three commits, not one: introduce flag (default-off, behavior unchanged), implement gated behavior, flip flag in its own commit. The flip commit is the actual deploy and is the one we revert if it goes wrong.

**0.6 — Prompts ship with their golden recordings, atomically.** Per coding rule 7.5. A diff that touches `core/agent/prompts/*.py` and the diff that touches `tests/golden/recordings/*.json` are one commit. A reviewer should see both halves of any prompt change.

**0.7 — Refactor commits are behavior-preserving by construction.** If a refactor changes behavior, it's two commits: the refactor (no test deltas) and the behavior change (test deltas). A `refactor:` commit whose tests change has lied about what it is.

**0.8 — Conventional Commits, single-purpose, no WIP on `main`.** Subject prefixes: `feat`, `fix`, `refactor`, `test`, `chore`, `docs`, `perf`, `migrate`. Squash before merge — the reflog is for branches, not for `main`. Every commit's body answers two questions:
- *What's now possible that wasn't before?*
- *What does it cost to revert?*

---

## 1. Phase reference

Phases are capability-shaped, not time-shaped. Each phase ends with the system having one new end-to-end capability the prior phase didn't have. Sub-phase commits are listed in dependency order; you can't reorder within a phase without breaking the always-green property.

| # | Phase | Capability gained at end of phase | Commits |
|---|---|---|---|
| 1 | Foundations | Empty repo passes CI on push | 6 |
| 2 | Data plane (advisories) | OSV advisories ingestible and queryable | 7 |
| 3 | Code corpus | Repo can be chunked, embedded, indexed | 5 |
| 4 | Hybrid retrieval | "Find code relevant to text" works against the corpus | 6 |
| 5 | Reachability core (no agent) | Given advisory + call site, get a grounded verdict | 8 |
| 6 | LangGraph orchestration | Agent runs end-to-end on a scripted LLM | 7 |
| 7 | MCP + capability isolation | Agent runs through MCP; structural security tests pass | 5 |
| 8 | Action layer | Real PR opens against a sandbox repo | 6 |
| 9 | Optimization (gated) | Each optimization shows measurable delta or is removed | 6 |
| 10 | Eval harness + CI | F1 with bootstrap CI on every push, per-commit cost tracked | 5 |
| 11 | Adversarial hardening | Injection corpus runs; structural-isolation invariants hold | 4 |
| 12 | Demo target + cutover | Demo app exists, shadow mode runs against it | 4 |

**Total: ~69 atomic commits.** Real history will have more (review fixups during PR, squashed at merge), but the merge-commit count on `main` is what this lists.

---

## 2. Phase 1 — Foundations

The point of this phase is that an empty `main` with nothing in it must already enforce the rules of every later phase. CI exists before code exists.

**1.1 — `chore: bootstrap repository structure`**
- Now possible: `git clone` produces a working layout. `pyproject.toml`, `core/`, `tests/`, `mcp_server/`, `api/`, `cli/`, `eval/` directories with `__init__.py`. Empty `README.md`.
- Revert safety: revert returns to an empty directory. No state.
- Tests added: none yet (no code).

**1.2 — `chore: pin Python 3.12 and lock dependencies`**
- Now possible: `pip install -e .[dev]` produces a deterministic environment. `requirements.lock` committed. `python --version` mismatch fails install with a clear error.
- Revert safety: revert leaves the working tree without a lock; install still works against `pyproject.toml`, just non-deterministic. Acceptable rollback state.
- Tests: none.

**1.3 — `chore: configure ruff, mypy --strict, pre-commit`**
- Now possible: `pre-commit run --all-files` passes on the empty tree. PRs can fail lint/type CI.
- Revert safety: revert removes the gate but doesn't break anything that was passing. Subsequent commits would run un-linted; CI would be permissive — undesirable but not broken.
- Tests: none, but the gate exists.

**1.4 — `chore: GitHub Actions skeleton — lint, type, test on push and PR`**
- Now possible: every push gets CI. The badge is `passing` because there's nothing to fail.
- Revert safety: no CI is bad, but reverting back to no CI doesn't break code. The pre-commit hook is the local backstop.
- Tests: a single `tests/test_smoke.py` asserting `True`. Exists so the test runner is wired.

**1.5 — `chore: docker-compose for local Postgres 16 + pgvector`**
- Now possible: `make up` starts a clean Postgres with pgvector available. `make db-shell` connects.
- Revert safety: nothing in `core/` references the DB yet. Revert removes a developer convenience, not capability.
- Tests: none directly; integration tests in later phases use this.

**1.6 — `feat: structlog config, no-op logger as default`**
- Now possible: `from core.observability.logging import get_logger` returns a configured structlog logger. JSON in prod, console in dev (env-driven).
- Revert safety: any caller in later commits would have to import directly from structlog, ugly but functional. Revert is local.
- Tests: one unit test on the JSON formatter (`test_log_emits_structured_json`).

End of Phase 1: empty repo with full guardrails. Every later commit lands on this surface.

---

## 3. Phase 2 — Data plane (advisories)

We need advisories before we need anything else. This phase ends with: "we can ingest from OSV and query by package."

**2.1 — `migrate: create tenants, repos, advisories tables (initial)`**
- Now possible: `alembic upgrade head` produces the schema for `tenants`, `repos`, `advisories` (LLD §2.2). All columns present including `embedding vector(1024)` (nullable for now), `fts` generated column, both indexes. No data.
- Revert safety: `alembic downgrade -1` drops the tables. No data to lose. **Migration is reversible — the down-migration is part of the commit.**
- Tests: `tests/integration/test_migrations.py::test_up_then_down_is_clean` runs the full up/down cycle, asserts no leftover artifacts.

**2.2 — `feat: storage layer — asyncpg pool, queries.sql loader`**
- Now possible: `Database` class with connection pool. `queries.sql` parsed into a dict at import. Health check returns OK.
- Revert safety: nothing depends on this yet.
- Tests: `tests/integration/test_db_pool.py` (real Postgres, asserts pool acquire/release, query timeout).

**2.3 — `feat: Advisory and related Pydantic schemas`**
- Now possible: `Advisory`, `AffectedRange`, `Reference` types in `core/storage/models.py`. `extra="forbid"`. Round-trip from `raw` jsonb to model and back.
- Revert safety: pure types, no consumers yet.
- Tests: ~15 unit tests covering Pydantic validation cases — including `test_unknown_field_rejected_when_extra_forbid` to lock in coding rule 2.4.

**2.4 — `feat: OSV client — list_modified_since, get_by_id`**
- Now possible: HTTP client for OSV, returning normalized records. No DB writes yet.
- Revert safety: pure client; nobody depends on it.
- Tests: contract tests with `RecordedHTTPClient` against committed OSV fixtures. Live test gated behind `RUN_REAL_HTTP=1`.

**2.5 — `feat: AdvisoryIngester — upsert without embeddings`**
- Now possible: `AdvisoryIngester.run_once(ecosystem="npm")` pulls deltas from OSV, upserts into `advisories` with `embedding = NULL`. Watermark advances. Idempotent on re-run.
- Revert safety: data already ingested stays in the DB (per principle 0.3). The `advisories` table is fine without ingestion happening; downstream code in later phases handles `embedding IS NULL` gracefully.
- Tests: integration test against real Postgres + recorded OSV fixtures, asserts (a) idempotency on second run, (b) watermark advances correctly, (c) malformed advisory goes to a DLQ row instead of crashing.

**2.6 — `feat: bge-m3 embedder with batched inference`**
- Now possible: `Embedder.embed_batch(texts: list[str], batch_size: int = 64) -> list[Vector]`. Async wrapper around the (sync) `sentence-transformers` call via `to_thread`.
- Revert safety: no consumers yet.
- Tests: contract test `test_embed_returns_1024_dim_unit_vectors`. Property test on batch boundary (`batch_size=1`, `=64`, `=65` give identical results modulo batch boundaries).

**2.7 — `feat: ingester writes embeddings; HNSW index becomes useful`**
- Now possible: ingestion now embeds (summary + details) for every advisory. `embedding IS NULL` only for in-flight rows. End of this phase: we can `SELECT * FROM advisories ORDER BY embedding <=> $1 LIMIT 5` and get sensible results.
- Revert safety: advisories ingested with embeddings stay; new ingestions revert to embedding-less. The HNSW index still serves the rows that have embeddings. **No corruption — just split data over time.**
- Tests: integration `test_advisory_search_by_vector_returns_relevant`. Uses 100 real OSV records as a fixture corpus and asserts the embedding nearest-neighbor of a known query lands in the top-5.

End of Phase 2: advisories live in our DB, embedded, queryable. We've built nothing that touches code yet.

---

## 4. Phase 3 — Code corpus

Mirrors Phase 2 but for code. The asymmetry is that code chunks need a chunker (tree-sitter) and we have to handle re-chunking on commit changes.

**3.1 — `migrate: create code_chunks, repo_dependencies tables`**
- Now possible: schema for the code side. Same expand-rules as Phase 2.
- Revert safety: tables drop cleanly via down-migration.
- Tests: migration up/down test extends.

**3.2 — `feat: tree-sitter chunker for JavaScript/TypeScript`**
- Now possible: `CodeChunker.chunk_file(path) -> list[Chunk]` returns function/class/module-level chunks with line spans, symbol names, and the file's import block attached to each chunk.
- Revert safety: pure function; no DB writes yet.
- Tests: ~12 unit tests covering: nested functions, classes, arrow functions, default exports, re-exports, files with no top-level code (e.g. `index.js` with only imports). Property test: `start_line <= end_line` on every emitted chunk.

**3.3 — `feat: chunker writes to code_chunks with content_hash idempotency`**
- Now possible: `CodeChunker.reindex(repo, sha)` walks the worktree, chunks changed files (diffed against last indexed sha), embeds, upserts. Re-running on the same sha is a no-op.
- Revert safety: chunks already written stay. New chunks won't be written until reindex runs again. Retrieval returns whatever's there.
- Tests: integration tests including `test_reindex_twice_is_no_op`, `test_modified_file_replaces_old_chunks_for_that_file_only`, `test_deleted_file_removes_its_chunks`.

**3.4 — `feat: dependency manifest reader for package.json + lockfile`**
- Now possible: `DepManifestReader.read(repo, sha) -> list[Dependency]` produces declared and resolved versions per package.
- Revert safety: pure read; no writes outside the reader's table population.
- Tests: unit tests against fixture `package.json` + `package-lock.json` files covering: dev deps, transitive deps, workspaces, monorepo cases (yarn), lockfile v1 vs v3.

**3.5 — `feat: end-to-end repo indexing CLI`**
- Now possible: `python -m cli.index <repo_url> <sha>` clones the repo, runs the chunker, writes to DB, populates `repo_dependencies`. Used in dev to populate the demo repo. End of this phase: we have indexed code we can query.
- Revert safety: indexed data stays; CLI just becomes unavailable.
- Tests: end-to-end integration test against a tiny fixture repo (committed under `tests/fixtures/repos/tiny/`) asserts row counts.

End of Phase 3: code corpus exists and is queryable by vector. No retrieval API yet.

---

## 5. Phase 4 — Hybrid retrieval

The SQL CTE from LLD §4.3 lands here. This is where the system gets interesting.

**4.1 — `feat: HybridRetriever with vector-only path (lexical disabled)`**
- Now possible: `HybridRetriever.search(repo, sha, query)` returns top-K chunks by vector similarity. FTS path stubbed to return empty.
- Revert safety: stubbed-FTS path is no worse than nothing. Revert removes the retriever; nobody depends on it yet.
- Tests: integration `test_vector_only_path_returns_results`, `test_repo_sha_filter_pushed_down_into_cte` (asserts on `EXPLAIN` plan).

**4.2 — `feat: enable FTS path; full RRF query`**
- Now possible: hybrid retrieval is now actually hybrid. The full LLD §4.3 SQL.
- Revert safety: revert returns to vector-only — strictly worse retrieval but functional. Tests at `4.1` still pass at the reverted commit.
- Tests: the four LLD §4.3 gotcha tests (`test_lexical_match_outranks_distant_vector`, `test_full_outer_join_keeps_vector_only_hits`, etc.).

**4.3 — `feat: BGE cross-encoder reranker`**
- Now possible: `BGEReranker.rerank(query, chunks, top_n)` — top-50 → top-5 cross-encoded. Wraps the sync `CrossEncoder` via `to_thread`.
- Revert safety: revert removes rerank; retrieval still returns top-50 by RRF, just unsorted at the head. End-to-end results worse but valid.
- Tests: contract test `test_reranker_orders_obviously_relevant_first` against a small labeled fixture; perf test asserts < 100ms for 50 pairs on CPU.

**4.4 — `feat: HybridRetriever composes reranker; expose via core API`**
- Now possible: production-grade retrieval call: `retriever.search(..., top_k=50, rerank_to=5)`.
- Revert safety: composition is local; `4.3`'s reranker still callable directly.
- Tests: integration `test_search_with_rerank_improves_top_1_relevance` against a labeled query set.

**4.5 — `feat: SourceProvider — read by file path + line range`**
- Now possible: `SourceProvider.read_lines(file, start, end)` against an indexed repo. Reads from a cloned worktree at `repo_sha`. Used by every node that quotes source.
- Revert safety: pure read.
- Tests: unit tests on line-range edge cases; property test on `read_lines(f, 1, n)` returning exactly `n` lines for a file of length `n`.

**4.6 — `feat: code_search MCP tool surface (no MCP server yet)`**
- Now possible: `code_search` callable shape exists as a Python function with the eventual MCP signature. Used internally; will be exposed over MCP in Phase 7.
- Revert safety: it's a thin wrapper; revert removes the wrapper, callers go to the retriever directly.
- Tests: contract test asserting input/output schemas match the MCP tool signature defined in LLD §6.1.

End of Phase 4: "find code relevant to text" works. No agent, no LLM, no PRs.

---

## 6. Phase 5 — Reachability core (no agent yet)

Per HLD §11: "does the core idea work at all on one real case?" — answered before LangGraph or MCP enter the picture. This is the riskiest phase. If reachability reasoning doesn't work standalone, the rest of the system is pointless.

**5.1 — `feat: LLMClient Protocol + ScriptedLLMClient + RecordedLLMClient`**
- Now possible: type-safe LLM call surface. Tests can use scripted responses; integration tests can use recorded ones. No real API calls anywhere yet.
- Revert safety: nothing depends on it.
- Tests: contract tests for the Protocol — every fake satisfies the same interface (TDD doc §6.2).

**5.2 — `feat: AnthropicLLMClient implementing the Protocol`**
- Now possible: real LLM calls behind the protocol. Cost tracking, prompt caching markers, two-tier routing (`cheap`, `frontier`).
- Revert safety: code that depends on `LLMClient` works against fakes; production usage just becomes impossible until we re-add. **Dev/test continue to work.**
- Tests: contract suite from `5.1` runs against the Anthropic client, gated behind `RUN_REAL_LLM_TESTS=1`. Cost-tracking unit test on the response-parsing layer.

**5.3 — `feat: StructuredCaller — Pydantic response_format with retry-on-validation-failure`**
- Now possible: every LLM call that wants structured output goes through `StructuredCaller.call(..., schema=ReachabilityOutput)`. On validation failure, retry once with the error fed back as user-message context.
- Revert safety: callers can fall back to raw `llm.complete`; brittle but functional. **Coding rule 7.2 fails on the reverted state — this rule isn't yet enforced in CI.**
- Tests: unit tests with `ScriptedLLMClient` covering the retry path explicitly (TDD doc §5.3).

**5.4 — `feat: QuoteMatcher (pure function) + EvidenceQuoteValidator`**
- Now possible: any output with `evidence_quotes` can be validated against a `SourceProvider`. Quote-matching is whitespace-tolerant, identifier-strict.
- Revert safety: the validator is a wrapper; revert removes the validator, leaves callers without grounding checks. **Critical capability is lost on revert** — this is one of the few commits where we'd consider rolling forward instead of back.
- Tests: the full TDD doc §2 walkthrough. Property tests on `quote_matches`. ~20 unit tests including the hallucinated-quote retry path with `ScriptedLLMClient`.

**5.5 — `feat: ast-grep call-site finder for JS/TS`**
- Now possible: `find_call_sites(repo, sha, symbol="_.template") -> list[CallSite]`. Wraps `ast-grep` subprocess with a list-arg invocation (coding rule 10.5). Returns file/line spans with surrounding context.
- Revert safety: revert removes call-site location; callers can fall back to ripgrep but lose AST precision. Documented limitation.
- Tests: integration tests against fixture repos with known call patterns. **Includes the known-false-negative tests** (dynamic dispatch, re-exports) — these tests *expect* the false negative and document the limitation. Per HLD §5.
- Note: this is a place where we explicitly test what *doesn't* work, so the limitation is encoded, not silent.

**5.6 — `feat: reachability prompt + ReachabilityOutput schema`**
- Now possible: `core/agent/prompts/reachability.py` with the system prompt, user template, and Pydantic output schema. Standalone — callable as a function `assess_call_site(advisory, call_site) -> ReachabilityOutput`.
- Revert safety: revert deletes the prompt; the schema goes with it. No silent behavior change.
- Tests: ~5 prompt regression tests using `RecordedLLMClient`. Asserts structural calibration rule (confidence < 0.7 ⇒ verdict = "unsure"). The recorded fixtures are committed in this same commit per principle 0.6.

**5.7 — `feat: per-call-site Assessor with evidence validation hooked in`**
- Now possible: `Assessor.assess(call_site)` does the full loop: prompt → structured output → evidence validation → retry on validation failure → return `CallSiteAssessment` with `evidence_validated: bool`. End of this commit: standalone reachability assessment works against a real LLM.
- Revert safety: revert removes the orchestration but leaves the prompt and validator usable directly.
- Tests: integration test against real LLM (gated) running on 3 hand-picked cases. Recorded variant for per-PR runs.

**5.8 — `feat: standalone CLI — assess one (advisory, repo, file, line)`**
- Now possible: `python -m cli.assess --advisory CVE-X --repo demo --file src/auth.js --line 42` runs the full standalone reachability flow and prints the verdict + evidence. **This is the milestone HLD §11 calls out.** If this doesn't produce useful output on a real case, every later phase is at risk.
- Revert safety: revert removes the CLI. The `Assessor` is still callable from Python.
- Tests: end-to-end integration test against a recorded LLM and a fixture repo. Asserts both `verdict == "reachable"` for a known-vulnerable case and `verdict == "not_reachable"` for a control case.

End of Phase 5: **the riskiest question is answered.** If we shipped nothing else, this is already a useful tool for security engineers running it manually on triage.

---

## 7. Phase 6 — LangGraph orchestration

Now we wrap the standalone reachability into the full agent. The state object, the nodes, the reflection loop.

**6.1 — `feat: AgentState Pydantic model with extra=forbid`**
- Now possible: typed state to thread through nodes. All fields from LLD §5.1.
- Revert safety: pure type, no consumers.
- Tests: round-trip unit tests; `test_unknown_field_rejected`.

**6.2 — `feat: triage nodes — classify, extract_symbols, match_dependency`**
- Now possible: the three cheap-tier nodes that kill 95% of advisories early. Each implemented as a function `(state, deps) -> state`. No graph yet.
- Revert safety: nodes are independent; revert removes whichever one was last added. The other two still callable.
- Tests: `ScriptedLLMClient` unit tests per node + one integration test running them in sequence on a fixture advisory.

**6.3 — `feat: locate stage — HyDE (gated off), retrieval, rerank, ast-grep, triage_call_sites`**
- Now possible: locate-stage nodes wired together. HyDE is behind a feature flag (`enable_hyde=False` default per LLD §10).
- Revert safety: revert peels back to triage nodes only. HyDE flag means the HyDE node never executes in production at this point — landing it disabled is itself the "safe to revert" mechanism (principle 0.5).
- Tests: per-node tests + chain-level integration.

**6.4 — `feat: assess_reachability node with bounded async fan-out`**
- Now possible: per-call-site fan-out using `asyncio.Semaphore(4)`, per-task try/except, per-call deadline. Reuses `Assessor` from `5.7`.
- Revert safety: revert removes the fan-out; the per-site assessor is still directly callable.
- Tests: TDD doc §5.3 tests, including timeout-with-FakeClock unit tests and the "one task fails, others complete" test.

**6.5 — `feat: relevance_critique node + LoopTermination value object`**
- Now possible: the Self-RAG critique loop, with the explicit termination predicate from TDD doc §0.3 row 4 (iteration cap **and** retrieval-unchanged check).
- Revert safety: revert removes the critique; the agent skips reflection and goes straight to decide. Quality drops; correctness preserved.
- Tests: the four loop-termination tests from TDD doc §3.4, including the property test for "always terminates."

**6.6 — `feat: decide_action node with semver-aware version selection`**
- Now possible: given a verdict and a vulnerable version range, pick the minimal patched version that doesn't cross a major boundary. No PR drafting yet.
- Revert safety: pure logic; revert removes the decision step. End of run produces `final_verdict` but no `pr_spec`.
- Tests: ~15 unit tests on semver edge cases; property tests on monotonicity (the chosen version is always `>= current` and `>= patched_introduced`).

**6.7 — `feat: build_graph wires nodes into LangGraph; agent runs end-to-end on scripted LLM`**
- Now possible: `run_agent(advisory_id, repo_id)` walks the full graph from `classify_advisory` to `decide_action`. **End of this commit: the agent works as an agent — no PRs, no MCP yet, but the orchestration is complete.**
- Revert safety: revert removes the graph; individual nodes still callable. No partial-graph state — either the graph runs fully or it's not present.
- Tests: golden-replay integration tests with `RecordedLLMClient`. Three scenarios from TDD doc §7: clean reachable, clean not-reachable, dependency not present.

End of Phase 6: full agent pipeline up to `decide_action`, no external side effects.

---

## 8. Phase 7 — MCP + capability isolation

The agent's tools become MCP tools, and the structural security properties get tested.

**7.1 — `feat: MCP server skeleton; expose advisory_query and code_read`**
- Now possible: read-only tools served over MCP. The agent doesn't use them yet; this is the surface.
- Revert safety: revert removes the server; agent code paths still work via direct function calls.
- Tests: integration test using the MCP Python SDK as client against the in-process server.

**7.2 — `feat: expose remaining read-only tools — code_search, dep_manifest_read, dep_registry_query, git_blame`**
- Now possible: every read-only LLD §6.1 tool is exposed.
- Revert safety: per-tool granularity; revert removes the most-recently-added tool.
- Tests: contract test per tool — input validates, output validates, error cases produce typed errors.

**7.3 — `feat: CapabilityGraph as first-class object; permission checks on every dispatch`**
- Now possible: the design change from TDD doc §0.3 row 5. `CapabilityGraph.from_permissions(TOOL_PERMISSIONS)` is a real object with `paths_to(tool)`, `nodes_with_permission(tool)`. Server's `dispatch()` enforces it.
- Revert safety: revert removes enforcement but keeps the dict-style permissions. The capability isolation property fails on the reverted state — **this is one of the few commits where revert moves us out of compliance with the threat model.** Documented in commit body.
- Tests: TDD doc §3.3 tests including the `test_no_path_from_advisory_text_to_side_effecting_tool` structural test.

**7.4 — `feat: agent nodes call tools through MCP, not direct function calls`**
- Now possible: the agent now goes through the MCP transport for every tool call. Capability isolation is enforced *in transit*, not just at the import level.
- Revert safety: revert returns the agent to direct function calls — capability dispatch stops being checked, but the import-level discipline still holds. Defense in depth means revert reduces depth without breaking it.
- Tests: golden-replay tests from `6.7` re-run through MCP transport; no expected behavior change.

**7.5 — `feat: pr_create stub tool — no GitHub API yet, returns canned URL`**
- Now possible: `draft_pr` node can call `pr_create` and get a fake response. Lets us run the full graph including the action layer without yet integrating with GitHub.
- Revert safety: revert returns to "no PR action exists." The graph terminates after `decide_action`.
- Tests: golden-replay scenario with `expected.pr_opened = True` now passes against the stub.

End of Phase 7: capability isolation is enforced and tested; the agent talks to its tools through MCP; PR creation is stubbed.

---

## 9. Phase 8 — Action layer

Real GitHub integration, preflight check, rate limits.

**8.1 — `feat: GitHub PAT-based client with retry and rate-limit handling`**
- Now possible: `GitHubClient` for PR creation, branch creation, file commit. Read-only operations work.
- Revert safety: nothing depends on it yet.
- Tests: contract tests against recorded GitHub fixtures. Live test gated.

**8.2 — `feat: PRDrafter — assemble PR body with citations, advisory link, evidence`**
- Now possible: `PRDrafter.draft(state) -> PRSpec` produces the structured PR body from the LLD §10 outline. Pure function — no GitHub call yet.
- Revert safety: pure function; output goes nowhere until 8.4.
- Tests: snapshot tests for the PR markdown; golden-fixture comparison.

**8.3 — `feat: preflight — npm install --package-lock-only resolves cleanly`**
- Now possible: subprocess invocation (list-arg, no shell) of `npm install --package-lock-only` in a temp dir against the proposed manifest. Returns a structured `PreflightResult`.
- Revert safety: revert removes the preflight check; PR drafting proceeds without resolution validation. Quality regression, not correctness.
- Tests: integration test using a real `npm` available on CI runners. Includes a deliberately-broken manifest to assert failure detection.

**8.4 — `feat: pr_create tool implementation; rate limits enforced at the tool boundary`**
- Now possible: real PRs against the configured target repo. Rate limits per LLD §6.3 enforced at the tool-handler layer (max-PRs-per-day, one-PR-per-advisory, max-diff-lines). Stub tool from `7.5` removed.
- Revert safety: revert restores the stub tool; system runs without real PR creation. Demo-mode still works. **Reverting after a real PR has been opened doesn't unwind the PR** — principle 0.3 in action.
- Tests: contract tests against a sandbox GitHub repo. Rate-limit tests use a `FakeClock` to advance time across the daily window.

**8.5 — `feat: idempotency on POST /v1/runs and pr_create`**
- Now possible: same idempotency key returns the same result. The eval harness can re-run cases without dup PRs.
- Revert safety: revert removes idempotency — re-running a case might double up. Annoying but not corrupting (unique constraints catch most).
- Tests: unit tests on the key-store + integration test asserting second call returns the cached response.

**8.6 — `feat: end-to-end live demo on demo target repo (replay mode)`**
- Now possible: `python -m cli.replay --advisory CVE-X --repo demo` runs the full pipeline and opens a real PR. **This is the demo path described in HLD §0 (Demo Scenario), end-to-end.**
- Revert safety: revert removes the CLI entry point only; the underlying pipeline still works via Python API.
- Tests: end-to-end integration test against the sandbox repo, recorded LLM responses.

End of Phase 8: the system as described in HLD §0 actually works. We could ship.

---

## 10. Phase 9 — Optimization (gated, measurable)

Per HLD §11 and TDD doc §8: every optimization commits a measurable delta or doesn't ship. This phase requires the eval harness from Phase 10 — which is why I considered ordering them swapped. But Phase 10's eval harness depends on having something stable to evaluate, and Phase 8 gives us that. So Phase 9 lands first, with manual measurement, and Phase 10 codifies the measurement. **Each Phase 9 commit ends with a "delta" line in the body.**

**9.1 — `feat: HyDE generator behind enable_hyde flag`**
- Now possible: `HyDEGenerator` exists but flag is still `False`. Code path doesn't execute in production. Per principle 0.5.
- Revert safety: trivial — flag-off means no behavior.
- Tests: unit tests on the generator; the existing flag-off retrieval tests continue to pass.

**9.2 — `chore: enable HyDE on dev split; record retrieval-recall delta`**
- Now possible: HyDE on for evaluation runs only. Manual measurement: did `context_recall` improve?
- Revert safety: flag flip; revert flips it back off.
- Tests: an A/B integration test running the same query set with HyDE on and off, asserting the delta direction. **If the delta is < 5 points, the next commit deletes HyDE.** Measured, not assumed.

**9.3 — `feat: prompt caching markers on shared prefix in reachability calls` OR `chore: remove HyDE — measured delta < 5 points`**
- One of these two ships, depending on `9.2` measurement. The commit plan acknowledges the fork rather than pretending we know the answer.
- Now possible (caching variant): per-call-site fan-out cost ~50% lower (LLD §5.6). Measured against the prior commit on the same fixture.
- Revert safety: caching is transparent to behavior — only cost changes. Revert restores higher cost.
- Tests: integration test asserting cost-per-fanout drops by > 30% on a fixture.

**9.4 — `perf: two-tier routing — verify cheap-tier nodes never hit frontier`**
- Now possible: a CI check that `tier="cheap"` is passed for classify/extract/HyDE/critique/decide nodes. Coding rule 7.1 enforcement landed in CI.
- Revert safety: removes the lint check. Coding rule 7.1 still applies in review but no longer mechanically enforced.
- Tests: a custom ruff plugin or AST check; unit-tested.

**9.5 — `feat: verdict_cache — memoize on (advisory, dep_manifest_hash, vulnerable_files_hash)`**
- Now possible: memoization per LLD §2.2 / HLD §9. Cache hit returns full prior result without re-running.
- Revert safety: revert removes the cache; every run re-executes from scratch. Slower, not broken.
- Tests: integration test with a cache hit and a cache miss; eviction-on-expiry test using `FakeClock`.

**9.6 — `feat: LangSmith tracing — every node, attributes per coding rule 9.3`**
- Now possible: end-to-end traces in LangSmith with the standardized attributes. Replaces the local-only structlog spans for agent observability.
- Revert safety: revert returns to structlog-only; traces stop appearing in LangSmith but logs still produced.
- Tests: integration test that emits a known trace ID and asserts it round-trips through the LangSmith client (gated on API key).

End of Phase 9: every optimization that landed is justified by a measured delta, recorded in the commit body. Anything that didn't measure up was deleted, not kept "in case."

---

## 11. Phase 10 — Eval harness + CI integration

The statistical layer. The badge.

**10.1 — `feat: eval_cases table + YAML loader + train/dev/test split enforcement`**
- Now possible: 30+ eval cases loaded from `eval/fixtures/`, with split membership locked. Rule "no test outside `eval/test_split/` may load the test split" enforced in `conftest.py` (TDD doc §8.4).
- Revert safety: revert removes the split-leak check but the data is still there. Risk of leakage in the *reverted* state.
- Tests: a meta-test that asserts the split-leak guard is wired.

**10.2 — `feat: eval harness — runs cases, computes per-case rows, persists results`**
- Now possible: `python -m eval.harness --split dev` runs all dev-split cases against the live system, writes per-case rows to a results table.
- Revert safety: revert removes the runner; cases stay in DB.
- Tests: smoke test running 3 fixture cases with a `RecordedLLMClient`.

**10.3 — `feat: metrics — F1, precision, recall with bootstrap confidence intervals`**
- Now possible: `eval.metrics.compute(results) -> EvalReport` with bootstrapped 95% CIs. Outputs confusion matrix and Pareto data.
- Revert safety: pure function; revert removes the analysis but results are still queryable.
- Tests: ~10 unit tests on edge cases (all-correct, all-wrong, single class).

**10.4 — `feat: CI eval job + statistical regression check`**
- Now possible: nightly job runs eval on dev split, post-merge job runs on test split. Significance gate (`p < 0.05 AND |Δ| > 0.02`) blocks main on real regression. (TDD doc §8.2.)
- Revert safety: revert removes the gate; eval still runs but doesn't block. Significant regression could land silently — a real downgrade.
- Tests: a synthetic regression test (manually-bad eval result) asserts the gate fires.

**10.5 — `feat: README badge — F1 with CI, last-run cost, Pareto chart`**
- Now possible: README shows live F1 [low, high], median cost per case. Pareto chart updates on every eval run.
- Revert safety: revert removes the badge; numbers still queryable from the dashboard.
- Tests: snapshot test on the badge SVG generation.

End of Phase 10: numbers are honest, regressions are caught statistically, the README earns its claims.

---

## 12. Phase 11 — Adversarial hardening

The threat model becomes a test corpus.

**11.1 — `feat: adversarial corpus loader; structure for attack fixtures`**
- Now possible: `tests/adversarial/corpus/*.yaml` loaded into typed `Attack` objects. No attacks committed yet — just the loader.
- Revert safety: pure infrastructure.
- Tests: loader unit tests.

**11.2 — `test: ten initial prompt-injection attacks (instruction override, role hijack, etc.)`**
- Now possible: ten attacks committed; `pytest tests/adversarial/` runs them all. Per TDD doc §5.6.
- Revert safety: revert removes the attacks; isolation properties still hold (they're enforced by `7.3`'s capability graph), we just stop testing them adversarially. Risk: a future regression slips through.
- Tests: each attack is a test, with assertions on the four §0.2 invariants.

**11.3 — `test: ten more attacks — evidence forgery, polyglot, tool-call exfiltration`**
- Now possible: corpus at 20. The full v1 set described in TDD doc §5.6.
- Revert safety: same as `11.2`.
- Tests: ten more.

**11.4 — `docs: THREATS.md — threat model, mitigations, residual risk`**
- Now possible: the security narrative is written down. Every mitigation links to the test that enforces it.
- Revert safety: docs only. Revert removes the narrative; the tests still enforce.
- Tests: a docs-link-check ensures every test referenced in THREATS.md exists.

End of Phase 11: the adversarial story is told and tested.

---

## 13. Phase 12 — Demo target + cutover

The portfolio piece becomes presentable.

**12.1 — `feat: demo target app — Express + Postgres notes app, ~15 deps pinned to ~18mo old`**
- Now possible: a real, small, working app with deliberately old dependencies for natural CVE matches. Per HLD demo target.
- Revert safety: separate repo / submodule; revert here just means we don't use it.
- Tests: the app's own tests.

**12.2 — `feat: shadow mode — run pipeline, write to DB, no PRs`**
- Now possible: cron runs the live pipeline against the demo repo, writes runs and assessments, *does not* create PRs. (HLD §12 phase 1 of cutover.)
- Revert safety: revert turns shadow off; nothing was being affected externally anyway.
- Tests: integration test asserting `pr_url IS NULL` even when verdict is `reachable` in shadow mode.

**12.3 — `chore: enable real PR creation on demo repo with confidence-gated triage`**
- Now possible: HLD §12 phase 2 — auto-PR with mandatory human approval. PRs get the `needs-human-review` label.
- Revert safety: revert returns to shadow. Open PRs stay; nothing unwinds (principle 0.3).
- Tests: an integration test asserts the label is applied.

**12.4 — `docs: README narrative, demo video link, architecture diagram`**
- Now possible: the project is presentable. End of v1.
- Revert safety: docs only.
- Tests: the link checker runs in CI.

---

## 14. Cross-cutting — the always-green discipline

Properties that hold across every phase, enforced by the rules above.

**14.1 — At any commit on `main`, `make test-fast` passes.** This is the atomicity check. CI runs it on every push; a red `main` is a five-alarm fire (page someone, revert immediately).

**14.2 — At any commit on `main`, `alembic upgrade head && alembic downgrade -1` is clean.** Migration reversibility test. Runs on every PR that touches `migrations/`.

**14.3 — At any commit on `main`, the structural security tests pass.** `tests/unit/test_capability_graph.py` and `tests/adversarial/` are part of the per-PR suite once they exist (Phase 7 onward). After Phase 7, no commit can land that violates capability isolation.

**14.4 — Every commit on `main` is reachable from the merge graph by exactly one merge commit.** Squash-merge enforced. No merge bubbles. `git log --oneline main` reads as a story.

**14.5 — When a commit on `main` turns out to be wrong, we revert by `git revert`, not by hot-fix-on-top.** The revert produces a new commit on `main` that undoes the bad one. The bad commit stays in history (so we learn from it); the working tree is healthy.

---

## 15. The revert playbook

Three failure modes, three responses. This is what an on-call engineer reaches for.

**15.1 — A feature flag flip caused a regression.**
Action: revert the flag-flip commit. Code paths revert to the pre-flip behavior. Recovery time: one revert + redeploy. Per principle 0.5, this is the cheapest recovery shape and is why flag-flips are their own commits.

**15.2 — A behavior change caused a regression and there's no flag.**
Action: revert the behavior-change commit. Per principle 0.6, prompt changes also revert atomically with their golden recordings. Per principle 0.7, refactor commits are behavior-preserving — so reverting a refactor that *did* change behavior is itself a sign the refactor was lying.

**15.3 — A migration shipped and now we want to roll back the code that depends on it.**
Action: revert the *consuming* commits, not the migration. Per principle 0.2, migrations are expand-then-contract — the schema change is forward-compatible with the prior code. Reverting the consuming code lands on a state where the new column is unused but present. The migration can stay, and we roll forward later. **Never roll back a migration that has run in production with data.**

---

## 16. The three things this commit plan is really about

1. **Every commit on main is a coherent state of the system, not a checkpoint in a developer's brain.** The discipline is not "commit often" — it's "commit *atomically*." Each commit gains a capability or refines one; reverting peels back exactly that capability and nothing else.

2. **Phases are capability-shaped, not time-shaped.** Phase 5 ends when the standalone reachability tool works on a real case. Phase 8 ends when a real PR opens. Calendar time slips; capabilities don't ship until they're done. The plan organizes work around what's true after the work, not when the work is supposed to be true.

3. **The riskiest question is asked first.** Phase 5 (standalone reachability) is the entire value proposition tested in isolation, before LangGraph, MCP, or PR creation enter the picture. If the answer is "the model can't reliably tell reachable from non-reachable," we know on commit ~25, not commit ~60. Every later phase compounds on that answer; getting it wrong late is catastrophic, getting it wrong early is just a project pivot.
