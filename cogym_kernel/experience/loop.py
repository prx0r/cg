"""Experience loop: write-after-evaluate, read-before-propose (async)."""
from __future__ import annotations
from dataclasses import dataclass

from .client import Edge, HydraClient, HydraError, NodeRef, apply_ops


@dataclass
class LoopStats:
    projections_ok: int = 0
    projections_failed: int = 0
    informed_proposals: int = 0
    fallback_proposals: int = 0


async def aavailable(client: HydraClient) -> bool:
    return await client.available()


async def project_performance(client: HydraClient, policy_key: str,
                              family_key: str, *, metrics: dict,
                              quality_pass: bool | None = None) -> None:
    pol = NodeRef("Policy", f"policy:{policy_key}", {"kind_label": "candidate"})
    fam = NodeRef("WorldFamily", f"worldfamily:{family_key}", {})
    props = {k: v for k, v in metrics.items() if v is not None}
    if quality_pass is not None:
        props["quality_pass"] = bool(quality_pass)
    await client.ensure_node(pol)
    await client.ensure_node(fam)
    await client.put_edge(Edge("RAN_ON", pol, fam, props))


async def top_policies(client: HydraClient, family_key: str,
                       limit: int = 5) -> list[dict]:
    try:
        rows = await client.query(
            "MATCH (e:REL_RAN_ON {dst_key: $f}) WHERE e.quality_pass = true "
            "RETURN e.src_key AS pk, e.mean_utility_bps AS util, "
            "e.cash_cost AS cost ORDER BY util DESC LIMIT $n",
            {"f": f"worldfamily:{family_key}", "n": limit},
            ("pk", "util", "cost"))
        return rows
    except HydraError:
        return []
