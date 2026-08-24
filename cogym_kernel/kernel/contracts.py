"""Kernel contracts: frozen dataclasses for world/policy/executor/candidate.

Ported from canonical/core/contracts.py, cleaned: stdlib frozen dataclasses,
volatile fields excluded from identities at the id layer (GIT-LEDGER.md).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

from .ids import content_id


@dataclass(frozen=True)
class WorldSpec:
    world_kind: str
    version: str
    instance_set_hash: str
    environment_hash: str
    oracle_hash: str            # evaluator-side only; never in observations
    metadata: dict = field(default_factory=dict)

    @property
    def spec_id(self) -> str:
        return content_id("worldspec", self)


@dataclass(frozen=True)
class ActionSpec:
    kind: str
    payload: dict = field(default_factory=dict)
    executor_kind: str = "deterministic"
    estimated_cost: float | None = None
    timeout_ms: int | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def action_id(self) -> str:
        return content_id("action", {"kind": self.kind, "payload": self.payload})


@dataclass(frozen=True)
class ActionResult:
    action_id: str
    status: Literal["ok", "error", "timeout"]
    payload: dict = field(default_factory=dict)
    started_ns: int = 0
    finished_ns: int = 0
    wall_ms: float = 0.0
    cash_cost: float = 0.0
    normalized_cost: float = 0.0
    provider: str = ""
    request_hash: str = ""
    response_hash: str = ""
    cache_hit: bool = False
    error: str | None = None


@dataclass(frozen=True)
class Metric:
    name: str
    value: float
    direction: Literal["min", "max"]


@dataclass(frozen=True)
class MetricVector:
    metrics: tuple[Metric, ...]

    def get(self, name: str) -> float | None:
        return next((m.value for m in self.metrics if m.name == name), None)

    def names(self) -> tuple[str, ...]:
        return tuple(m.name for m in self.metrics)


@dataclass(frozen=True)
class CandidateArtifact:
    kind: str
    version: str
    config: dict
    parent_ids: tuple[str, ...] = ()
    provenance: dict = field(default_factory=dict)

    @property
    def candidate_id(self) -> str:
        return content_id("cand", {"kind": self.kind, "version": self.version,
                                   "config": self.config,
                                   "parents": self.parent_ids})


@dataclass(frozen=True)
class RunReceipt:
    """The proof primitive: content-addressed execution record (GIT-LEDGER.md)."""
    worldpack_id: str
    scenario: dict                 # Σ commitment: spec + suite config
    candidate_id: str
    candidate_config: dict
    seed: int
    event_hashes: tuple[str, ...]
    metrics: MetricVector

    @property
    def events_root(self) -> str:
        from .ids import events_root
        return events_root(list(self.event_hashes))

    @property
    def run_id(self) -> str:
        from .ids import content_id
        return content_id("run", {
            "worldpack": self.worldpack_id,
            "scenario": self.scenario,
            "candidate": self.candidate_id,
            "seed": self.seed,
            "events_root": self.events_root,
        })

    def to_json(self) -> str:
        d: dict[str, Any] = {
            "worldpack_id": self.worldpack_id,
            "scenario": self.scenario,
            "candidate_id": self.candidate_id,
            "candidate_config": self.candidate_config,
            "seed": self.seed,
            "event_hashes": list(self.event_hashes),
            "events_root": self.events_root,
            "run_id": self.run_id,
            "metrics": [{"name": m.name, "value": m.value,
                         "direction": m.direction}
                        for m in self.metrics.metrics],
        }
        return json.dumps(d, indent=2, sort_keys=True)


@dataclass(frozen=True)
class PolicyDecision:
    action: ActionSpec
    rationale: str = ""
    confidence: float | None = None
