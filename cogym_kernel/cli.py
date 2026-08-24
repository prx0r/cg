"""cogym CLI: status · worlds · run · claim. Thin over the kernel."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time


async def _status() -> dict:
    from . import __version__
    from .experience.client import HydraClient
    report: dict = {"package": "cogym-kernel", "version": __version__}
    try:
        c = HydraClient()
        avail = await c.available()
        report["hydra"] = {"graph": c.graph, "ready": c.ready(),
                           "available": avail}
    except Exception as e:  # noqa: BLE001
        report["hydra"] = f"error: {e}"
    return report


def _cmd_status(_) -> None:
    print(json.dumps(asyncio.run(_status()), indent=2))


def await_or(coro):
    return asyncio.get_event_loop().run_until_complete(coro) \
        if False else asyncio.run(coro)


def _cmd_worlds(_) -> None:
    from .worlds import registry
    print(json.dumps(registry.kinds(), indent=2))


def _cmd_run(args) -> None:
    from cogym_kernel.experience.client import HydraClient  # noqa: F401
    asyncio.run(_run(args))


async def _run(args) -> None:
    from .kernel.contracts import CandidateArtifact
    from .kernel.runner import AsyncRunner, ExecutorRegistry
    from .executors import DeterministicExecutor
    from .worlds.registry import create
    runner = AsyncRunner(ExecutorRegistry({"deterministic": DeterministicExecutor()}))
    world = create(args.world)
    # pick the world's own starter policy if available, else toy's
    try:
        mod_name = args.world.split(".")[0]
        mod = __import__(f"cogym_kernel.worlds.{mod_name}.world", fromlist=["CautiousPolicy"])
        PolicyCls = getattr(mod, "CautiousPolicy")
    except Exception:
        from .worlds.toy import CautiousPolicy as PolicyCls
    policy = PolicyCls()
    cand = CandidateArtifact(kind="cli", version="1", config={"seed_run": True})
    rec = await runner.run_episode(world, policy, instance_id="t",
                                   seed=args.seed, candidate=cand)
    receipt_json = rec.to_json()
    if getattr(args, "out", None):
        with open(args.out, "w") as fh:
            fh.write(receipt_json)
    print(receipt_json)


def _cmd_worldpack_export(args) -> None:
    import hashlib
    import tarfile
    art = os.path.join(args.out_dir,
                       f"{os.path.basename(args.path)}-v1.tar.gz")
    os.makedirs(args.out_dir, exist_ok=True)
    with tarfile.open(art, "w:gz") as tf:
        tf.add(args.path, arcname=os.path.basename(args.path))
    h = hashlib.sha256(open(art, "rb").read()).hexdigest()
    print(json.dumps({"artifact": art, "sha256": h}))


async def _evolve(args) -> None:
    from .kernel.contracts import CandidateArtifact
    from .kernel.runner import AsyncRunner, ExecutorRegistry
    from .executors import DeterministicExecutor
    from .worlds.registry import create
    from .worlds.toy import SignalWorld
    from .evo.loop import CampaignConfig, EvolutionCampaign
    from .experience.client import HydraClient

    runner = AsyncRunner(ExecutorRegistry({"deterministic": DeterministicExecutor()}))
    hydra = HydraClient() if not args.no_hydra else None
    if hydra and not await hydra.available():
        print("[evolve] hydra unavailable — running without experience memory", file=sys.stderr)
        hydra = None
    world_factory = lambda: create(args.world)
    # simple policy factory: strategy in config selects policy class
    def policy_factory(cand):
        strat = cand.config.get("strategy", "cautious")
        if strat == "reckless":
            class R:
                policy_id = "reckless"
                def initialize(self, ws): return {}
                def act(self, obs, actions, ps):
                    from .kernel.contracts import PolicyDecision
                    a = next(a for a in actions if a.kind == "COMMIT")
                    return PolicyDecision(action=a)
            return R()
        from .worlds.toy import CautiousPolicy
        return CautiousPolicy()

    import json as _json
    ss = json.loads(args.search_space) if getattr(args, "search_space", None) else {"strategy": ["cautious","reckless"]}
    cfg = CampaignConfig(world_kind=args.world, suite=[("t", 42+i) for i in range(args.suite_size)],
                         gates_metric="correct", generations=args.generations,
                         population=args.population, elite_k=2)
    seeds = [CandidateArtifact(kind="p", version="1", config={"strategy": s})
             for s in ["cautious", "reckless"][:args.population]]
    camp = EvolutionCampaign(world_factory=world_factory, policy_factory=policy_factory,
                             runner=runner, config=cfg, hydra_client=hydra,
                             recipe=args.recipe, search_space=ss)
    winners = await camp.run(seeds)
    print(json.dumps({"winners": [w.candidate_id[:16] for w in winners],
                      "generations": len(camp.generations),
                      "archive": len(camp.archive)}, indent=2))


def _cmd_evolve(args) -> None:
    asyncio.run(_evolve(args))


def _cmd_claim_create(args) -> None:
    rec = json.load(open(args.receipt_path))
    from .kernel.ids import keccak256
    claim = {
        "schema": "cogym.capability_claim.v1",
        "claim_id": "",
        "title": args.title or f"Run {rec.get('run_id', '?')[:18]}",
        "world": json.loads(rec.to_json()).get("scenario", {}).get(
            "spec", {}).get("world_kind", "unknown")
        if False else "see-receipt",
        "scenario_hash": rec.get("events_root", ""),
        "candidate": {"kind": "kernel_candidate",
                      "version": "1",
                      "config": rec.get("candidate_config", {})},
        "metrics": {m["name"]: m["value"] for m in rec.get("metrics", [])},
        "mode": "PILOT",
        "n_decisions": len(rec.get("event_hashes", [])),
        "verification": {"final": "PROVISIONAL"},
        "reproducibility": {
            "git_repo": "", "git_commit": "", "world_path": "",
            "deps_lock": "", "python_version": sys.version.split()[0],
            "api_transcripts": [],
            "run_command": f"cogym run --seed {rec.get('seed', 42)}"},
        "receipts": [rec.get("run_id", "")],
        "model": {"id": "n/a-deterministic", "temperature": 0, "seeded": True},
        "author": args.author,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "signature": None,
    }
    VOLATILE = ("claim_id", "created_at", "signature")
    payload = {k: v for k, v in claim.items() if k not in VOLATILE}
    cid = "claim_" + hashlib.sha256(json.dumps(
        payload, sort_keys=True).encode()).hexdigest()[:24]
    claim["claim_id"] = cid
    with open(args.out, "w") as fh:
        json.dump(claim, fh, indent=2, sort_keys=True)
    print(json.dumps({"claim_id": cid, "out": args.out}))


def main() -> None:
    p = argparse.ArgumentParser(prog="cogym")
    sub = p.add_subparsers(required=True)
    sub.add_parser("status", help="kernel + hydra health").set_defaults(fn=_cmd_status)
    sub.add_parser("worlds", help="list registered worldpacks").set_defaults(fn=_cmd_worlds)
    r = sub.add_parser("run", help="run one episode and print the RunReceipt")
    r.add_argument("--world", default="toy.signal_game")
    r.add_argument("--seed", type=int, default=42)
    r.add_argument("--out", help="also write receipt to this path")
    r.set_defaults(fn=_cmd_run)
    wp = sub.add_parser("worldpack-export", help="export a world dir as artifact")
    wp.add_argument("path")
    wp.add_argument("--out-dir", default="worldpacks")
    wp.set_defaults(fn=_cmd_worldpack_export)
    cl = sub.add_parser("claim-create", help="build CapabilityClaim from receipt")
    cl.add_argument("receipt_path")
    cl.add_argument("--title", default="")
    cl.add_argument("--author", default="cogym-kernel")
    cl.add_argument("--out", required=True)
    cl.set_defaults(fn=_cmd_claim_create)
    ev = sub.add_parser("evolve", help="run an evolution campaign")
    ev.add_argument("--world", default="toy.signal_game")
    ev.add_argument("--generations", type=int, default=2)
    ev.add_argument("--population", type=int, default=4)
    ev.add_argument("--suite-size", type=int, default=3)
    ev.add_argument("--recipe", default="elitist_mutation")
    ev.add_argument("--no-hydra", action="store_true")
    ev.add_argument("--search-space", help="JSON dict for search space")
    ev.set_defaults(fn=_cmd_evolve)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
