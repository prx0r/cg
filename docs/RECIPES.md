# COGYM EVOLUTION RECIPES — out-of-the-box evolutionary mechanisms

**Location:** `canonical/cogym/evolution/recipes.py` · wired into the
Hermes↔HydraDB loop (`docs/ORCHESTRATION.md`). No overengineering: each recipe
is one function `(context, n_children) → child configs`. Selection is NOT a
recipe's job — quality gates + lexicographic ranking live in
`core/campaign.py` and always dominate.

## The loop every recipe lives in

```
evaluate population ──► project to HydraDB ──► gates kill failures ──►
        ▲                                                  rank (cost→latency)
        │                                                         │
        └────────── recipe proposes N children ◄── elites + Hydra leaders
```

A recipe sees only: elite configs, this generation's scorecard, Hydra leaders
on this world family, and your declared search space. It never sees
evaluators, oracle data, or gates.

## Using a recipe (one line in a job spec)

```json
{
  "job_id": "toy-a-1234abcd",
  "world_kind": "toy.search_game",
  "recipe": "elitist_mutation",
  "search_space": {"strategy": ["sequential", "binary", "reverse"]},
  "gates": {"found": ["max", 1.0]},
  "suite": [["t", 42], ["t", 7]],
  "generations": 3,
  "population": 6,
  "candidate_configs": [{"strategy": "sequential"}, {"strategy": "binary"}]
}
```

Then: `python3 experiments/orchestrator/dispatch.py` (edit `build_jobs()`) and
drain with N parallel workers. The receipt records which recipe ran and how
many proposals were Hydra-informed.

## Search space syntax

```python
{"strategy":  ["a", "b", "c"],              # categorical
 "threshold": [0.5, 0.9],                   # literal choices
 "budget":    {"min": 1, "max": 8, "step": 1}}   # int range
```

## Standard recipes

| recipe | mechanism | use when |
|---|---|---|
| `random_search` | uniform sampling of the space | baseline every campaign must beat |
| `elitist_mutation` | (μ+λ): copy elites, resample genes p=0.5 | safe default; small populations |
| `tournament` | k=3 tournament by cost → uniform crossover → mutate | you have ≥4 evaluated configs and want recombination |
| `successive_halving` | narrow around top half of scorecard, light mutation | expensive suites; wide first waves |
| `hydra_adoption` | mutate elites gently toward graph-known leaders | continuing campaigns; cross-campaign memory |

## Reasoning recipes (the novel ones)

| recipe | mechanism | grounding |
|---|---|---|
| `chain_assembly` | evolves the ORDER and COMPOSITION of reasoning-chain steps (`steps`, `parallel_first_wave`, `model_routing`). Ops: reorder / drop / insert / swap-routing | COLLUDE E-C2: structure beats chatter (debate +92.8 > chat −51.8 V_comm); chains are CandidateArtifacts per KERNEL-SPEC §5.3 |
| `champion_lineage` | spawns conservative mutants around Hydra-proven leaders; lineage roots recorded for later `algo.SSpaths` ancestry queries | E-C1/E-C2 experience graph already ranks conditions; ancestry = who-descended-from-whom |

Chain semantics are world-defined. In generated worlds (`cogym world-new`),
the scaffold ships `StepChainPolicy`: each `ANALYZE_*`/`ATTACK_*` step buys
one evidence unit, `JUDGE` weighs, `COMMIT` commits — so evolving the chain
literally evolves the cost/quality frontier.

## Worked example — what actually ran on this repo (2026-08-24)

```
recipe elitist_mutation  toy.search_game   winners=2  champion={"strategy":"sequential"}
recipe champion_lineage  toy.search_game   winners=2  informed_proposals=2 (Hydra leaders)
recipe chain_assembly    demo.signal_game  winners=2  champion steps=[PACKET, COMMIT, ANALYZE_SUPPORT,…]  ← recipe reordered the chain
```

## Adding a recipe (~10 lines)

```python
@recipe("my_recipe", "standard", "what it does")
def _my(ctx: EvolutionContext, n: int) -> list[dict]:
    return [mutate_config(ctx.elite_configs[i % len(ctx.elite_configs)],
                          ctx.search_space, ctx.rng) for i in range(n)]
```

Rules: no evaluator access, no I/O requirements (Hydra leaders arrive as plain
dicts), deterministic given `ctx.rng`, and record any Hydra dependence via
`adopted_from`/`lineage_root` keys so receipts stay honest.

## Provenance & honesty

Every child carries `provenance = {recipe, hydra_informed, donor?}` into its
CandidateArtifact; every job receipt reports `informed_proposals` vs
`fallback_proposals`. A recipe that claims Hydra guidance but proposes without
leaders is visible immediately.
