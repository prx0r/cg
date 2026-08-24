# GUIDE — operating cogymkernel

The successor to legacy CANONICAL.md. Same doctrine, new kernel.

## Core loop

```
worlds/registry → AsyncRunner.run_episode → RunReceipt(run_id)
      ↓ metrics
eval/: gates PASS? → lexicographic rank (cost→latency)
      ↓ winners
experience/: project to Hydra → read leaders → evo recipe proposes children
      ↓ repeat
orchestration/scheduler: parallel jobs, receipts keyed by job_id
```

## Run an evolution campaign

```python
import asyncio
from cogym_kernel.kernel.runner import AsyncRunner, ExecutorRegistry
from cogym_kernel.executors import DeterministicExecutor
from cogym_kernel.eval import LayeredSuite, run_layered_campaign, QualityGate
from cogym_kernel.experience.client import HydraClient
from cogym_kernel.worlds.toy import SignalWorld, CautiousPolicy
from cogym_kernel.kernel.contracts import CandidateArtifact

async def main():
    runner = AsyncRunner(ExecutorRegistry({"deterministic": DeterministicExecutor()}))
    suite = LayeredSuite(dev=(("t",42),("t",7)), n_secret=4,
                         secret_instance_fn=lambda s: ("t", s))
    def evaluate(cand, layer):
        utils = []
        for inst, seed in layer:
            rec = asyncio.create_task(...)   # see tests for sync pattern
        return {"objective": sum(utils)/len(utils)}

asyncio.run(main())
```
(Full runnable versions live in `tests/`; copy a test and change the knobs.)

## Recipes & styles

```python
from cogym_kernel.evo.recipes import propose_children, EvolutionContext
kids = propose_children("elitist_mutation", ctx, 5)   # docs/RECIPES parity
from cogym_kernel.evo.reasoning_styles import apply_style  # 33 styles
sysmsg = apply_style(base_prompt, "cove", seed_context="prior critique…")
```

## Claims (community sharing)

```bash
cogym claim create runs/<run_id>.json --out claim.json   # M4 CLI surface
# validate + PR into the community site data dir (website/data/claims/)
```

## Rules recap

See AGENTS.md: never push; gates dominate; volatile fields out of ids;
secret layers proposer-blind; Hydra deletable/rebuildable.
