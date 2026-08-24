"""State-induction metrics (thesis §'hypnosis', de-anthropomorphized).

Measures whether controlled context pushes a model into a reproducible
behavioral basin. All quantities are computed from logged decisions only.
"""
from __future__ import annotations

import math


def signature(stance_rates: dict[str, float], mean_confidence: float,
              sd_confidence: float) -> dict:
    """Minimal behavioral signature over a probe suite (v0 fields)."""
    return {"stance_rates": dict(stance_rates),
            "mean_confidence": round(mean_confidence, 4),
            "sd_confidence": round(sd_confidence, 4)}


def behavioral_distance(a: dict, b: dict) -> float:
    """L2 distance between two signatures (keys unioned, missing = 0)."""
    def flat(sig):
        out = {}
        for k, v in sig.get("stance_rates", {}).items():
            out[f"stance:{k}"] = v
        out["conf"] = sig.get("mean_confidence", 0.0)
        return out
    fa, fb = flat(a), flat(b)
    keys = set(fa) | set(fb)
    return round(math.sqrt(sum((fa.get(k, 0) - fb.get(k, 0)) ** 2
                               for k in keys)), 6)


def compression_ratio(full_history_tokens: int, pack_tokens: int) -> float:
    """tokens(H)/tokens(P): how much the education compressed."""
    if pack_tokens <= 0:
        return 0.0
    return round(full_history_tokens / pack_tokens, 2)


def retention(baseline_distance: float, post_reset_distance: float) -> dict:
    """Does the induced state survive a context reset?
    retention_ratio in [0,1]: 1 = fully retained after washout."""
    if baseline_distance <= 0:
        return {"retention_ratio": None}
    ratio = 1 - (post_reset_distance / baseline_distance)
    return {"baseline_distance": baseline_distance,
            "post_reset_distance": post_reset_distance,
            "retention_ratio": round(max(0.0, min(1.0, ratio)), 4)}
