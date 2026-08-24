# Methods: A Deterministic, Replayable Laboratory for Evolving Decision Policies Under Quality Constraints

**Cogym Kernel — methods documentation v1.0 · 2026-08-24**
*This document is written to be convertible into a paper's Methods section.
Claims here are restricted to what the implemented system does; limitations
and threats are stated explicitly (§7).*

---

## 1. Abstract (system summary)

We describe a laboratory for optimizing computational decision policies against
frozen, content-addressed scenario instances while holding evaluation quality
to a hard constraint. The system separates (i) a domain-agnostic kernel
(world/policy/executor contracts, paired episode execution, lexicographic
selection under quality gates), (ii) pluggable content packs that supply
domain data and semantics, and (iii) scenario instances defined by a tuple of
specification, immutable time-indexed state, a decision schedule, an
availability function over world state, a hidden oracle, and a cost model. An
associated experience graph (a derived projection of immutable run receipts)
supports cross-generation and cross-domain policy selection. A three-tier
verification protocol — deterministic checks, binary per-criterion verification
by an independent language-model call with abstention, and qualitative review —
gates all reported outcomes. We report the system design, its statistical
discipline, and its failure-containment behavior; we make no cognitive claims.

## 2. System overview

### 2.1 Layering

Three strictly ordered layers prevent domain leakage into the experimental
machinery: the **kernel** (contracts, runner, evaluation, campaign, experience),
**content packs** (e.g., market OHLCV data via a brokerage API; fact-verification
claims), and **scenario instances**. The kernel contains no domain identifiers;
worlds register by string kind in a single registry module. Acceptance test: no
kernel module performs type dispatch on any concrete world class.

### 2.2 Contracts

A *World* implements `reset(instance_id, seed)`, `observe(state)`,
`actions(state)`, `apply(state, action, result)`, `terminal(state)`, and
`score(state)` returning a named metric vector. Crucially, `apply` receives the
outcome of an *Executor* and performs no input/output itself; executors are the
only components permitted side effects (deterministic simulation, model calls,
search providers, or replay from recorded tapes). This separation converts
non-deterministic environments into replayable ones: recording executors emit
action-keyed receipts, and a tape executor serves byte-identical responses
thereafter. Unknown tape keys fail loudly rather than falling back to live calls,
preventing accidental mixture of live and replayed observations.

A *Policy* implements `initialize(world_spec)` and
`act(observation, actions, policy_state)`. Policies may be deterministic
programs, finite-state machines, or sampled language-model calls; the kernel is
indifferent. The optimization unit is a frozen *candidate artifact*
`(kind, version, config, parent_ids, provenance)` identified by content hash;
evolution operates exclusively on `config`.

### 2.3 Scenario algebra

A scenario instance is

> Σ = ⟨Σ_spec, T, D, A, Ω, φ, κ⟩

with T an immutable time-indexed state series pinned by digest; D = (d₁…d_n)
the decision schedule; A the availability function determining which state
channels and history windows are visible at each dᵢ; Ω the evaluator-side
oracle; φ the point-in-time packet builder enforcing `available_at ≤ t(dᵢ)`;
κ a cost model. The scenario identifier hashes Σ_spec, the T digest, D, the
A configuration, and κ, so any change to information availability or decision
structure yields a distinct, comparable experiment rather than a silent confound.
Data partitions follow a dev / validation / secret discipline with feedback
permitted only on dev; secret splits receive no proposal feedback.

## 3. Experimental protocol

### 3.1 Paired evaluation

All candidates in a comparison consume identical packets at identical decision
points on identical scenario instances. Outcomes are graded deterministically
against Ω by the world's `score`; outcome states distinguish correct, incorrect,
malformed, and infrastructure-failure cases, and malformed/failed rows are
reported separately and excluded from accuracy statistics.

### 3.2 Selection under constraints

Candidate acceptance is lexicographic: (1) hard quality gates must pass
(e.g., task success = 1 on every episode); (2) among gate-passers, primary
objectives such as cash cost, then latency, break ties at a configured
materiality ε; robustness/simplicity breaks remaining ties. No scalar fitness
aggregation exists in the system. Pairwise claims use matched-instance deltas
with percentile bootstrap intervals; promotion requires the lower confidence
bound of the quality delta ≥ −margin.

### 3.3 Evolution recipes

Mutation-based search operates on candidate configs under declared search
spaces (categorical, literal-choice, integer-range genes). Provided mechanisms
include uniform random search, elitist mutation (μ+λ), tournament recombination,
successive-halving-style narrowing, graph-memory-informed adoption, reasoning-
chain composition search (reorder/insert/delete/route operations over typed
decision steps), and ancestry-guided spawning. Recipes receive only elite
configs, a scorecard, graph-derived leaders, the search space, and a seeded RNG;
they cannot access evaluators, gates, or oracle data. Every child records its
recipe, Hydra-informedness flag, and donor lineage in provenance.

## 4. Experience graph

Run receipts (immutable JSON lines, one file per job, filenames equal to job
identifiers) are canonical. A graph database (HydraDB; object-store-backed,
Bolt + HTTPS query interfaces) maintains a derived projection: policy,
world-family, and association nodes encoding ran-on relationships with metric
payloads, improvement/regression deltas versus controls, mutation ancestry, and
an epistemic chain linking experiments to hypotheses, findings, and seeded
sub-hypotheses (`Experiment—TESTED→Hypothesis—PRODUCED→Finding—SEEDS→Hypothesis′`).
Because the projection is fully derivable, deleting it is safe by construction;
rebuild replays receipts. Reads used for proposal biasing are advisory only:
graph-informed policies compete under the same hidden evaluation as all other
candidates, and the graph never receives privileged labels.

## 5. Verification protocol

Every experiment cycle emits standardized quantitative findings (schema v2:
winner configs, per-candidate metric distributions with Wilson score intervals
on binary success metrics, projection audit counts, mode label PILOT when any
decision count n < 30). Three verification tiers then apply:

1. **Deterministic checks** — schema conformance, winner-count consistency
   between findings and raw receipt, receipt-file integrity on disk,
   projection-budget bounds. Authoritative; any failure blocks the run as a
   machinery defect and it is excluded from scientific tallies.
2. **Binary criteria verdict** — an independent language-model call (separate
   session from the reviewer) answers YES / NO / UNCERTAIN per pre-frozen
   success criterion, citing quantitative evidence; majority-of-k aggregation
   (configurable k) with ties resolving to abstention; a different model family
   may be slotted for judge independence.
3. **Qualitative review** — narrative assessment, insights, and one seeded
   sub-hypothesis for the next variation.

Reconciliation: deterministic failure ⇒ BLOCKED; abstention ⇒ PROVISIONAL
(directional only); binary outcome contradicting the reviewer ⇒ DISPUTED and
routed to human review; otherwise SUPPORTED or REFUTED as agreed.

This ordering follows evidence from LLM-as-judge studies showing systematic
overestimation of correctness and prompt-induced instability of scalar
judgments (§6): model judgment is admissible only as a binary, criterion-bound,
abstention-capable check layered above deterministic verification, never as
ground truth.

## 6. Related work

LLM-as-judge reliability and bias: position and presentation biases in pairwise
judgment (arXiv:2406.07791); measurement-first audits of judge sensitivity in
code evaluation (arXiv:2604.16790); judge-overestimation against sound automated
verifiers (RESpecBench, ICLR 2026 submission); taxonomic judge-bias benchmarks
(arXiv:2603.08091); judge survey (arXiv:2412.05579). Multi-agent interaction
effects motivating our communication-topology experiments: diversity collapse
under dense communication; debate outperforming consultancy under information
asymmetry. Wilson-score reporting follows standard small-sample practice for
binomial proportions. The generator–judge separation inherits from
generator–verifier results in program synthesis and from peer-prediction
mechanisms for eliciting honest reports.

*(Full bibliographic entries in docs/REFERENCES.md.)*

## 7. Threats to validity and limitations

**Internal.** Language-model subjects are stochastic; we control temperature and
seed per call, log raw transcripts, and repeat conditions; residual nondeterminism
at provider level is bounded but not eliminated. Parallel wave scheduling cannot
alter canonical episode identity because receipts are action-id-sorted.

**Construct.** "Quality" is whatever the world's `score` encodes; a weak proxy
makes gates vacuous. We therefore require gates to be decidable per episode
(binary success metrics with Wilson intervals) and publish them in the frozen
experiment document. Graph-informed proposals risk confounding memory with
learning; they are always evaluated as ordinary candidates against hidden data.

**External.** Results at n < 30 decisions are labelled PILOT and directional
only; confirmatory status requires the pre-declared threshold. Current public
results are pilots on toy and market-replay worlds plus one multi-agent
communication pilot; nothing herein should be cited as a confirmed cognitive
or economic finding.

**Statistical.** Bootstrap intervals on matched pairs assume exchangeability of
episodes within scenario families; regime-clustered market episodes violate this,
which we mitigate by stratified suites rather than claiming independence.

**Infrastructure.** The experience-graph backend is version-pinned and its
verified query surface is documented; projections are rebuildable, so backend
defects degrade capability, never validity.

## 8. Artifact availability

Canonical artifacts are plain files: JSONL receipts, cycle directories
(findings/verification/review), frozen experiment documents, and tests (95 at
time of writing). The experience graph rebuilds from these by construction.
Reproduction commands: docs/REPRODUCE.md.
