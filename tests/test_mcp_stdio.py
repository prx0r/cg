"""MCP stdio server: initialize, tools/list, tools/call over real stdio."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_stdio_roundtrip():
    import subprocess
    proc = subprocess.Popen(
        [sys.executable, "-m", "cogym_kernel.mcp.stdio"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True)

    def send(obj):
        proc.stdin.write(json.dumps(obj) + "\n"); proc.stdin.flush()

    def recv():
        line = proc.stdout.readline()
        return json.loads(line) if line else {}

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        r = recv()
        assert r["result"]["serverInfo"]["name"] == "cogymkernel"
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        r = recv()
        names = [t["name"] for t in r["result"]["tools"]]
        assert {"run_episode", "query_experience"} <= set(names)
        send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
              "params": {"name": "run_episode",
                         "arguments": {"seed": 42}}})
        r = recv()
        inner = json.loads(r["result"]["content"][0]["text"])
        assert inner["run_id"].startswith("run_")
    finally:
        proc.terminate()
