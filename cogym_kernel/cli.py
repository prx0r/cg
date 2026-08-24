"""cogym CLI: status · worlds · run · claim. Thin over the kernel."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys


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
    from .worlds.toy import CautiousPolicy  # default policy set per worldpack
    runner = AsyncRunner(ExecutorRegistry({"deterministic": DeterministicExecutor()}))
    world = create(args.world)
    policy = CautiousPolicy()
    cand = CandidateArtifact(kind="cli", version="1", config={"seed_run": True})
    rec = await runner.run_episode(world, policy, instance_id="t",
                                   seed=args.seed, candidate=cand)
    print(rec.to_json())


def main() -> None:
    p = argparse.ArgumentParser(prog="cogym")
    sub = p.add_subparsers(required=True)
    sub.add_parser("status", help="kernel + hydra health").set_defaults(fn=_cmd_status)
    sub.add_parser("worlds", help="list registered worldpacks").set_defaults(fn=_cmd_worlds)
    r = sub.add_parser("run", help="run one episode and print the RunReceipt")
    r.add_argument("--world", default="toy.signal_game")
    r.add_argument("--seed", type=int, default=42)
    r.set_defaults(fn=_cmd_run)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
