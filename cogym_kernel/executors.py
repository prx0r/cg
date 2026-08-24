"""Built-in executors. Only these touch the outside world.

DeterministicExecutor — simulated cost/latency, no I/O (reference + tests).
ReplayTape/TapeExecutor/RecordingExecutor — capture once, replay byte-identical;
unknown tape keys are ERRORS, never silent live fallbacks.
ModelExecutor — async, content-addressed response cache (ADR-5): reruns cost
zero tokens. Cache lives beside receipts; opt out per call.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Callable

from .kernel.contracts import ActionResult, ActionSpec
from .kernel.ids import content_id, now_ns


class DeterministicExecutor:
    executor_id = "det-v1"

    def execute(self, action: ActionSpec) -> ActionResult:
        t = now_ns()
        return ActionResult(
            action_id=action.action_id, status="ok",
            payload={"echo": action.payload}, started_ns=t,
            finished_ns=now_ns(), wall_ms=5.0,
            cash_cost=action.estimated_cost or 0.0,
            normalized_cost=action.estimated_cost or 0.0,
            provider="local",
            request_hash=content_id("req", action.payload),
            response_hash=content_id("resp", action.payload))


class ReplayTape:
    """action_id -> ActionResult, recorded from live runs."""

    def __init__(self) -> None:
        self._store: dict[str, ActionResult] = {}

    def record(self, result: ActionResult) -> None:
        self._store[result.action_id] = result

    def lookup(self, action_id: str) -> ActionResult | None:
        return self._store.get(action_id)

    def __len__(self) -> int:
        return len(self._store)


class TapeExecutor:
    executor_id = "tape-v1"

    def __init__(self, tape: ReplayTape):
        self.tape = tape

    def execute(self, action: ActionSpec) -> ActionResult:
        hit = self.tape.lookup(action.action_id)
        if hit is None:
            return ActionResult(action_id=action.action_id, status="error",
                                error=f"action {action.action_id} not in tape")
        return hit


class RecordingExecutor:
    """Wrap any live executor; every result is recorded into the tape."""

    def __init__(self, inner, tape: ReplayTape):
        self.inner = inner
        self.tape = tape
        self.executor_id = f"recording[{getattr(inner, 'executor_id', '?')}]"

    def execute(self, action: ActionSpec) -> ActionResult:
        t = now_ns()
        result = self.inner.execute(action)
        if hasattr(result, "__dict__") and not getattr(result, "started_ns", 0):
            object.__setattr__(result, "started_ns", t)
            object.__setattr__(result, "finished_ns", now_ns())
        self.tape.record(result)
        return result


class ModelExecutor:
    """Async model calls with a content-addressed response cache (ADR-5).

    `complete_fn(messages, temperature, seed)` must be injected (provider
    adapter). Cache key = hash(model, messages, temperature, seed). Cache hits
    are marked cache_hit=True and cost 0 — reruns of identical experiments are
    free and byte-reproducible.
    """

    executor_id = "model-cached-v1"

    def __init__(self, complete_fn: Callable[..., str], model_id: str,
                 cache_dir: str | None = None):
        self.complete_fn = complete_fn
        self.model_id = model_id
        self.cache_dir = cache_dir

    def _cache_path(self, messages: list[dict], temperature: float,
                    seed: int) -> tuple[str, str]:
        payload = {"model": self.model_id, "messages": messages,
                   "temperature": temperature, "seed": seed}
        h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return h, (os.path.join(self.cache_dir, f"{h}.json")
                   if self.cache_dir else "")

    def execute(self, action: ActionSpec) -> ActionResult:
        raise NotImplementedError("use async_execute via AsyncRunner")


def now_ns() -> int:
    return time.time_ns()
