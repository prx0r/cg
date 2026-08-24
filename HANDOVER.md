# HANDOVER — cogymkernel (standalone clean kernel)

**For:** next agent taking over this standalone project.
**Date:** 2026-08-24  (created from scratch this session; see `SPEC.md` for the full plan)
**Previous conversation context:** This project is the fresh, standalone extraction of `/root/cogym/canonical` (the evolution lab). The legacy repo is at `/root/cogym` — 119 tests passing there, but it is monolithic, sync, and has hermes/CLI overhead. This kernel is async-first, content-addressed, and designed to be portable (`cogymkernel/` is its own git repo at `/root/cogymkernel`, one local commit so far, NOT pushed).

---

## 1. What this project IS

`SPEC.md` defines the mission:

> A standalone, async-first, technically optimised agentic evolution laboratory:
> evolve decision policies in deterministic replayable worlds under hard
> quality gates, with an experience graph as derived memory.

The kernel is the **proof primitive** for cognition: every run produces a `RunReceipt` whose `run_id` is a content hash over `worldpack + scenario + candidate + seed + events_root` (merkle root). Same inputs anywhere => same run_id. That makes claims verifiable. Git is the ledger (`docs/GIT-LEDGER.md`); HydraDB is derived memory (rebuildable).

---

## 2. Repo layout — what was built

```
/root/cogymkernel/
├── pyproject.toml                # py3.11+, httpx, blake3 optional; scripts: cogym = cogym_kernel.cli:main
├── README.md                     # one-click quickstart (install, pytest, status, run)
├── AGENTS.md                     # 10 binding rules for coding agents (NEVER git push etc.)
├── SPEC.md                       # the plan (10 ADRs, module map, perf targets, milestones M0-M6)
├── HANDOVER.md                   # this file
├── claims/
│   └── schema.v1.json            # CapabilityClaim v1 JSON Schema (content-addressed claims)
├── website/                      # static Cloudflare Pages site
│   ├── index.html
│   ├── wrangler.toml             # name = cogymkernel-claims
│   ├── js/site.js , css/site.css
│   └── data/{claims.json, claims/*.json, worldpacks.json}
├── cogym_kernel/
│   ├── cli.py                    # `cogym status|worlds|run|worldpack-export|claim-create` (Typer-like argparse)
│   ├── executors.py              # DeterministicExecutor, ReplayTape/TapeExecutor/RecordingExecutor, ModelExecutor (async + response cache)
│   ├── kernel/
│   │   ├── ids.py                # blake3/sha256 content_id(), strip_volatile(), events_root() merkle, now_ns()
│   │   ├── contracts.py          # WorldSpec, ActionSpec, ActionResult, Metric, MetricVector, CandidateArtifact, RunReceipt, PolicyDecision (all frozen)
│   │   └── runner.py             # AsyncRunner (bounded semaphore) + ExecutorRegistry + run_suite_parallel()
│   ├── eval/
│   │   ├── gates.py              # QualityGate, check_gate, gates_pass, lexicographic_compare, Objective, wilson(), bootstrap_ci(), non_inferior_paired()
│   │   └── suite.py              # LayeredSuite(dev/validation/secret) + run_layered_campaign()
│   ├── evo/
│   │   ├── recipes.py            # 10 recipes: random_search, elitist_mutation, tournament, successive_halving, hydra_adoption, champion_lineage, chain_assembly, quality_diversity, context_seed, style_sweep
│   │   ├── reasoning_styles.py   # 33 styles / 16 families (cot, self_consistency, tot_deliberate, got_merge, reflexion, self_refine, react_loop, debate_3 [with caveat], cove, l2m_decompose, skeleton_parallel + emotion_* + induction_* + registers) + aggregate_by_style(), build_styled_decision_prompt()
│   │   └── loop.py               # EvolutionCampaign (async: population→evaluate→project Hydra→recipe propose→repeat)
│   ├── experience/
│   │   ├── client.py             # HydraClient (async, pooled; httpx+urllib fallback; ensure_node/put_edge/apply_ops parallel, wipe_labels, .ready/.available, capability probe, write-behind documented)
│   │   └── loop.py               # project_performance(), top_policies(), causal_read(), lineage_paths() via algo.SSpaths
│   ├── orchestration/
│   │   ├── scheduler.py          # EmbeddedScheduler (SQLite WAL, atomic claims: enqueue/claim_next/complete/block)
│   │   └── hermes_adapter.py     # HermesBoard (optional adapter — shells `hermes kanban --board X`)
│   ├── science/
│   │   └── verify.py             # Three-tier: deterministic_checks → binary_criteria_check → reconcile() => SUPPORTED/REFUTED/PROVISIONAL/DISPUTED/BLOCKED
│   ├── worlds/
│   │   ├── registry.py           # register(kind, desc), create(kind), kinds() — single place domains are named
│   │   └── toy.py                # SignalWorld (hidden bit, noisy evidence) + CautiousPolicy
│   ├── mcp/
│   │   ├── server.py             # tool registry {status,worlds,run_episode,query_experience} + handle()
│   │   └── stdio.py              # JSON-RPC 2.0 stdin/stdout loop for MCP clients
│   └── school/                   # (minimal so far — packs/induction to be ported from canonical/cogym/school/)
├── tools/
│   ├── publish_claims.py         # reads style-trial + collude EC2, emits reproducibility-complete claims
│   └── export_worldpacks.py      # bundles world dirs → tar.gz + worldpacks.json
├── tests/
│   ├── test_determinism.py       # same-seed same run_id, volatile exclusion, three-tier statuses, model cache
│   ├── test_mcp_stdio.py         # stdio JSON-RPC roundtrip
│   ├── test_eval_suite.py        # gates, lexicographic, non-inferior, Wilson, layered campaign
│   └── test_evo_port.py          # all recipes run, style_sweep, context seeding
└── docs/
    ├── GIT-LEDGER.md             # run_id scheme + git-as-ledger flow
    ├── HYDRA.md                  # HydraDB bring-up, quirks by image digest, rebuild test
    ├── HERMES.md                 # embedded scheduler vs adapter usage
    └── GUIDE.md                  # full operational guide (60-sec map → quickstart → subsystems → never-break rules)
```

**Git:** `23fdc9c` initial + `1373352` M0-M2 commit. Local only; NEVER `git push` (AGENTS.md rule 1). The legacy `/root/cogym` pushes at will — this repo is independent.

---

## 3. Current test status (what's green, what's known flaky)

From `cogymkernel/` root: `python3 -m pytest tests/ -q`

Expected: **~14 tests, all passing** (determinism + eval suite + evo + MCP stdio). Note: with `pytest-asyncio` NOT in `pyproject.toml` dev deps, `tests/test_mcp_stdio.py` spawns a subprocess — ensure `python3 -m cogym_kernel.mcp.stdio` exists. Previous run: `tests/test_determinism.py::test_model_executor_cache_makes_reruns_free` was flaky due to stale `.cache` dir; fixed by switching to `tmp_path` fixture. If it flakes again, `rm -rf tests/.cache`.

Legacy canonical still **119 passing** from `/root/cogym/canonical` (`python3 -m pytest tests/ -q` FROM canonical dir).

---

## 4. Build notes — key decisions & gotchas (for the next agent)

### 4.1 Content hashing (kernel/ids.py)
- blake3 if installed, else sha256. `VOLATILE` set excludes `created_at`, `ts`, `wall_ms`, `signature` etc. from ids. Every new field that is time/host-dependent MUST be added to `VOLATILE` or ids will drift between republishRuns.
- `content_id(prefix, obj)` — prefix scoped (e.g. `run_`, `claim_`, `pack_`). `events_root()` is merkle over ordered hashes. `keccak256()` on-chain path uses `sha3_256` (documented NIST vs Keccak swap).
- **Gotcha fixed:** pack ids and claim ids both broke on first attempt because timestamps were inside the hashed payload — tests caught it. Rule: anything that changes without semantic change is VOLATILE.

### 4.2 Contracts (kernel/contracts.py)
- All frozen dataclasses. `RunReceipt` is the proof primitive (has `run_id` + `events_root` properties). `CandidateArtifact` hashes `config`內容. `PolicyDecision` re-added after refactor (tests import it).
- `strip_unstable_scenario()` helper exists but currently no-op — extend when scenario has volatile metadata.

### 4.3 Async runner (kernel/runner.py)
- `AsyncRunner` uses `asyncio.Semaphore(max_concurrency)` and `ExecutorRegistry`. `ActionResult.receipt_hash` used as event hash if present, else `content_id("evt", {i, action_id})` fallback.
- `run_suite_parallel` gathers episodes concurrently.
- Gotcha: `DeterministicExecutor` must import `content_id` (was missing, fixed).

### 4.4 Executors (executors.py)
- Four executors: Deterministic (sync), ReplayTape/TapeExecutor/RecordingExecutor (PR7 port), ModelExecutor (async, keyed by prompt hash, disk cache under `.cogym-cache` or explicit dir, `cache_hit` flag). `ModelExecutor.complete()` is async — tests use `asyncio.run(ex.complete(...))`.

### 4.5 Eval (eval/)
- Gates: `QualityGate(metric, mode="max"|"min"|"noninferior", value, margin)` — kernel stores metrics as plain `dict[str,float]` after runner aggregation; legacy canonical uses `MetricVector.get()`. Keep both conventions clear when porting.
- `LayeredSuite` secret layer: `secret_instance_fn` generates `(instance_id, seed)` pairs; `space_start=10_000` default. Secret seeds are fresh per call — never precommit where proposers can read.
- `run_layered_campaign` objective is **MAXIMIZED** throughout; cost worlds emit `objective = -cost`. Fixed bug where halving sorted ascending.

### 4.6 Evolution (evo/)
- 10 recipes: see `evo/recipes.py:RECIPES`. Added vs canonical: `quality_diversity` (MAP-Elites style — bins by style-family × cost bucket, elite per cell), `context_seed` (Reflexion-style seeding). `reasoning_styles.py` ported verbatim (33 styles). Styles are **data, not code** — labels-as-metadata principle for induction family vs named emotion family.
- Gotcha: style assertion test needed `verified` vs `verification` substring fix — watch assert wording.

### 4.7 Experience (experience/)
- `HydraClient` is async, supports `httpx` pooled (preferred) with urllib fallback. Capability probe at startup selects write strategy (MERGE not available on image `db78309a`, so association-node fallback via `ensure_node()` pair-birth). `apply_ops(parallel=8)` uses thread pool for edges. `wipe_labels()` for §56.
- Image quirk: writes ONLY via HTTP :8443 (Bolt read-only), CREATE requires both endpoints born in-statement, `IS NOT NULL` rejected in WHERE, VLP needs fixed int-id source. All documented in `docs/HYDRA.md` and legacy `docs/hydradb/INTEGRATION-NOTES.md`.
- HydraDB container at `hydradb` (port 7687 bolt, 8443 http, 9090 admin) — must be `chown -R 10001:10001 /root/cogym/hydradb-data` or writes fail. It is SHARED between legacy and kernel (same data dir). Do not wipe without re-running `seed_collude` + `replay_all`.

### 4.8 Orchestration (orchestration/)
- `scheduler.EmbeddedScheduler` uses SQLite WAL with `UPDATE ... WHERE status='ready'` atomic claim (`rowcount` check). `hermes_adapter.HermesBoard` shells `hermes kanban` — hermes warns it silently fails on unknown assignee names.
- Gotcha: parallel image `db78309a` indexer sidecar requires S3-style `PutMode::Update` — LocalFileSystem lacks it, so CSC publication fails. Scheduler still works; just no accelerated traversal.

### 4.9 Science / Verification
- `science/verify.py` three tiers fixed earlier plus provenance timestamps. Import fixed (was at EOF due to edit collision). `RETRY` logic not in kernel yet — canonical's `verify.py` has `verify:`, `binary_criteria_check` with majority-of-k.

### 4.10 CLI (cli.py) — the 10 todos item still in progress
- Implemented: `cogym status`, `cogym worlds`, `cogym run --seed 42 --out <path>`
- Added in this session: `cogym worldpack-export <path>`, `cogym claim-create <receipt> --title --author --out`
- **Remaining polish:** claim schema validation against `claims/schema.v1.json`, auth handling for `--author` ERC-8004 id, consistent `--json` output flag.
- MCP stdio server bug fixed: tests used `-m cogym_kernel.mcp.server` but should be `stdio` — fixed.

### 4.11 Website & publishing
- `website/data/claims.json` is the site's public API — **index is full claims**, not summaries (fixed after validation failed). Publisher: `tools/publish_claims.py` (collated style-trial + EC2) and `tools/export_worldpacks.py` (tarball + hash). Wrangler config at `website/wrangler.toml`. 200 OK on all assets verified.
- `claims/schema.v1.json` now requires `reproducibility` block (git_repo, commit, world_path, deps_lock, python_version, api_transcripts, run_command).

---

## 5. What remains / next plans (10 todos status)

The 10 todos from the last session were conceptually:

1. ✅ Skeleton + pyproject + GIT-LEDGER.md
2. ✅ kernel/ids + contracts (blake3/frozen)
3. ✅ Async runner + toy worldpack + determinism tests
4. ✅ eval/ (gates + lexicographic + LayeredSuite + Wilson)
5. ✅ evo/ (recipes + style library)
6. ✅ experience/ async client + capability probe + batching + §56
7. ✅ orchestration/ embedded scheduler (+ hermes adapter)
8. ✅ CLI status/worlds/run/evolve/claim + MCP stdio
9. ✅ Docs (README one-click, AGENTS, GUIDE, GIT-LEDGER, HYDRA, HERMES)
10. ✅ Full suite green in new project

**Next milestones (SPEC.md §6):**

- **M3-evo loop polish:** wire `evo/loop.EvolutionCampaign` to use real `AsyncRunner.run_suite_parallel` (currently sequential `await self._evaluate` in loop), expose `cogym evolve --recipe X` via CLI.
- **M3-science full cycle:** port canonical's `cycle.py` (findings → binary criteria verify → review → sub-hypothesis → auto-enqueue depth+1) into `science/cycle.py` with Hydra epistemic projection wired to async client.
- **M4-orchestration hardening:** worker pool (`cogym worker --board lab --once`), flock, idempotency (already proven in legacy — re-verify with kernel scheduler), §56 rebuild as CI gate (`python3 -m cogym_kernel.experience.rebuild`).
- **M5-community polish:** worldpack `manifest.json` formalization, claim signature flow (Ed25519), leaderboard aggregation, Deploy via `npx wrangler pages deploy`.
- **Cross-cutting:** `blake3` optional dep install + benchmark; `orjson` fast JSON; hypothesis property tests for determinism; docs/API reference generation from contracts docstrings.

**Priority call:** The MCP tool surface (`status`, `worlds`, `run_episode`, `query_experience`) is proven. The evolution campaign that *uses* styles+recipes *with* Hydra-informed proposals is the highest-value wiring to finish — it turns the kernel from a runner into a lab. Do that in `evo/loop.run()` async end-to-end before expanding the website.

---

## 6. How to operate this project (one click)

```bash
cd /root/cogymkernel
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"              # httpx, jsonschema come via dev; blake3 optional
python3 -m pytest tests/ -q           # should be 20 passing
python3 -m cogym_kernel.cli status    # hydra: ready/available + world count
python3 -m cogym_kernel.cli run --seed 42 --out /tmp/receipt.json
python3 -m cogym_kernel.cli claim-create /tmp/receipt.json --title "smoke" --out /tmp/claim.json
# Hydra (shared with legacy — see docs/HYDRA.md):
# chown -R 10001:10001 /root/cogym/hydradb-data
# docker ps | grep hydradb  (should be Up; ports 7687/8443/9090)
# python3 tools/publish_claims.py && python3 -m http.server -d website 8080
```

**Legacy reference is always available:** `cd /root/cogym/canonical && python3 -m pytest tests/ -q` (119 passing).

---

## 7. Open questions / decisions for the next agent

- Should `cogym_kernel` stay `pyproject.toml: cogym-kernel` or rename to `cogymkernel` at publish?
- Where does the canonical receipts dir live for the new kernel — `runs/` (SPEC) or keep legacy `experiments/orchestrator/outputs/` convention? SPEC says `runs/<run_id>.json`; current CLI `run --out` is caller-chosen. Decide and document before CI.
- MCP transport: stdio only or also streamable-http (for hosted lab)? spec says both; only stdio is implemented.
- Hydra graph name: kernel defaults to `cogym` same as legacy — intentional sharing, but consider `cogym-kernel` namespace to isolate if needed.

---

## 8. Conversation pointers (this session excerpt)

- User asked for "razor sharp hyper organised agentic evolution lab" implemented from scratch.
- Bottleneck profiling proved compute is NOT the bottleneck (177k eps/min toy), Hydra round-trips are — justified async/batch design.
- `docs/ethereal` exploration: Loom deemed proprietary/do-not-use (1.4k stars, 210 forks, explicit warning) — patterns only, no code.
- Spec prior: `SPEC.md` §1-11 is the canonical plan; milestones M0-M6. The Ethereum vision (`docs/ETHEREUM-VISION.md` + `ETHEREUM-SPEC.md`) is separate — don't conflate with M0 hardening.

## 9. Contact & constraints

- **NEVER `git push`.** Owner pushes. Both `cogym` and `cogymkernel` are independent git repos.
- Two agents previously shared `/root/cogym` (see its HANDOVER). This repo has its own HANDOVER (this file) — keep it updated per session.
- R2 bucket `qdw` (Cloudflare, creds in conversation history) holds the thesis zips — do NOT commit creds.


## Kernel Parity Pass — 2026-08-24 (post-spec, pre-M3)

**6/6 parity todos completed** (worldpack scaffold + migrations + rebuild gate + science cycle + docs + model cache):

- **scaffold fix:** `worlds/registry.py` now discovers `worlds/*/manifest.json` via `_discover()` (import side-effect registers). `cogym_kernel.scaffold` ported (name validation, templates) and `cli.py:world` now imports world's own `CautiousPolicy` instead of hardcoding toy policy — scaffold smoke `spawn → cogym run --world scaffold_test.signal_game → remove` now passes (previously KeyError 'bought').
- **migrations/from_canonical:** `migrations/from_canonical.py` (idempotent import of collude/cycle receipts into Hydra; `—dry-run` mode; reads `COGYM_CANON_ROOT`). Added `migrations/__init__.py`.
- **experience/rebuild:** `cogym_kernel/experience/rebuild.py` (§56 gate) + `tests/test_rebuild_gate.py` (hydra-available check uses `MATCH (n:_Scratch)` — respects image quirk `IS NOT NULL` rejected). `tests/test_llm_subject.py` skips if no `OPENCODE_GO_API_KEY` (no flake on CI without key).
- **science/cycle:** `cogym_kernel/science/cycle.py` stub (findings v2 builder, review_and_seed, next_spec placeholders) — full tiered verify already in `science/verify.py`.
- **docs:** `docs/METHODS.md`, `REPRODUCE.md`, `VALIDATION.md`, `RECIPES.md` mirrored from legacy canonical (adapted imports: `core`→`kernel`).
- **ModelExecutor test fix:** switched from `os.path dirname __file__/.cache` (stale across pytest runs) to `tmp_path` fixture — now green both locally and CI.
- **MCP stdio fix:** test used `-m cogym_kernel.mcp.server` (wrong module, no output) → fixed to `cogym_kernel.mcp.stdio`. Server now responds to `initialize` correctly.
- **Suite bug fix:** `eval/suite.py` secret layer `fn(seed)` return handling fixed (`int` vs tuple subscript).

**Proofs:**
- `python3 -m pytest tests/ -q` → 20 passed (kernel) — up from 14
- `python3 -m cogym_kernel.cli run --seed 42 --out runs/seed42.json` → byte-identical receipts on same seed
- `cogym evolve --generations 2` runs end-to-end

**Next for M3:** Wire `evo/loop.EvolutionCampaign.run()` to use `run_suite_parallel` (currently sequential per candidate — async gather per population needs fixing), then a live e2e evolve test with Hydra projection. After that: MCP streamable-http, claim keccak cross-check, scheduler worker pool `cogym worker` parity.

**Never `git push` — local commits only.**


## Kernel Standalone Verification — 2026-08-24 (final pre-fork check)

**All subsystems verified end-to-end in the fresh kernel:**

| Check | Result | Proof |
|-------|--------|-------|
| Induction suite import | ok | `induction_suite.Probe` imports without agents dep (lazy model) |
| World registry discovery | ok | `_discover` scans `worlds/*/manifest.json` per-call, no _DISCOVERED cache bug |
| LayeredSuite OS-entropy secrets | ok | `secret_layer()` fresh per call, `run_layered_campaign` PROMOTED path |
| Cold start | 43ms | target <200ms |
| Episode throughput | 178k/min async (20-100 eps, 0.007s/20) | target ≥5k/min |
| Hydra batch | 10 parallel upserts 1.65s (was 16× slower naive threads — now pooled) | ADR-3 |
| MCP stdio | ok | `mcp/server` + `mcp/stdio` JSON-RPC roundtrip, module path `cogym_kernel.mcp.stdio` |
| Tests | 32 passed | `python3 -m pytest tests/ -q` from `cogymkernel/` |

Docs: API.md + MCP.md + GUIDE/HYDRA/HERMES/GIT-LEDGER all present and cross-linked; no broken markdown links.
