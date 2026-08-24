"""Runnable MCP-style stdio server for cogymkernel tools.

Protocol: newline-delimited JSON-RPC 2.0 on stdin/stdout (synchronous loop;
robust under pipes). Run: python3 -m cogym_kernel.mcp.server
"""
from __future__ import annotations

import json
import sys

from .server import TOOLS, handle


def _descriptions():
    return [{"name": t, "description": d} for t, d in sorted(TOOLS.items())]


def _dispatch(method: str, params: dict):
    if method == "initialize":
        return {"protocolVersion": "2026-06-01",
                "serverInfo": {"name": "cogymkernel", "version": "0.1.0"},
                "tools": _descriptions()}
    if method == "tools/list":
        return {"tools": _descriptions()}
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        return {"content": [{"type": "text",
                             "text": json.dumps(handle(name, args))}]}
    raise KeyError(f"unknown method {method}")


def serve() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        rid, method, params = req.get("id"), req.get("method"), req.get("params", {})
        try:
            result = _dispatch(method, params)
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid,
                                         "result": result}) + "\n")
        except Exception as e:  # noqa: BLE001 - JSON-RPC errors are responses
            sys.stdout.write(json.dumps(
                {"jsonrpc": "2.0", "id": rid,
                 "error": {"code": -32000, "message": str(e)[:300]}}) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    serve()
