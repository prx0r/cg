# POSITIONING — what cogym should be (strategy review)

**2026-08-24 · Decision doc. Reviews the landscape, audits our assets, picks
the flagship product, and shows it reuses what we already built.**

---

## 1. Competitive landscape (researched)

| Player | What they do | What they DON'T do |
|---|---|---|
| x402 Bazaar / Agentic.Market | discover + pay for services | no quality signal at all |
| x402scan | volume/txn analytics | popularity ≠ competence |
| Bitquery | payment-flow data | payment-level only |
| x402 Hub Reputation API | uptime/response-time/stake badges | scores process inputs, never outputs |
| x402 Trust Layer MCP | KYM wash-trade scoring, delivery escrow, settlement receipts | verifies money moved, not work quality |
| Prova (Solana) | signed action receipts ("this call happened") | proves occurrence, not correctness |
| Bittensor | decentralized model market with validator scoring | closed subnet benchmarks, own chain, not portable to arbitrary x402 endpoints |

**The confirmed hole:** payment history is visible; results are invisible.
Nobody captures what an API *actually returned*, whether outputs were correct,
consistent, or safe — and nobody can replay a claimed result. Every reputation
system scores process. Zero score outcomes.

## 2. Asset audit — what we uniquely have

1. **ReplayTape / RecordingExecutor / TapeExecutor** — capture verbatim
   external responses; serve them byte-identical forever (`core/campaign.py`).
2. **Scenario hashing + fork ids** — pin exact conditions; change one variable.
3. **Secret splits** — fresh entropy evaluation instances proposers can't see.
4. **Three-tier verification + CapabilityClaims** — outcomes graded against
   oracles, published tamper-evidently.
5. **HydraDB experience loop** — write-after-run, read-before-decide;
   association graph of behaviors per policy/world.
6. **Evolution engine** — 14 recipes, 33 reasoning styles, kanban parallelism:
   machinery to EVOLVE probing strategies themselves.
7. **MCP surface (planned)** — native tool access for any agent.

Nobody else combines capture-replay + oracle grading + experience memory +
evolution. Each alone is copyable; the composition is the moat.

## 3. The three directions, honestly assessed

### Direction A — Verification/trust layer for x402 (recent drift)
Strong science, but sells shovels to people who haven't asked for holes yet.
Requires vendors to *want* certification — adoption friction high at n=0.
Also collides head-on with Trust-Layer-MCP/Prova-type players moving fast.

### Direction B — MCP evolution lab (original factminer vision)
Our deepest differentiator, but it's infrastructure without a face: hard to
explain, harder to sell. Needs a killer application to be visible.

### Direction C — Empirical Service Profiles (the user's new idea)
> Run any x402 endpoint through cogym with generated request-classes; capture
> verbatim outputs into replay tapes; compute behavioral signatures (schema
> conformance, latency distribution, failure modes, consistency-under-repeat,
> cost); publish an **Empirical Service Profile** so a buyer agent can see
> EXACTLY what output it will get for its request-class before spending.

**This is the sharpest wedge**, because:
- It needs only ONE kernel primitive end-to-end: RecordingExecutor → tape →
  signature → Hydra profile. All built.
- Demand is immediate and universal: every Bazaar buyer has this problem today.
- It sidesteps the "who grades correctness?" problem — showing REAL exemplar
  outputs is evidence even where ground truth doesn't exist (no judge needed).
- It naturally upgrades into A (profiles carry verified claims where oracles
  exist) and B (profiling strategies are themselves evolved — meta-lab).

## 4. Decision — converge, don't choose

**Flagship product: Empirical Service Profiles (ESP) — "try the API without
trusting the API."**

**The MCP evolution lab remains the engine**, not a casualty:
- profiling policies (probe sequences, attack styles, stop rules) are
  CandidateArtifacts evolved by our own recipes under information-gain/cost
  objectives — the lab eats its own cooking;
- Hydra stores profiles + which probe strategies produced maximal
  discrimination per service-class — exactly the §5.3 reasoning-chain pattern;
- MCP tools expose both layers: `profile_service`, `query_profile`,
  `compare_services` for buyers; `evolve.step` for the meta-loop.

## 5. ESP v0 — mapped entirely to existing components

```
probe plan (style_sweep over request-classes)     ← evo/recipes.py
        ↓
RecordingExecutor captures verbatim responses      ← core/campaign.py (BUILT)
        ↓
behavioral signature: schema-conformance rate,
latency dist, failure modes, repeat-consistency,
cost per class                                     ← school/induction.signature (extend)
        ↓
Hydra: (:Service)-[:EXHIBITS]->(:Profile {class, exemplars, stats})
       (:Probe)-[:PRODUCED]->(:Exemplar)            ← experience/projection.py
        ↓
buyer tool: match(request-class) → exemplars+stats → decide
                                                    ← MCP tool, thin
```

New code required: a `probes.py` request-class generator (~100 lines), the
signature extension for text/schema outputs (~80 lines), one MCP wrapper.
Everything else exists and is tested.

## 6. Verification/trust (Direction A) becomes a PROFILE FEATURE, not the product

Where ground truth EXISTS (factcheck claims, trading realized returns,
deterministic toy worlds), profiles embed verified accuracy claims — the
full three-tier machinery. Where it doesn't, profiles are honest raw
exemplars + consistency stats. The claim ladder stays intact; we simply lead
with the universally-valuable half (exemplars) and grow into the oracle half.

## 7. What we do NOT build now

- Challenge/slash contracts (Edition C deferred until profiles have users)
- Generic marketplace UI beyond the existing static site (add a profile tab)
- Bittensor integration (watch its validator economics; no dependency)
- Any probe of endpoints without consent signals (respect robots/ToS;
  probe only services that opt in via `.well-known/x402` discovery or explicit
  listing — same channel the Bazaar itself uses)

## 8. One-line positioning

> **cogym: before you pay an agent-API, see exactly what it will return.
> We run real probe requests in deterministic capture, publish the exemplars,
> and evolve the probes so sellers can't game them.**

---

## 9. Drift detection — timestamped profiles (v0.5 upgrade)

Every profile run emits fork_id + tape with wall-clock timestamps. Re-running
the SAME probe plan later yields a TEMPORAL FORK: identical request+seed,
different date. Output diffs = endpoint behavior change detection.

    profile(endpoint, t1) --replay-same-plan--> profile(endpoint, t2)
         diff → DRIFT REPORT: which request-classes changed, how much

Consequences:
- ESP becomes a SUBSCRIPTION (continuous behavioral monitoring), not a static
  review. Recurring revenue + alerting ("vendor silently swapped models Mar 3").
- Temporal forks reuse core/forks.py unchanged — time is just another fork axis.
- Longitudinal tape archive = the one asset that cannot be backfilled by a
  fast follower. It compounds daily.

## 10. Relation to the evolution lab and forks — honest mapping

v0 loop (capture → signature → publish) uses: RecordingExecutor/ReplayTape,
scenario hashing, Hydra projection. NOT the evolution engine.

Where evolution genuinely enters (v1+):
1. PROBE STRATEGY EVOLUTION: probe sequences are CandidateArtifacts; recipes
   evolve them under information-gain-per-cost objectives against known-
   heterogeneous service sets. The lab optimizes how we profile.
2. CROSS-ENDPOINT FORKS: same canonicalized request across N competing
   services = controlled comparison (fork discipline applied horizontally).
3. STYLE SENSITIVITY: LLM-mediated endpoints probed under multiple reasoning
   styles expose prompt-brittleness — a quality dimension no uptime metric
   captures.
4. BUYER-SIDE MATCHING POLICIES also evolve (which exemplar-matching approach
   best predicts buyer satisfaction).

So: the lab is the optimization layer on profiling, not the heart. Heart =
capture + publish. Fine — not every product needs every organ.

## 11. Business model refinement

Free tier: latest profile snapshot per endpoint (discovery value).
Paid: full exemplar sets, drift alerts, historical diffs, API access,
verified-score add-ons where oracles exist. Buyers pay per profile-query or
subscribe; providers pay to feature VERIFIED badges (never to suppress).

Scoring integration rule: where ground truth exists (factcheck, trading
realized returns), profiles embed three-tier-verified accuracy claims.
Where it doesn't, profiles carry raw exemplars + consistency/drift stats —
honest by construction.

## 12. The Coinbase threat — full analysis

Q: What stops Coinbase from adding reviews to Bazaar/Agentic.Market?

1. STRUCTURAL CONFLICT: Coinbase monetizes volume. Honest quality reviews
   shrink volume (dead vendors stop transacting). A facilitator grading its
   own listings has misaligned incentives — agents will discount it. We profit
   from TRUTH, structurally independent of flow.
2. REVIEWS ≠ OUR ARTIFACT: opinions/stars are sybil-gameable. We ship captured
   verbatim outputs + replay proofs + longitudinal drift archives. Different
   artifact class; requires building capture/replay/secret-split infra +
   accepting neutrality — i.e., becoming a different company.
3. THE UNCLONABLE MOAT: longitudinal tape archive. Day-one clone has no
   history; behavioral drift records compound and cannot be backfilled.
4. ECOSYSTEM POLITICS: x402 is Linux-Foundation-neutral. Facilitator-graded
   listings break that neutrality; an independent verifier is the politically
   correct shape (and multi-facilitator/open-schema posture keeps us
   unlockable even from CDP itself).
5. IF THEY BUILD IT ANYWAY: integration > war — our signed claims feed becomes
   their review source, or the acquisition target. Either outcome validates
   the market we defined.

Positioning sentence: facilitators profit from VOLUME; cogym profits from
TRUTH. When those conflict — and they will — agents need somewhere unbiased
to stand. That place is a deterministic replay of reality.
