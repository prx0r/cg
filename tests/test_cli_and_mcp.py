import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_status_reports_hydra():
    from cogym_kernel.cli import _status
    r = asyncio_run(_status())
    assert r["package"] == "cogym-kernel"
    assert isinstance(r["hydra"], dict)


def test_mcp_tools_surface():
    from cogym_kernel.mcp.server import TOOLS, handle
    assert set(TOOLS) >= {"status", "worlds", "run_episode", "query_experience"}
    out = handle("worlds", {})
    assert "toy.signal_game" in out["worlds"]


def test_mcp_run_episode_returns_receipt():
    from cogym_kernel.mcp.server import handle
    r = handle("run_episode", {"seed": 42})
    assert r["run_id"].startswith("run_")
    assert any(m["name"] == "correct" for m in r["metrics"])


def asyncio_run(coro):
    import asyncio
    return asyncio.run(coro)
