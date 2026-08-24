# REPRODUCE — exact commands to rebuild every result class

**Rule:** receipts are truth. Everything derived (leaderboards, experience
graph, reviews) rebuilds from files in this repo.

## 0. Environment

```bash
cd /root/cogym/canonical
source ~/.bashrc                      # OPENCODE_GO_API_KEY (subject/proposer plane)
set -a; source .env; set +a           # ALPACA keys (only for market content packs)
python3 --version                     # 3.11.2 reference
python3 -m pytest tests/ -q          # expect: all pass (95 @ 2026-08-24)
```

## 1. Kernel determinism (no network, no keys)

```bash
python3 -m pytest tests/test_generic_core.py tests/test_trading_adapter.py \
                   tests/test_evolution_recipes.py tests/test_verification.py -q
```
Proves: same seed ⇒ identical episode_id + final_output_hash; golden trading
episode byte-parity; recipes deterministic given RNG seed; verification tiers.

## 2. HydraDB experience layer

```bash
docker ps | grep hydradb                       # container up
curl -fsS http://localhost:9090/readyz         # admin ready
# permissions fix if writes fail with Permission denied:
chown -R 10001:10001 /root/cogym/hydradb-data
```

Rebuild the epistemic/experience graph from canonical receipts:

```bash
python3 experiments/hydra/seed_collude.py      # replays COLLUDE E-C1/E-C2 results
```

Verify ranked leaders match published pilot numbers:

```bash
python3 - <<'PY'
from cogym.experience.loop import ExperienceLoop
tops = ExperienceLoop().top_policies("alpaca_bank_a621a0e19fa8")
for t in tops: print(t)
PY
# expected top: ensemble3 / solo +106.1 bps, debate3 +92.8, roles3 +80.3 (E-C1/E-C2 pilots)
```

## 3. Evolution campaign on a world

```bash
python3 -m cogym.worlds.demo.runner --generations 2      # scaffolded world smoke
cat ../../experiments/demo-auto/outputs/demo-receipts.jsonl
```

## 4. Parallel scenario matrix via kanban

```bash
python3 experiments/orchestrator/dispatch.py
python3 experiments/orchestrator/worker.py --board cogym-lab --once &   # ×N workers
hermes kanban --board cogym-lab list --json
ls experiments/orchestrator/outputs/           # one immutable receipt per job_id
```

## 5. Full scientific cycle (hypothesis → findings → review → sub-hypothesis)

Enqueue an `experiment_cycle` task per docs/EXPERIMENT-TEMPLATE.md, then drain:

```bash
python3 experiments/orchestrator/worker.py --board cogym-lab --max-tasks 1 --once
cat experiments/orchestrator/cycles/<cycle_id>/FINDINGS.json     # quantitative v2 (+ Wilson CIs)
cat experiments/orchestrator/cycles/<cycle_id>/VERIFICATION.json # three-tier verdicts
cat experiments/orchestrator/cycles/<cycle_id>/REVIEW.md         # qualitative + seeded sub-hypothesis
```

Majority-of-k binary verifier: `COGYM_VERIFY_K=3`. Cross-family verifier:
`VERIFY_MODEL_ID` + `VERIFY_BASE_URL` (+ `VERIFY_API_KEY`).

## 6. Multi-agent communication pilots (COLLUDE E-C1/E-C2)

```bash
cd canonical && python3 experiments/collude/run_ec1.py    # ~64 calls, ox-alpha-free
python3 experiments/collude/run_ec2.py EC2_SCORE_ONLY=1   # score-only recovery path
# outputs: experiments/collude/outputs/ec{1,2}-results.json (+ peer-review MDs)
```

## Known irreproducibles (declared)

1. Live LLM subjects: provider-side nondeterminism beyond seed/temperature.
2. Alpaca IEX feed: historical bars are stable but refetch windows ending
   "today" shift; always pin end dates (subworld registry does).
3. Reviewer/verifier LLM outputs: logged verbatim under
   `experiments/orchestrator/transcripts/`; reruns will differ in prose,
   not in graded numbers.
