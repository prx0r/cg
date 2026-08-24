# API Reference — cogymkernel

All public entry points. Import paths are stable; anything not listed here is internal.

## Kernel

### `cogym_kernel.kernel.ids`
- `content_id(prefix, obj) -> str` — blake3/sha256 over canonical JSON with VOLATILE excluded.
- `strip_volatile(obj)` — remove timestamp/latency fields.
- `events_root(hashes: list[str]) -> str` — merkle root.
- `keccak256(data: bytes) -> str` — on-chain commitment (sha3_256).
- `now_ns() -> int`

### `cogym_kernel.kernel.contracts`
Frozen dataclasses: `WorldSpec`, `ActionSpec`, `ActionResult`, `Metric`, `MetricVector`, `CandidateArtifact`, `RunReceipt` (with `.run_id`, `.events_root`, `.to_json()`), `PolicyDecision`.

### `cogym_kernel.kernel.runner`
- `AsyncRunner(registry, max_concurrency=8)` — `await run_episode(world, policy, instance_id, seed, candidate) -> RunReceipt`
- `ExecutorRegistry(executors: dict)` — `await execute(action) -> ActionResult`
- `run_suite_parallel(runner, make_world, policy, suite) -> list[RunReceipt]`

## Executors (`cogym_kernel.executors`)

| Class | Executor ID | Notes |
|-------|-------------|-------|
| `DeterministicExecutor` | `det-v1` | cost/latency simulated |
| `ReplayTape` / `TapeExecutor` / `RecordingExecutor` | `tape-v1` | capture→replay, unknown keys are errors |
| `ModelExecutor(complete_fn, model_id, cache_dir)` | `model-cached-v1` | `await complete(prompt, temperature, seed) -> {text, cache_hit}` |

## Worlds (`cogym_kernel.worlds`)

- `registry.register(kind, description)` decorator, `kinds()`, `create(kind, **kw)`
- `toy.SignalWorld` — hidden bit, noisy evidence; policies: `CautiousPolicy`, `RecklessPolicy`
- Scaffold: `python3 -m cogym_kernel.scaffold my_world "desc"`

## Evaluation (`cogym_kernel.eval`)

- `QualityGate(metric, mode="max"|"min"|"noninferior", value, margin)` + `check_gate`, `gates_pass`
- `lexicographic_compare(a, a_pass, b, b_pass, objectives)` — gates dominate
- `LayeredSuite(dev, validation, n_secret, secret_instance_fn, halve_fraction)` — `dev_layer()`, `validation_layer()`, `secret_layer()` (OS entropy), `halve(ranked)`, `run_layered_campaign(candidates, evaluate_fn, suite, gates_pass_fn)`
- `wilson(k,n)`, `bootstrap_ci(deltas)`, `non_inferior_paired(baseline, candidate, margin)`

## Evolution (`cogym_kernel.evo`)

- `recipes.RECIPES` (10) + `propose_children(name, ctx, n)` via `EvolutionContext`
  `random_search · elitist_mutation · tournament · successive_halving · hydra_adoption · champion_lineage · chain_assembly · quality_diversity · context_seed · style_sweep`
- `reasoning_styles.STYLES` (33 / 16 families) + `apply_style`, `list_styles`, `aggregate_by_style`

## Experience (`cogym_kernel.experience`)

- `HydraClient(http_url, graph, namespace, cell, token)` — `await query(...)`, `await write(...)`, `await available()`, `ready()`, `ensure_node(NodeRef)`, `put_edge(Edge)`, `apply_ops(nodes, edges, parallel=8)`, `wipe_labels(labels)`
- `NodeRef(label, key, props)`, `Edge(rel_type, src, dst, props)` + `.to_node()` for association schema
- `loop.project_performance`, `top_policies`, `causal_read`, `lineage_paths`

## School (`cogym_kernel.school`)

- `pack_v2.compile_pack_from_leaders(name, world_kind, leaders, contract)` → PackV0 (`.pack_id`, `.to_dict()`, `.dumps()`) + `certify(pack, verification)` + `local_commitment_attestation(...)`
- `induction.signature`, `behavioral_distance`, `compression_ratio`, `retention`

## Orchestration (`cogym_kernel.orchestration`)

- `scheduler.EmbeddedScheduler(path)` — `enqueue(job)`, `claim_next(worker_id)`, `complete(job_id, result)`, `block(job_id, reason)`
- `hermes_adapter.HermesBoard(board)` — same protocol over `hermes kanban` CLI (optional)

## Science (`cogym_kernel.science.verify`)

- `deterministic_checks(findings, receipt_path?)` + `binary_criteria_check(findings, spec, llm_fn?)` + `reconcile(det, binary, review_verdict)` → SUPPORTED/REFUTED/PROVISIONAL/DISPUTED/BLOCKED

## CLI (`cogym_kernel.cli`)

`cogym status` | `cogym worlds` | `cogym run --world X --seed N --out path` | `cogym evolve --world X --generations N` | `cogym worldpack-export <path>` | `cogym claim-create <receipt> --title --out`

## MCP (`cogym_kernel.mcp`)

Stdio server: `python3 -m cogym_kernel.mcp.server`. Tools: `status`, `worlds`, `run_episode`, `query_experience` (streamable-http transport planned).
