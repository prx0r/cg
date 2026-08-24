"""Async kernel runner: world + policy + executors -> RunReceipt.

Structured concurrency; episodes are independent tasks. Executors own ALL
side effects; World.apply() consumes ActionResult only (factminer §0.A).
Determinism: same (worldpack, instance_id, seed, candidate) => same run_id.
"""
from __future__ import annotations

import asyncio
import time

from .contracts import (ActionResult, CandidateArtifact, MetricVector,
                        RunReceipt)
from .ids import content_id


class ExecutorRegistry:
    def __init__(self, executors: dict[str, Any]):
        self.executors = executors            # executor_kind -> executor

    async def execute(self, action) -> ActionResult:
        ex = self.executors.get(action.executor_kind)
        if ex is None:
            return ActionResult(action_id=action.action_id, status="error",
                                error=f"no executor '{action.executor_kind}'")
        result = ex.execute(action)
        if asyncio.iscoroutine(result):
            result = await result
        if not getattr(result, "started_ns", 0):
            now = time.time_ns()
            result = ActionResult(**{**result.__dict__, "started_ns": now,
                                     "finished_ns": time.time_ns()})
        return result


class AsyncRunner:
    def __init__(self, registry: ExecutorRegistry, max_concurrency: int = 8):
        self.registry = registry
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def run_episode(self, world, policy, *, instance_id: str, seed: int,
                          candidate: CandidateArtifact | None = None,
                          max_steps: int = 64) -> RunReceipt:
        from .contracts import RunReceipt as RR
        async with self.semaphore:
            state = world.reset(instance_id=instance_id, seed=seed)
            pstate = policy.initialize(world.world_spec)
            event_hashes: list[str] = []
            steps = 0
            while not world.terminal(state) and steps < max_steps:
                obs = world.observe(state)
                actions = world.actions(state)
                decision = policy.act(obs, actions, pstate)
                result = await self.registry.execute(decision.action)
                state = world.apply(state, decision.action, result)
                event_hashes.append(result.receipt_hash
                                    if hasattr(result, "receipt_hash")
                                    else content_id("evt", {
                                        "i": steps,
                                        "a": decision.action.action_id}))
                steps += 1
            metrics = (world.score(state)
                       if hasattr(world, "score") else MetricVector(metrics=()))
            cand = candidate or policy_as_candidate(policy)
            wp = getattr(world, "worldpack_id", None) or \
                content_id("wp", {"kind": world.world_spec.world_kind})
            scenario = {"spec": world.world_spec.spec_id,
                        "instance": instance_id}
            return RR(
                worldpack_id=wp, scenario=scenario,
                candidate_id=cand.candidate_id,
                candidate_config=dict(cand.config),
                seed=seed,
                event_hashes=tuple(event_hashes),
                metrics=metrics)


def policy_as_candidate(policy) -> CandidateArtifact:
    """Policies without an explicit artifact get one derived from identity."""
    from .contracts import CandidateArtifact
    return CandidateArtifact(kind="policy", version="1",
                             config={"policy_id": getattr(policy, "policy_id",
                                                          type(policy).__name__)})


async def run_suite_parallel(runner: AsyncRunner, make_world, policy,
                             suite: list[tuple[str, int]]) -> list[RunReceipt]:
    """Evaluate one policy across a suite CONCURRENTLY (bounded)."""
    tasks = [runner.run_episode(make_world(), policy, instance_id=i, seed=s)
             for i, s in suite]
    return list(await asyncio.gather(*tasks))
