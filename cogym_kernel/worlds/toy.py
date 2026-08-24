"""Toy worldpack: signal game. Ships as the reference distribution.

A hidden bit UP/DOWN; policies buy noisy evidence ($0.01 each, 75% reliable)
then commit. Quality gate: correct == 1.0. Cost minimization is the objective.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from ..kernel.contracts import (ActionResult, ActionSpec, Metric,
                                MetricVector, WorldSpec)


@dataclass
class State:
    seed: int
    truth_up: bool
    signals: tuple = field(default_factory=tuple)
    committed: str | None = None


class SignalWorld:
    def __init__(self, n_signals_available: int = 5):
        self.n = n_signals_available
        self._spec = None

    @property
    def world_spec(self) -> WorldSpec:
        if self._spec is None:
            self._spec = WorldSpec(
                world_kind="toy.signal_game", version="1",
                instance_set_hash="signal-instances-v1",
                environment_hash="rng-v1", oracle_hash="hidden-bit")
        return self._spec

    @property
    def worldpack_id(self) -> str:
        from ..kernel.ids import content_id
        return content_id("wp", {"kind": "toy.signal_game", "v": 1})

    def reset(self, *, instance_id: str, seed: int) -> State:
        return State(seed=seed, truth_up=random.Random(seed).random() < 0.5)

    def observe(self, state: State) -> dict:
        return {"bought": len(state.signals),
                "left": self.n - len(state.signals),
                "signals": list(state.signals)}

    def actions(self, state: State) -> tuple[ActionSpec, ...]:
        acts: list[ActionSpec] = []
        if len(state.signals) < self.n:
            acts.append(ActionSpec(kind="BUY_EVIDENCE", executor_kind="deterministic",
                                   estimated_cost=0.01))
        for s in ("UP", "DOWN"):
            acts.append(ActionSpec(kind="COMMIT", payload={"stance": s},
                                   executor_kind="deterministic"))
        return tuple(acts)

    def apply(self, state: State, action: ActionSpec,
              result: ActionResult) -> State:
        rng = random.Random(state.seed * 1000 + len(state.signals))
        if action.kind == "BUY_EVIDENCE":
            reading = state.truth_up if rng.random() < 0.75 else not state.truth_up
            return State(state.seed, state.truth_up, state.signals + (reading,),
                         state.committed)
        return State(state.seed, state.truth_up, state.signals,
                     action.payload["stance"])

    def terminal(self, state: State) -> bool:
        return state.committed is not None

    def score(self, state: State) -> MetricVector:
        correct = state.committed == ("UP" if state.truth_up else "DOWN")
        cost = round(0.01 * len(state.signals), 6)
        return MetricVector(metrics=(
            Metric("correct", 1.0 if correct else 0.0, "max"),
            Metric("cash_cost", cost, "min"),
            Metric("wall_latency_ms", 5.0 * (len(state.signals) + 1), "min"),
        ))


class CautiousPolicy:
    """Buy 3 signals, commit to majority."""
    policy_id = "toy.cautious_v1"

    def initialize(self, world_spec):
        return {}

    def act(self, obs, actions, pstate):
        from ..kernel.contracts import PolicyDecision
        if obs["bought"] < min(3, obs["left"] + obs["bought"]):
            a = next(a for a in actions if a.kind == "BUY_EVIDENCE")
            return PolicyDecision(action=a)
        ups = sum(1 for sg in obs["signals"] if sg)
        want = "UP" if ups >= max(1, len(obs["signals"])) / 2 else "DOWN"
        a = next(a for a in actions
                 if a.kind == "COMMIT" and a.payload["stance"] == want)
        return PolicyDecision(action=a)
