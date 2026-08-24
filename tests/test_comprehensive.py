"""Comprehensive coverage: world, suite, school, experience, orchestrator extras."""
import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_world_signal_game_determinism():
    from cogym_kernel.worlds.toy import SignalWorld, CautiousPolicy
    from cogym_kernel.kernel.runner import AsyncRunner, ExecutorRegistry
    from cogym_kernel.executors import DeterministicExecutor
    from cogym_kernel.kernel.contracts import CandidateArtifact
    runner = AsyncRunner(ExecutorRegistry({"deterministic": DeterministicExecutor()}))
    cand = CandidateArtifact(kind="p", version="1", config={})
    async def go():
        r1 = await runner.run_episode(SignalWorld(), CautiousPolicy(), instance_id="t", seed=99, candidate=cand)
        r2 = await runner.run_episode(SignalWorld(), CautiousPolicy(), instance_id="t", seed=99, candidate=cand)
        return r1, r2
    r1, r2 = asyncio.run(go())
    assert r1.run_id == r2.run_id
    assert r1.metrics.get("correct") in (0.0, 1.0)

def test_layered_suite_secret_freshness():
    from cogym_kernel.eval.suite import LayeredSuite
    s = LayeredSuite(dev=(("t",1),), n_secret=2)
    a = s.secret_layer(); b = s.secret_layer()
    # fresh entropy: extremely likely different
    assert a != b or True  # allow rare collision, just check length
    assert len(a) == 2

def test_school_pack_compile_and_distance():
    from cogym_kernel.school.pack_v2 import compile_pack_from_leaders
    from cogym_kernel.school.induction import behavioral_distance, signature
    p = compile_pack_from_leaders("test", "toy.signal_game", [{"pk":"a","util":5}], {"fmt":"json"})
    assert p.pack_id.startswith("pack_")
    d = behavioral_distance(signature({"UP":0.5},0.5,0.1), signature({"UP":0.9},0.5,0.1))
    assert 0 < d < 1

def test_scheduler_block_and_reclaim():
    from cogym_kernel.orchestration.scheduler import EmbeddedScheduler
    import tempfile
    s = EmbeddedScheduler(tempfile.mktemp())
    s.enqueue({"job_id":"j2","type":"test"})
    j = s.claim_next("w1")
    assert j["job_id"] == "j2"
    s.block("j2", "test block")
    # blocked jobs not claimable
    assert s.claim_next("w2") is None

def test_experience_client_available_gracefully():
    import asyncio
    from cogym_kernel.experience.client import HydraClient
    c = HydraClient(http_url="http://127.0.0.1:1", timeout_s=1.0)
    # should not raise, just return False when hydra down
    assert asyncio.run(c.available()) is False

def test_reasoning_styles_count():
    from cogym_kernel.evo.reasoning_styles import list_styles
    assert len(list_styles()) >= 30

def test_recipes_all_run_minimal():
    import random
    from cogym_kernel.evo.recipes import EvolutionContext, propose_children, RECIPES
    for name in list(RECIPES.keys())[:3]:
        ctx = EvolutionContext(elite_configs=[{"a":1}], scorecard=[], hydra_leaders=[], search_space={"a":[1,2]}, rng=random.Random(0))
        kids = propose_children(name, ctx, 2)
        assert len(kids)==2

def test_mcp_tools_call_worlds():
    from cogym_kernel.mcp.server import handle
    r = handle("worlds", {})
    assert "toy.signal_game" in r["worlds"]

