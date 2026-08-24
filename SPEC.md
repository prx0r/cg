# COGYMKERNEL — Specification & Plan v1.0

**Status:** SPEC (pre-implementation) · 2026-08-24 · supersedes nothing; imports everything worth keeping from `/root/cogym/canonical`.

---

## 0. Mission

> A standalone, async-first, technically optimised agentic evolution laboratory:
> evolve decision policies in deterministic replayable worlds under hard
> quality gates, with an experience graph as derived memory.

**Non-goals:** real-money trading, LLM weight training, dashboards-first, a
prompt marketplace, multi-tenant SaaS. One lab, one operator, N workers.

## 1. Evidence base — what the current build taught us (measured, not guessed)

| Finding | Measurement | Consequence |
|---|---|---|
| Compute is NOT the bottleneck | toy episodes: **177k eps/min** serial Python | "Rewrite in Rust for speed" is unjustified |
| Hydra writes are round-trip-bound | ~10ms serial; naive threads made it **165ms** (no connection pooling) | persistent pooled async client + batching is the win |
| Node birth costs 4 round trips | match → pair-create → scratch-del → set | batch buffer / write-behind; capability probe to upgrade when image supports MERGE+SET |
| Association-node schema exists because of image limitations | probed 2026-08-24 | client must **capability-probe at startup** and auto-select write strategy |
| Kanban via CLI subprocess | ~200-500ms per call, poll loops | built-in scheduler default; external boards become adapters |
| LLM calls re-paid across runs | no response cache | content-addressed response cache = free replays |
| §56 rebuild works but needs a canonical replayer per artifact class | replay_all.py | event-sourcing native from day one |
| Scaffolded worlds work end-to-end | spawn→run→remove proven | formalize as **worldpack distribution format** |

## 2. Architecture Decision Records

### ADR-1 — Language: async Python core, Rust never required
Python 3.12+, asyncio + uvloop, structured concurrency (`TaskGroup`).
Rationale: measured bottleneck is IO/latency; iteration speed matters because
agents author recipes/worlds here; pydantic-core and orjson give
Rust-accelerated hot paths without writing Rust. Compiled extensions
(blake3 hashing) only where profiled. Loom/HydraDB validate Rust workspaces,
but both also prove the maintenance cost.

### ADR-2 — Async everywhere, structured concurrency
Runner, executors, experience client, orchestrator: all `async def`.
Episodes run as tasks with cancellation safety; suite layers fan out episodes
concurrently (bounded semaphore). Target ≥500 eps/min on deterministic worlds
vs ~1,800 peak today serially — parallel *episodes*, not micro-threads.

### ADR-3 — Experience client: pooled, batched, capability-probed
- One `httpx.AsyncClient` per process (keep-alive; kills the 16× regression).
- **Write-behind buffer**: upserts queue locally, flush ≤64 ops per request
  round trip; durability boundary stays the local receipt (JSONL), Hydra flush
  is best-effort background.
- Startup capability probe (MERGE? UNWIND? MATCH-CREATE?) selects write
  strategy; association-node fallback preserved.
- Cursor pagination loop when server offers `next_cursor`.

### ADR-4 — Built-in orchestrator, boards as adapters
Default scheduler = embedded SQLite queue (WAL mode) + asyncio workers:
standalone, zero external deps, same atomic-claim semantics we proved.
Hermes kanban, Kubernetes Jobs, or plain process pools plug in via one
protocol (`Scheduler`). Receipts idempotent by job_id (unchanged).

### ADR-5 — Content-addressed model-response cache
Key = hash(model, messages, temperature, seed, tools). Hits return recorded
responses ⇒ experiment reruns cost zero tokens and are byte-reproducible.
Cache lives next to receipts; opt-out per run (freshness checks).

### ADR-6 — Event sourcing native
Every episode appends an event stream (JSONL primary, Parquet snapshots for
analytics). Leaderboards, graphs, reports are pure projections. The §56 test
(delete every projection → rebuild → byte-equal) is a CI gate, not a ritual.

### ADR-7 — Worldpack distribution format
A world = directory: `manifest.json` + `world.py` + `policies.py` +
`experience.py` + tests + README/AGENTS.md (today's scaffold output,
formalized). Install via path/zip/git URL; kernel discovers entrypoints;
version-pinned scenario hashes guarantee cross-machine comparability.

### ADR-8 — Sealed evaluation from day one
Subject plane runs in a subprocess with no oracle imports; evaluator owns
labels/gates. Escalation path: containers. (factminer §51 finally implemented.)

### ADR-9 — Quality-diversity archive first-class
MAP-Elites grid with pluggable behavior descriptors (style-family × cost-bucket
today; arbitrary descriptor functions tomorrow). Elites-per-cell is the default
archive policy; global-best ranking remains available but secondary.

### ADR-10 — Credential proxy pattern (from Loom, patterns not code)
One local proxy holds provider keys; subject executors receive capability
handles (`TINY_JSON`, `FAST_REASONER`, …), never raw keys. Enables key rotation,
quota accounting, and the cost-accounting doctrine (cash vs normalized).

## 3. Module layout

```
cogymkernel/
├── pyproject.toml                # py3.12+, httpx, pydantic, orjson, blake3, typer
├── cogym_kernel/
│   ├── kernel/                   # ids(blake3), contracts(pydantic frozen), runner(async)
│   ├── executors/                # deterministic · model(cached) · search · browser · replay-tape
│   ├── eval/                     # suites(dev/val/secret+halving) · gates · lexicographic · stats(Wilson/bootstrap)
│   ├── evo/                      # recipes registry · style library · typed search spaces · QD archive
│   ├── experience/               # async hydra client(capability probe, batching) · projection · rebuild
│   ├── school/                   # packs · induction metrics/certs
│   ├── memory/                   # subject-memory protocol (null/sqlite/hydra-view)
│   ├── orchestration/            # embedded scheduler · worker pool · hermes adapter
│   ├── science/                  # experiment cycle · findings schema · three-tier verify
│   └── cli.py                    # status · worlds · world-new · evolve · cycle · replay · verify
├── worldpacks/                   # shipped examples: toy.search_game (+trading/factcheck adapters later)
├── migrations/from_canonical.py  # import legacy receipts/graphs
└── docs/                         # SPEC.md(this) · GUIDE.md(CANONICAL successor) · METHODS.md
```

## 4. What imports verbatim vs gets rewritten

| From canonical | Disposition |
|---|---|
| Gate/lexicographic/paired-bootstrap logic, Wilson stats | port near-verbatim (proven, tested) |
| Recipe + style registries, 14 recipes, 33 styles | port as data/modules; typed spaces added |
| Scenario algebra Σ, fork ids, golden fixtures | port; becomes the typed spec |
| Association-node projection + capability probe | rewrite (async, batching) preserving schema |
| Kanban worker/cycle/verify logic | rewrite onto embedded scheduler; verification tiers unchanged |
| scaffold generator | rewritten as `worldpack init` |
| v1 harness internals, scalar fitness | left behind (doctrine rejects) |

## 5. Performance targets (CI-enforced)

| Metric | Current | Kernel target |
|---|---|---|
| Deterministic episode throughput | ~1,800/min serial | ≥5,000/min (8 workers) |
| Hydra upsert p50 | 10–165ms | ≤3ms amortized (batched, pooled) |
| Experiment rerun cost w/ cache | full price | ~$0 (cache hits) |
| CLI cold start | ~600ms (imports) | <200ms (lazy modules) |
| Rebuild test | manual script | CI gate, byte-equal |

## 6. Milestones

- **M0 skeleton**: pyproject, kernel contracts, ids, runner + determinism tests.
- **M1 evaluation**: suites/gates/comparator/stats + golden fixtures.
- **M2 experience**: async client + probe + batching + §56 CI gate.
- **M3 evolution**: recipes/styles/QD archive over typed genomes.
- **M4 orchestration**: embedded scheduler + worker pool; hermes adapter.
- **M5 science**: cycle + findings v2 + three-tier verify; worldpack init;
  migration importer; docs(GUIDE/METHODS/REPRODUCE parity).

Definition of done mirrors factminer §65 + REPRODUCE parity, enforced in CI.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Hydra image drift breaks write strategies | startup capability probe pins strategy; probe battery is a test |
| Provider nondeterminism leaks into "replay" | cache keys include seed/temp; uncached runs flagged in receipts |
| Embedded scheduler scope creep | scheduler protocol stays ≤5 methods; complexity lives in adapters |
| Agent-authored worlds unsafe | worldpacks execute in sealed subprocess; no oracle imports possible |
| Two-agent repo conflicts during build | cogymkernel is fresh root project; legacy stays read-only reference |

## 8. Immediate next step (on approval)

M0 skeleton in `/root/cogymkernel`: pyproject + `kernel/{ids,contracts,runner}.py`
+ determinism property tests, then M1–M2 in order — evaluation and the Hydra
client are where the measured wins live.


## 9. Vision integrations (2026-08-24 — all six adopted)

### 9.1 The Proof Primitive — CapabilityClaim schema v1
Every verified run compiles to a content-addressed **CapabilityClaim**:
re-runnable by any third party; if their receipt hashes differ, the claim is
refuted. Determinism becomes trust infrastructure for agent-to-agent
communication. Schema: `claims/schema.v1.json` (see §9.7). Kernel CLI:
`cogym claim create <cycle_dir>` and `cogym claim verify <claim.json>`.

### 9.2 MCP server — "easy for LLMs to call" by construction
The kernel exposes tools over MCP: `run_episode`, `evaluate_candidate`,
`query_experience`, `propose_mutation`, `get_leaderboard`, `fork_decision`,
`submit_candidate`. Any MCP client (Claude, hermes, …) operates the lab
natively. Thin layer over the CLI surface; milestone M4.

### 9.3 Evolution engine as a callable loop
`evolve.step(objective, budget)` exposes the population/gates/archive loop as
a tool; the calling LLM acts as mutation operator between steps (AlphaEvolve/
OpenEvolve pattern), with our recipes as deterministic fallback mutators.
Recipe registry stays the fallback so evolution never stalls on LLM creativity.

### 9.4 Hidden-suite challenge server
Secret splits + sealed evaluator exposed as `submit(candidate) → score only`.
Fresh entropy secrets, no label visibility, three-tier verification attached.
Enables public cognition benchmarks immune to contamination.

### 9.5 Counterfactual fork explorer
`fork_decision(dp_record, change={...})` replays any logged decision with
exactly one changed variable (cognition policy, register, availability).
Self-knowledge tool for agents; implements the thesis fork-A/B/C table.

### 9.6 Pack marketplace seed
Certified Packs (§school) publish as claims; capability deltas on hidden
suites are their certificates. Deferred product; §9.1 claim schema is its
foundation.

## 10. Community sharing site

`website/` in this repo: static, no build step, deployable to Cloudflare Pages.
Renders an index of published CapabilityClaims + worldpack manifests +
leaderboards from JSON files in `website/data/`. Publishing flow: run locally →
`cogym claim create` → commit JSON or POST to a claims repo. No server, no
database: **the claims are the API.**

## 11. Updated milestones

- M4 gains: MCP server (`mcp/server.py`) + claim create/verify CLI.
- M5 gains: website/ deployment + worldpack registry index.
- New **M6 community**: claims directory service (static-first; optional CF
  Pages Functions for submission), signed claims, leaderboard aggregation.
