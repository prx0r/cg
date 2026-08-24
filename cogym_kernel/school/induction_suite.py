"""Induction regression harness: does a style/context still induce its basin?

Runs a probe suite under (style, seed_context) vs neutral baseline for an LLM
subject, computes behavioral signatures + distance + retention, and projects
results into Hydra as REL_INDUCED edges keyed by model+style+suite hash.

This is the School thesis's stability axis: re-run after any model update;
distance drift = the induction broke.
"""
from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass

from ..kernel.forks import decision_fork_id
from ..evo.reasoning_styles import apply_style
from .induction import behavioral_distance, signature


@dataclass
class Probe:
    instance_id: str
    observation: str
    expected_stance: str | None = None     # optional; accuracy secondary here


def _parse_stance(raw: str) -> str | None:
    import re
    m = re.search(r'"stance"\s*:\s*"?(UP|DOWN|LONG|SHORT)', raw or "", re.I)
    if not m:
        return None
    v = m.group(1).upper()
    return "UP" if v in ("UP", "LONG") else "DOWN"


def run_signature(model, probes: list[Probe], *,
                  system: str, style_id: str = "direct",
                  seed_context: str | None = None,
                  temperature: float = 0.3, seed_base: int = 7) -> dict:
    try:
        from cogym_kernel.executors import ModelExecutor  # noqa
    except ImportError: pass
    stances, confs = [], []
    for i, p in enumerate(probes):
        sysmsg = apply_style(system, style_id, seed_context=seed_context)
        user = p.observation + ('\nReply ONLY JSON: {"stance":"UP"|"DOWN",'
                                '"confidence":0-100}')
        try:
            from cogym_kernel.executors import ModelExecutor as _M2
            raw = model.complete([{"role": "system", "content": sysmsg},
                                  {"role": "user", "content": user}],
                             temperature=temperature, seed=seed_base + i)
        except Exception:
            raw = model.complete([{"role": "system", "content": sysmsg},
                                  {"role": "user", "content": user}],
                                 temperature=temperature, seed=seed_base + i)
        stance = _parse_stance(raw) or "NONE"
        stances.append(stance)
        import re
        mc = re.search(r'"confidence"\s*:\s*([0-9]{1,3})', raw or "")
        confs.append((int(mc.group(1)) if mc else 50) / 100.0)
    n = max(1, len(stances))
    rates = {s: stances.count(s) / n for s in ("UP", "DOWN")}
    mean_c = sum(confs) / n
    var = sum((c - mean_c) ** 2 for c in confs) / n
    return signature(rates, mean_c, math.sqrt(var))


def regression_entrypoint(model, probes: list[Probe], *,
                          styles: list[str], system: str,
                          suite_hash: str, hydra_client=None,
                          seed_context: str | None = None) -> dict:
    """Baseline vs each style; distance + Hydra projection."""
    base_sig = run_signature(model, probes, system=system, style_id="neutral"
                             if "neutral" in __import__("cogym.evolution."
                                "reasoning_styles", fromlist=["STYLES"]).STYLES
                             else "direct")
    entries = []
    for sid in styles:
        sig = run_signature(model, probes, system=system, style_id=sid,
                            seed_context=seed_context)
        dist = behavioral_distance(base_sig, sig)
        fork = decision_fork_id(
            timestamp=time.strftime("%Y-%m-%d"), context_hash=suite_hash,
            model=getattr(model, "model_id", "unknown"),
            cognition_policy=sid, memory_version="v0",
            random_seed=len(probes))
        entries.append({"style": sid, "signature": sig,
                        "distance_from_baseline": dist, "fork_id": fork})
        if hydra_client is not None:
            try:
                from ..experience.client import Edge, NodeRef
                pol = NodeRef("Policy", f"{suite_hash}:{sid}", {})
                fam = NodeRef("WorldFamily",
                              f"worldfamily:induction:{suite_hash}", {})
                edge = Edge("INDUCED_DISTANCE", pol, fam,
                            {"distance": dist}).to_node_ref()
                from ..experience.client import ensure_node
                ensure_node(hydra_client, pol)
                ensure_node(hydra_client, fam)
                ensure_node(hydra_client, edge)
            except Exception as e:  # noqa: BLE001 - hydra is derived, never fatal
                print(f"[induction] hydra projection skipped: {e}")
    import json as _json
    return {"suite_hash": suite_hash, "baseline_signature": base_sig,
            "entries": entries}

