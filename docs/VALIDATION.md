# COGYM VALIDATION — how we know a finding is real

**Status:** implemented · 2026-08-24 · `canonical/experiments/orchestrator/verify.py`
**Grounding:** LLM-as-judge reliability literature (2024–2026) + Hermes agent
verification features + repo anti-theatre contract.

## The problem we guard against

Systematic results across CodeJudgeBench, RESpecBench (ICLR-26), position-bias
studies (arXiv 2406.07791, 2604.16790) and judge-bias surveys:

- **LLM judges overestimate correctness** — high false-acceptance rates vs
  executable ground truth. A judge saying "SUPPORTED" is weak evidence.
- Judge verdicts are **sensitive to prompt presentation** (position, verbosity,
  authority cues) even when content is unchanged.
- **Binary criterion checks are more stable** than scalar scores.
- Reliability requires **repetition/aggregation** and an explicit **abstain** path.
- Deterministic/executable evidence (tests, arithmetic, hashes) is the only tier
  that can be treated as authoritative.

## Our three tiers (in cycle.py: findings → verification → review)

| Tier | What | Trust | Failure behavior |
|---|---|---|---|
| **1. Deterministic** (`deterministic_checks`) | schema v1 check, winner-count vs raw receipt consistency, receipt-file-on-disk match, projection-budget sanity, hypothesis present | **Authoritative.** No LLM anywhere. | Any failure ⇒ task BLOCKED (machinery defect — never counted as a scientific result) |
| **2. Binary criteria** (`binary_criteria_check`) | fresh-context LLM answers YES / NO / UNCERTAIN per frozen `success_criteria`, quoting numbers from FINDINGS only. Pointwise (no pairwise ⇒ no position bias). Cannot see Tier-3 narrative. Abstention allowed. | Evidence-grade when it quotes numbers; ABSTAIN ⇒ status PROVISIONAL (directional only) | Disagrees with reviewer ⇒ **DISPUTED** ⇒ blocked for human review |
| **3. Qualitative review** (`review_and_seed`) | narrative assessment, insights, sub-hypothesis seeding | Narrative only — never promotes a claim alone | |

Final statuses: `SUPPORTED` / `REFUTED` (tiers agree), `PROVISIONAL`
(binary abstained), `DISPUTED` (tiers disagree → human review),
`BLOCKED` (deterministic failure).

Frozen-before-run `success_criteria` in the EXPERIMENT doc are what Tier 2
checks — post-hoc criteria would be theatre (repo rule).

## Known gaps this system still has (honest list)

1. FINDINGS does not yet surface per-candidate gate metrics (caught live by the
   binary verifier on exp-verified-1: `gate_quality: UNCERTAIN`) — add
   `found/correct` distributions to findings.quantitative next.
2. Single binary verifier call, no repetition yet. Literature recommends
   majority-of-k for stability; add k=3 at temperature 0 when stakes rise.
3. Same model family reviews and verifies (ox-alpha-free). Cross-family
   verification (different provider for Tier 2) is the cheap upgrade.

## Hermes: goals, kanban, and what else is worth using

Vendored docs: `docs/hermes/` (llms.txt index, kanban.md, goals.md).

### Goal-mode cards (`--goal`)? Yes — but scoped.

Hermes goal-mode wraps a card's worker in a Ralph-style loop: after every turn
an auxiliary judge checks output against the card's title+body as acceptance
criteria; on budget exhaustion the card BLOCKS for human review rather than
exiting silently. Hermes' own docs: use it for open-ended multi-step cards;
skip it for cheap one-shot work (judge overhead); write the body as explicit
acceptance criteria.

Our mapping:
- **Deterministic campaign workers**: NO goal mode. They are one-shot scripts;
  verification is our Tier-1 code, not a per-turn LLM judge.
- **Open-ended proposer tasks** (e.g. "search arxiv for mechanisms that beat
  chain_assembly and draft a recipe"): YES — `--goal --goal-max-turns 10`,
  body written as acceptance criteria ("≥3 candidate papers with protocol
  summaries; proposed recipe passes tests/test_evolution_recipes.py shape").

### Kanban Swarm (workers → verifier → synthesizer)

Adopted as a *pattern*, not a dependency: our cycle IS that topology
(run → Tier1/Tier2 verify → seeded synthesis), with the verifier stages
deterministic-first. If we later want profile-based swarms,
`hermes kanban swarm` creates the graph atomically with dependency gating.

### Completion evidence convention

We adopt Hermes' recommended structured handoff metadata: every experiment
task completes with summary containing `verdict=… verification=<status> … |
verification evidence: <path to VERIFICATION.json>`; BLOCKED/DISPUTED tasks
are blocked (never silently done).

### Other Hermes features worth noting (not wired yet)

- **Curator** — background skill grading/pruning: candidate for maintaining the
  `cogym-experiment` skill as prompts evolve.
- **Batch processing / trajectory export** — relevant later for RL-style reuse
  of subject trajectories (out of scope until receipts are big).
- **Task ownership gate** — destructive kanban ops are env-gated per worker;
  free safety win we inherit by staying on the CLI.
- **Multi-board isolation** — one board per world/workstream if contention
  appears; today one `cogym-lab` board suffices.

## Validation of the loop itself (meta-checks)

1. **Rebuild test** (factminer §56): delete Hydra graph → replay receipts →
   identical projection. Receipts are truth; the graph is derived.
2. **Golden fixtures**: trading episode pinned byte-for-byte; recipe outputs
   deterministic given seed (tests/test_evolution_recipes.py).
3. **PILOT honesty**: n<30 ⇒ directional-only labels everywhere (README rule,
   enforced by reviewer prompt and AGENTS conventions).
4. **Idempotency**: receipt filename = job_id; flock prevents double-runs;
   kanban idempotency keys prevent duplicate tasks.
