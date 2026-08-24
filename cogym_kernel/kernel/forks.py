"""Decision-fork identifiers (thesis: deterministic context forks)."""
from __future__ import annotations
from .ids import content_id
def decision_fork_id(*, timestamp: str, context_hash: str, model: str,
                     cognition_policy: str, memory_version: str,
                     random_seed: int | str) -> str:
    return content_id("fork", {"ts": timestamp, "ctx": context_hash, "model": model,
                               "policy": cognition_policy, "mem": memory_version, "seed": random_seed})
def scenario_fork_id(base_scenario_hash: str, **overrides: str) -> str:
    return content_id("scenfork", {"base": base_scenario_hash, **overrides})
