# MCP — agentic access to the lab

This kernel is an MCP server. Any MCP client (Claude Desktop, hermes) can operate it natively without learning the CLI.

## Transport

Today: **stdio** — `python3 -m cogym_kernel.mcp.server` speaks JSON-RPC 2.0 on stdin/stdout.

## Tools

| Tool | Args | Returns |
|------|------|---------|
| `status` | — | `{package, version, hydra: {graph, ready, available}}` |
| `worlds` | — | `{worlds: {kind: description}}` |
| `run_episode` | `seed` (int) | `RunReceipt` JSON (run_id is the proof) |
| `query_experience` | `family` (string), `limit` (int) | `{leaders: [{pk, util, cost}]}` |

Example client call (any MCP library):
```json
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"run_episode","arguments":{"seed":42}}}
```

Planned: streamable-http transport so a hosted lab can serve many clients.

## Adding a tool

1. Add entry to `mcp/server.py:TOOLS`.
2. Handle it in `handle(tool, args)`.
3. Add a test in `tests/test_mcp_stdio.py` that round-trips the tool.

All tools are thin over the CLI/kernel surface — same determinism, same gates, same receipts.
