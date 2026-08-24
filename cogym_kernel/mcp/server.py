"""MCP tool surface (M4 skeleton — thin over the CLI/kernel).

Tools: status, worlds, run_episode, query_experience.
Wire into any MCP client; transport-agnostic wrappers only.
"""
from __future__ import annotations

TOOLS = {
    "status": "kernel + hydra health",
    "worlds": "list registered worldpacks",
    "run_episode": "execute one episode; returns RunReceipt JSON (run_id is the proof)",
    "query_experience": "top verified policies on a world family",
}


def handle(tool: str, args: dict) -> dict:
    if tool == "status":
        from ..cli import _status
        import asyncio
        return asyncio.run(_status())
    if tool == "worlds":
        from ..worlds.registry import kinds
        return {"worlds": kinds()}
    if tool == "run_episode":
        import asyncio
        from .runner_tool import run_episode_tool
        return asyncio.run(run_episode_tool(args))
    if tool == "query_experience":
        import asyncio
        from cogym_kernel.experience.loop import top_policies
        from cogym_kernel.experience.client import HydraClient

        async def go():
            return await top_policies(HydraClient(), args["family"],
                                      int(args.get("limit", 5)))
        return {"leaders": asyncio.run(go())}
    raise KeyError(f"unknown tool '{tool}'. tools: {sorted(TOOLS)}")
