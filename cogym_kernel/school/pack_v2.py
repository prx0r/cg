"""Pack v0 — a content-addressed Context Program (docs/SCHOOL-INTEGRATION.md).

A Pack is compiled FROM the Hydra experience graph (leaders + lineage), carries
a decision contract and provenance, and is certified by our existing
three-tier verification on a probe suite. Hydra keeps evolving; a certified
Pack stays immutable. Not memory, not just a prompt: an education slice.

v0 scope: compile/certify/measure. No economy layer (deferred by thesis).
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field

from ..kernel.contracts import content_id


@dataclass(frozen=True)
class PackV0:
    name: str
    world_kind: str
    decision_contract: dict            # output format + gates reference
    induction_sequence: tuple[str, ...]   # ordered prompt/context fragments
    exemplar_refs: tuple[str, ...]     # receipt/graph keys this was distilled from
    target_signature_ref: str          # behavioral-signature id it aims to induce
    provenance: dict = field(default_factory=dict)

    @property
    def pack_id(self) -> str:
        """Content address over SEMANTIC fields only — provenance (timestamps,
        counters) must never drift the identity of identical programs."""
        d = self.to_dict()
        d.pop("provenance", None)
        return content_id("pack", d)

    def to_dict(self) -> dict:
        return asdict(self)

    def dumps(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def compile_pack_from_leaders(name: str, world_kind: str, leaders: list[dict],
                              decision_contract: dict,
                              max_fragments: int = 4) -> PackV0:
    """Compile a minimal context program from graph-known leaders.

    The induction sequence is ordered best-first; each fragment is advisory
    text derived from leader records. Compression comes from keeping only
    max_fragments fragments regardless of history size.
    """
    frags = []
    for i, l in enumerate(leaders[:max_fragments]):
        frags.append(
            f"[{i+1}] On {world_kind}, policy {l.get('pk')} achieved "
            f"util={l.get('util')}, cost={l.get('cost')}. "
            "Prefer consistent strategies when evidence ties.")
    return PackV0(
        name=name, world_kind=world_kind,
        decision_contract=dict(decision_contract),
        induction_sequence=tuple(frags),
        exemplar_refs=tuple(str(l.get("pk")) for l in leaders[:max_fragments]),
        target_signature_ref="",       # filled after probe-suite signature run
        provenance={"compiled_at_ns": time.time_ns(),
                    "source": "hydra.top_policies",
                    "n_leaders_considered": len(leaders)})


def certify(pack: PackV0, verification: dict) -> dict:
    """Attach a capability certificate from three-tier verification output."""
    cert = {
        "pack_id": pack.pack_id,
        "committed": True,             # pack bytes are content-addressed
        "verification_final": verification.get("final", {}).get("status"),
        "binary_outcome": (verification.get("binary") or {}).get("outcome"),
        "certified_at_ns": time.time_ns(),
        "note": ("layer1 commitment = pack hash; layer3 capability = "
                 "verification tiers; layer2 zkML inference proof deferred "
                 "(DeepProve path, optional)"),
    }
    return cert


# ---------- attestation (evolution_lab proofs.py lineage) ----------

def local_commitment_attestation(pack: PackV0, input_text: str,
                                 output_text: str, model_id: str) -> dict:
    """Integrity receipt only — hash commitments. NOT a zk proof of execution.
    An ExternalProofCommand adapter (DeepProve path) can be added later; the
    benchmark never fakes zkML (school_v2 PROOFS.md rule)."""
    return {
        "kind": "hash_commitment_only",
        "model_commitment": content_id("model", model_id),
        "input_commitment": content_id("input", input_text),
        "output_commitment": content_id("output", output_text),
        "pack_commitment": pack.pack_id,
    }
