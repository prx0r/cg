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
