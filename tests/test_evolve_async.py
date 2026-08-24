"""Async evolution campaign: real loop, real world, no mocks."""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cogym_kernel.evo.loop import EvolutionCampaign, CampaignConfig
from cogym_kernel.kernel.runner import AsyncRunner, ExecutorRegistry
from cogym_kernel.executors import DeterministicExecutor
from cogym_kernel.kernel.contracts import CandidateArtifact


def test_campaign_runs_and_selects():
    from cogym_kernel.worlds.toy import SignalWorld, CautiousPolicy, \
        __dict__ as _d
    class Reckless:
        policy_id = "reckless"
        def initialize(self, ws): return {}
        def act(self, obs, actions, ps):
            from cogym_kernel.kernel.contracts import PolicyDecision
            a = next(a for a in actions if a.kind == "COMMIT")
            return PolicyDecision(action=a)

    polmap = {"cautious": CautiousPolicy, "reckless": Reckless}
    def pfactory(cand):
        return polmap[cand.config["strategy"]]()
    def wfactory():
        return SignalWorld()

    runner = AsyncRunner(ExecutorRegistry({"deterministic": DeterministicExecutor()}))
    cfg = CampaignConfig(world_kind="toy.signal_game",
                         suite=[("t", 42), ("t", 7), ("t", 2026)],
                         gates_metric="correct", generations=2, population=4,
                         elite_k=1)
    camp = EvolutionCampaign(world_factory=wfactory, policy_factory=pfactory,
                             runner=runner, config=cfg, hydra_client=None,
                             recipe="elitist_mutation",
                             search_space={"strategy": ["cautious", "reckless"]})
    seeds = [CandidateArtifact(kind="p", version="1", config={"strategy": s})
             for s in ("cautious", "reckless")]
    winners = asyncio.run(camp.run(seeds))
    assert winners, "campaign must produce winners"
    cautious_won = any(w.config.get("strategy") == "cautious" for w in winners)
    assert cautious_won, "quality gate should favor the 3-signal policy"
    assert len(camp.generations) == 2
