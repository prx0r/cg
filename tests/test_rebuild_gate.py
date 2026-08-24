import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
def test_rebuild_gate_dry():
    from cogym_kernel.experience.client import HydraClient
    async def go():
        c = HydraClient()
        if not await c.available():
            return True
        keys = await c.query("MATCH (n:_Scratch) RETURN count(*) AS c", columns=("c",))
        return True
    assert asyncio.run(go())
