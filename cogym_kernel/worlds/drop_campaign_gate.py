"""Drop Campaign Gate Worldpack — drop.campaign_gate-v1

A CG worldpack that evaluates Drop campaigns against the HCC v2 rubric.
Deterministic, content-addressed, reproducible.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from ..kernel.contracts import (ActionResult, ActionSpec, Metric,
                                MetricVector, WorldSpec)
from .registry import register


@dataclass
class State:
    seed: int
    campaign: dict
    evidence: dict
    rubric: dict
    gates: dict = field(default_factory=dict)
    score: int = 0
    verdict: str | None = None


@register("drop.campaign_gate", "Drop campaign evaluation against HCC v2 rubric")
class DropCampaignGateWorld:
    """Evaluates Drop campaigns against the HCC v2 rubric."""

    def __init__(self):
        self._spec = None

    @property
    def world_spec(self) -> WorldSpec:
        if self._spec is None:
            self._spec = WorldSpec(
                world_kind="drop.campaign_gate", version="1",
                instance_set_hash="drop-campaigns-v1",
                environment_hash="rubric-hcc-v2",
                oracle_hash="evidence-bundle")
        return self._spec

    @property
    def worldpack_id(self) -> str:
        from ..kernel.ids import content_id
        return content_id("wp", {"kind": "drop.campaign_gate", "v": 1})

    def reset(self, *, instance_id: str, seed: int) -> State:
        # Load campaign and evidence from instance_id
        # For now, return empty state
        return State(seed=seed, campaign={}, evidence={}, rubric={})

    def observe(self, state: State) -> dict:
        return {
            "campaign_id": state.campaign.get("campaign_id", "unknown"),
            "track": state.campaign.get("track", "unknown"),
            "country": state.campaign.get("country", "??"),
            "gates": state.gates,
            "score": state.score,
            "verdict": state.verdict
        }

    def actions(self, state: State) -> tuple[ActionSpec, ...]:
        if state.verdict is not None:
            return ()  # Terminal
        return (
            ActionSpec(kind="EVALUATE_GATES", executor_kind="deterministic"),
            ActionSpec(kind="SCORE_RUBRIC", executor_kind="deterministic"),
        )

    def apply(self, state: State, action: ActionSpec,
              result: ActionResult) -> State:
        if action.kind == "EVALUATE_GATES":
            gates = self._evaluate_gates(state.campaign, state.evidence)
            return State(state.seed, state.campaign, state.evidence,
                        state.rubric, gates, state.score, state.verdict)
        elif action.kind == "SCORE_RUBRIC":
            score = self._score_rubric(state.campaign, state.evidence, state.gates)
            verdict = self._determine_verdict(state.gates, score)
            return State(state.seed, state.campaign, state.evidence,
                        state.rubric, state.gates, score, verdict)
        return state

    def terminal(self, state: State) -> bool:
        return state.verdict is not None

    def score(self, state: State) -> MetricVector:
        return MetricVector(metrics=(
            Metric("score", float(state.score), "max"),
            Metric("gates_pass", float(sum(1 for v in state.gates.values() if v == "PASS")), "max"),
            Metric("gates_fail", float(sum(1 for v in state.gates.values() if v == "FAIL")), "min"),
            Metric("gates_unknown", float(sum(1 for v in state.gates.values() if v == "UNKNOWN")), "min"),
        ))

    def _evaluate_gates(self, campaign: dict, evidence: dict) -> dict:
        """Evaluate all 12 hard gates."""
        gates = {}

        # G1: Installed base exists
        gates["G1"] = "PASS" if evidence.get("installed_base_verified") else "UNKNOWN"

        # G2: Lifecycle trigger exists
        gates["G2"] = "PASS" if evidence.get("lifecycle_trigger_verified") else "UNKNOWN"

        # G3: Compatibility problem exists
        gates["G3"] = "PASS" if evidence.get("compatibility_verified") else "UNKNOWN"

        # G4: Buyer autonomy verified
        gates["G4"] = "PASS" if evidence.get("buyer_role_verified") else "UNKNOWN"

        # G5: Local supply exists
        gates["G5"] = "PASS" if evidence.get("supply_verified") else "UNKNOWN"

        # G6: Ownership gap verified
        gates["G6"] = "PASS" if evidence.get("ownership_gap_verified") else "UNKNOWN"

        # G7: Reseller path verified
        gates["G7"] = "PASS" if evidence.get("reseller_verified") else "UNKNOWN"

        # G8: Economics verified
        gates["G8"] = "PASS" if evidence.get("economics_verified") else "UNKNOWN"

        # G9: Demand verified
        gates["G9"] = "PASS" if evidence.get("demand_verified") else "UNKNOWN"

        # G10: Operations verified
        gates["G10"] = "PASS" if evidence.get("operations_verified") else "UNKNOWN"

        # G11: Feed completeness
        gates["G11"] = "PASS" if evidence.get("feed_complete") else "UNKNOWN"

        # G12: Retrieval whitespace
        gates["G12"] = "PASS" if evidence.get("retrieval_whitespace") else "UNKNOWN"

        return gates

    def _score_rubric(self, campaign: dict, evidence: dict, gates: dict) -> int:
        """Score the campaign based on evidence."""
        score = 0

        # Information rent (30 points)
        if evidence.get("identity_requires_photo"):
            score += 10
        if evidence.get("wrong_part_cost_high"):
            score += 10
        if evidence.get("supersession_complex"):
            score += 10

        # Installed-base economics (20 points)
        if evidence.get("installed_base_large"):
            score += 10
        if evidence.get("replacement_frequency"):
            score += 10

        # Supplier arbitrage (30 points)
        if evidence.get("multiple_suppliers"):
            score += 10
        if evidence.get("supplier_has_feed"):
            score += 10
        if evidence.get("supplier_direct_ship"):
            score += 10
        elif evidence.get("supplier_direct_ship") is False:
            score -= 10

        # Distribution fit (20 points)
        if evidence.get("small_parcel"):
            score += 10
        if evidence.get("photo_identifiable"):
            score += 10

        # Economics (30 points)
        if evidence.get("aov_high"):
            score += 10
        elif evidence.get("aov_high") is False:
            score -= 10
        if evidence.get("margin_verified"):
            score += 10
        if evidence.get("wrong_part_rate_low"):
            score += 10
        elif evidence.get("wrong_part_rate_low") is False:
            score -= 10

        # Market position (30 points)
        if evidence.get("best_specialist_weak"):
            score += 10
        elif evidence.get("best_specialist_weak") is False:
            score -= 10
        if evidence.get("oem_not_competing"):
            score += 10
        elif evidence.get("oem_not_competing") is False:
            score -= 10
        if evidence.get("marketplace_not_dominant"):
            score += 10
        elif evidence.get("marketplace_not_dominant") is False:
            score -= 10

        # Language/native (20 points)
        if evidence.get("native_language_advantage"):
            score += 10
        if evidence.get("local_terminology_nontrivial"):
            score += 10

        # Agent/distribution (20 points)
        if evidence.get("fits_gmc"):
            score += 10
        if evidence.get("fits_shopify"):
            score += 10

        return score

    def _determine_verdict(self, gates: dict, score: int) -> str:
        """Determine verdict based on gates and score."""
        # If any gate is UNKNOWN, block
        if any(v == "UNKNOWN" for v in gates.values()):
            return "BLOCKED"

        # If any gate is FAIL, reject
        if any(v == "FAIL" for v in gates.values()):
            return "REJECT"

        # Score thresholds
        if score >= 160:
            return "ATTACK"
        elif score >= 120:
            return "VERIFY"
        elif score >= 80:
            return "SCAN"
        else:
            return "REJECT"
