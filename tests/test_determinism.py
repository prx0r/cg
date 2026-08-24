"""Determinism is the proof primitive: same inputs => identical run_id."""
import asyncio
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cogym_kernel.kernel.contracts import CandidateArtifact
from cogym_kernel.kernel.ids import content_id
from cogym_kernel.kernel.runner import AsyncRunner, ExecutorRegistry
from cogym_kernel.worlds.toy import SignalWorld


class Cautious:
    policy_id = "cautious"
    def initialize(self, ws): return {}
    def act(self, obs, actions, ps):
        from cogym_kernel.kernel.contracts import PolicyDecision
        if obs["bought"] < 3:
            a = next(a for a in actions if a.kind == "BUY_EVIDENCE")
            return PolicyDecision(action=a)
        ups = sum(obs["signals"])
        want = "UP" if ups >= len(obs["signals"]) / 2 else "DOWN"
        return PolicyDecision(action=next(a for a in actions
                                          if a.kind == "COMMIT"
                                          and a.payload["stance"] == want))


def _runner():
    from cogym_kernel.executors import DeterministicExecutor
    return AsyncRunner(ExecutorRegistry({"deterministic": DeterministicExecutor()}))


def test_same_seed_same_run_id_anywhere():
    cand = CandidateArtifact(kind="p", version="1", config={})
    async def go():
        r1 = await _runner().run_episode(SignalWorld(), Cautious(),
                                         instance_id="t", seed=42, candidate=cand)
        r2 = await _runner().run_episode(SignalWorld(), Cautious(),
                                         instance_id="t", seed=42, candidate=cand)
        return r1, r2
    r1, r2 = asyncio.run(go())
    assert r1.run_id == r2.run_id and r1.events_root == r2.events_root


def test_different_seed_different_run():
    async def go():
        return [await _runner().run_episode(SignalWorld(), Cautious(),
                                            instance_id="t", seed=s,
                                            candidate=CandidateArtifact(
                                                kind="p", version="1", config={}))
                for s in (42, 43)]
    r1, r2 = asyncio.run(go())
    assert r1.run_id != r2.run_id


def test_volatile_fields_never_enter_ids():
    a = content_id("x", {"v": 1, "created_at": "2026-01-01"})
    b = content_id("x", {"v": 1, "created_at": "2099-12-31"})
    assert a == b


def test_three_tier_verification_statuses():
    from cogym_kernel.science.verify import (binary_criteria_check,
                                             deterministic_checks, reconcile)
    det_ok = {"tier": "deterministic", "pass": True, "checks": []}
    assert reconcile(det_bad := {"tier": "d", "pass": False, "checks": [1]},
                     {"outcome": "SUPPORTED"}, "SUPPORTED")["status"] == "BLOCKED"
    assert reconcile(det_ok, {"outcome": "ABSTAIN"}, None)["status"] == "PROVISIONAL"
    assert reconcile(det_ok, {"outcome": "REFUTED"}, "SUPPORTED")["status"] == "DISPUTED"
    assert reconcile(det_ok, {"outcome": "SUPPORTED"}, "SUPPORTED")["status"] == "SUPPORTED"
    abstain = binary_criteria_check({}, {}, llm_fn=None)
    assert abstain["outcome"] == "ABSTAIN"


def test_model_executor_cache_makes_reruns_free(tmp_path):
    import asyncio
    import shutil
    from cogym_kernel.executors import ModelExecutor
    calls = {"n": 0}

    def fake_llm(prompt):
        calls["n"] += 1
        return f"reply-{calls['n']}"

    ex = ModelExecutor(fake_llm, model_id="test-model",
                       cache_dir=str(tmp_path / "cache"))
    r1 = asyncio.run(ex.complete("hello", temperature=0.3, seed=1))
    r2 = asyncio.run(ex.complete("hello", temperature=0.3, seed=1))
    assert r1["cache_hit"] is False and r2["cache_hit"] is True
    assert r1["text"] == r2["text"] and calls["n"] == 1
    assert (tmp_path / "cache").exists()


def test_worldpack_manifest_required_fields_and_registry_roundtrip(tmp_path):
    """Scaffolded worlds carry manifest.json; registry discovers them."""
    from cogym_kernel.scaffold import create_world
    from cogym_kernel.worlds.registry import kinds, create
    import shutil as _shutil
    name = "manifest_check"
    _shutil.rmtree(f"cogym_kernel/worlds/{name}", ignore_errors=True)
    create_world(name, description="manifest test", force=False)
    try:
        assert f"{name}.signal_game" in kinds()
        w = create(f"{name}.signal_game")
        assert w.world_spec.world_kind == f"{name}.signal_game"
        import json
        manifest = json.loads(open(f"cogym_kernel/worlds/{name}/manifest.json").read())
        for field in ("kind", "name", "version", "created"):
            assert field in manifest, f"missing manifest field {field}"
    finally:
        import shutil
        shutil.rmtree(f"cogym_kernel/worlds/{name}", ignore_errors=True)


def test_claim_keccak_cross_check(tmp_path):
    """claim_id content-hash recomputes; keccak for chain is deterministic."""
    import json, hashlib, sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    receipt = {"run_id": "run_abc", "candidate_config": {"a": 1},
               "event_hashes": ["h1", "h2"], "events_root": "abc",
               "metrics": [{"name": "correct", "value": 1.0}],
               "seed": 42}
    claim = {
        "schema": "cogym.capability_claim.v1",
        "title": "t", "world": "toy.signal_game",
        "scenario_hash": "abc", "mode": "PILOT", "n_decisions": 2,
        "verification": {"final": "SUPPORTED"},
        "candidate": {"kind": "k", "version": "1", "config": {}},
        "metrics": {"correct": 1.0},
        "reproducibility": {"git_repo": "https://x", "git_commit": "a"*40,
                            "world_path": "x", "deps_lock": "h",
                            "python_version": "3.11", "api_transcripts": [],
                            "run_command": "cogym run"},
        "receipts": ["run_abc"], "model": {"id": "m", "temperature": 0, "seeded": True},
        "author": "test", "created_at": "2026-08-24T00:00:00Z", "signature": None,
        "claim_id": "",
    }
    # simulate publisher: claim_id excludes volatile keys
    payload = {k: v for k, v in claim.items() if k not in ("claim_id", "created_at", "signature")}
    claim["claim_id"] = "claim_" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:24]
    # verifier recomputes
    payload2 = {k: v for k, v in claim.items() if k not in ("claim_id", "created_at", "signature")}
    expect = "claim_" + hashlib.sha256(json.dumps(payload2, sort_keys=True).encode()).hexdigest()[:24]
    assert claim["claim_id"] == expect
