import asyncio
from ..kernel.runner import AsyncRunner, ExecutorRegistry
from ..executors import DeterministicExecutor
from ..worlds.registry import create


async def run_episode_tool(args: dict) -> dict:
    runner = AsyncRunner(ExecutorRegistry({"deterministic": DeterministicExecutor()}))
    world = create(args.get("world", "toy.signal_game"))
    from ..worlds.toy import CautiousPolicy
    rec = await runner.run_episode(world, CautiousPolicy(),
                                   instance_id=args.get("instance", "t"),
                                   seed=int(args.get("seed", 42)))
    return json.loads(rec.to_json()) if (json := __import__("json")) else {}
