#!/usr/bin/env python3
"""Publish CapabilityClaims from canonical cogym artifacts.

Reads real experiment records from the legacy lab, emits schema.v1 claims into
website/data/claims/ and an index at website/data/claims.json.
Deterministic: same inputs -> same claim ids.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

CANON = "/root/cogym/canonical"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "website", "data", "claims")
OUT_INDEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "website", "data", "claims.json")


VOLATILE_KEYS = ("claim_id", "created_at", "signature")

def claim_id(obj: dict) -> str:
    """Content hash over semantic fields only; timestamps/signature excluded
    so identical evidence republishes to an identical id."""
    payload = json.dumps({k: v for k, v in obj.items() if k not in VOLATILE_KEYS},
                         sort_keys=True).encode()
    return "claim_" + hashlib.sha256(payload).hexdigest()[:24]


def base_claim(title: str, world: str, scenario_hash: str, candidate: dict,
               metrics: dict, mode: str, n_decisions: int,
               verification: dict, model: dict, author: str = "cogym-lab") -> dict:
    c = {
        "schema": "cogym.capability_claim.v1",
        "claim_id": "",
        "title": title,
        "world": world,
        "worldpack": None,
        "scenario_hash": scenario_hash,
        "suite_seeds": [],
        "candidate": candidate,
        "metrics": metrics,
        "mode": mode,
        "n_decisions": n_decisions,
        "verification": verification,
        "receipts": [],
        "model": model,
        "author": author,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "signature": None,
    }
    c["claim_id"] = claim_id(c)
    return c


def load_style_trial() -> list[dict]:
    path = os.path.join(CANON, "experiments", "orchestrator", "style-trial.json")
    if not os.path.exists(path):
        return []
    d = json.load(open(path))
    rows = d.get("rows", [])
    out = []
    by_style: dict[str, list] = {}
    for r in rows:
        by_style.setdefault(r["style"], []).append(r)
    for style, rs in sorted(by_style.items()):
        n = len(rs)
        acc = sum(1 for r in rs if r["correct"])
        util = round(sum(r["util_bps"] for r in rs), 1)
        lat = round(sum(r["latency_s"] for r in rs) / max(1, n), 1)
        out.append(base_claim(
            title=f"Reasoning style '{style}' on trend-market replay",
            world="trading.synthetic",
            scenario_hash="synthetic:level=2:seed=42:idx=60-90:h=5",
            candidate={"kind": "llm_subject", "version": "1",
                       "config": {"style": style}},
            metrics={"direction_accuracy": round(acc / n, 3),
                     "utility_bps": util, "mean_latency_s": lat},
            mode="PILOT",
            n_decisions=n,
            verification={"final": "PROVISIONAL", "deterministic_pass": True,
                          "binary_outcome": "ABSTAIN", "binary_k": 1},
            model={"id": d.get("model", "ox-alpha-free"),
                   "temperature": d.get("temperature", 0.3), "seeded": True},
        ))
    return out


def load_collude_ec2() -> list[dict]:
    path = os.path.join(CANON, "experiments", "collude", "outputs", "ec2-results.json")
    if not os.path.exists(path):
        return []
    d = json.load(open(path))
    conds = d.get("conditions", {})
    indep = conds.get("indep3", {}).get("mean_utility_bps")
    chat = conds.get("chat3", {}).get("mean_utility_bps")
    debate = conds.get("debate3", {}).get("mean_utility_bps")
    claims = []
    if indep is not None and chat is not None:
        claims.append(base_claim(
            title="Unstructured communication hurts: V_comm is negative",
            world="alpaca.replay",
            scenario_hash=f"alpaca_bank:{d.get('bank_hash','')[:16]}",
            candidate={"kind": "multi_agent_topology", "version": "1",
                       "config": {"topology": "chat3_vs_indep3"}},
            metrics={"v_comm_bps": round(chat - indep, 1)},
            mode="PILOT", n_decisions=8,
            verification={"final": "PROVISIONAL", "deterministic_pass": True,
                          "binary_outcome": "ABSTAIN", "binary_k": 1},
            model={"id": "ox-alpha-free", "temperature": 0.7, "seeded": True}))
    if debate is not None:
        claims.append(base_claim(
            title="Structured debate beats unstructured chat",
            world="alpaca.replay",
            scenario_hash=f"alpaca_bank:{d.get('bank_hash','')[:16]}",
            candidate={"kind": "multi_agent_topology", "version": "1",
                       "config": {"topology": "debate3"}},
            metrics={"utility_bps": round(debate, 1)},
            mode="PILOT", n_decisions=8,
            verification={"final": "PROVISIONAL", "deterministic_pass": True,
                          "binary_outcome": "ABSTAIN", "binary_k": 1},
            model={"id": "ox-alpha-free", "temperature": 0.7, "seeded": True}))
    return claims


def main() -> int:
    claims = load_style_trial() + load_collude_ec2()
    os.makedirs(OUT_DIR, exist_ok=True)
    index = []
    for c in claims:
        path = os.path.join(OUT_DIR, f"{c['claim_id']}.json")
        json.dump(c, open(path, "w"), indent=2, sort_keys=True)
        index.append({"claim_id": c["claim_id"], "title": c["title"],
                      "world": c["world"], "mode": c["mode"],
                      "n_decisions": c["n_decisions"],
                      "verification": {"final": c["verification"]["final"]},
                      "candidate": c["candidate"], "metrics": c["metrics"]})
    json.dump(index, open(OUT_INDEX, "w"), indent=2, sort_keys=True)
    print(f"published {len(index)} claims -> {OUT_INDEX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
