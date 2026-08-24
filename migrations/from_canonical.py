"""Import canonical receipts into kernel's Hydra experience graph.

Usage:
  python3 -m migrations.from_canonical --dry-run
  python3 -m migrations.from_canonical

Canonical sources (on disk in legacy lab):
  canonical/experiments/collude/outputs/ec*-results.json  COLLUDE pilots
  canonical/experiments/orchestrator/cycles/*/FINDINGS.json  cycles
  canonical/experiments/orchestrator/outputs/*.json         campaign receipts

This importer is best-effort: missing files are skipped with a note.
Every run is idempotent (claim ids are content-addressed); reruns don't dupe.
"""
from __future__ import annotations
import glob, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CANON = os.environ.get("COGYM_CANON_ROOT", "/root/cogym/canonical")

def import_collude(dry_run=False):
    from cogym_kernel.experience.client import HydraClient, NodeRef, Edge
    import asyncio
    async def go():
        c = HydraClient()
        if not await c.available():
            print("[import] hydra unavailable — dry_run only"); return 0
        n=0
        for p in sorted(glob.glob(os.path.join(CANON, "experiments/collude/outputs/ec*-results.json"))):
            d=json.load(open(p)); 
            for k,v in d.get("conditions",{}).items():
                pol=NodeRef("Policy", f"{k}", {})
                fam=NodeRef("WorldFamily", f"collude:{p}", {})
                if not dry_run:
                    await c.ensure_node(pol); await c.ensure_node(fam)
                    await c.ensure_node(Edge("RAN_ON", pol, fam, {"sample":1}).to_node())
                n+=1
        return n
    import asyncio; return asyncio.run(go())

if __name__ == "__main__":
    import argparse; ap=argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true")
    a=ap.parse_args()
    print(f"import dry_run={a.dry_run}: {import_collude(dry_run=a.dry_run)} records scanned")
