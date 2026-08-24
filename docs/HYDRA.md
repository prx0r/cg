# HYDRA.md — experience memory setup & usage

HydraDB is cogymkernel's **derived** experience store: written after
evaluation, read before proposal. Canonical truth is always local files
(receipts, findings). Deleting Hydra destroys nothing — `rebuild()` replays.

## Bring-up

```bash
mkdir -p hydradb-data/store hydradb-data/cache
printf '%s\n' 'local-dev-token-must-be-32-chars-min' > hydradb-data/auth-token

docker run -d --name hydradb --user 10001:10001 \
  -p 7687:7687 -p 8443:8443 -p 9090:9090 \
  -v "$PWD/hydradb-data:/data" \
  -e CLOUD_PROVIDER=local -e LOCAL_PATH=/data/store \
  -e GRAPH_NAMESPACE=default -e GRAPH_ID=cogym -e GRAPH_CELL_ID=cell-0 \
  -e GRAPH_CELLS=cell-0 -e GRAPH_NODE_ID=node-0 \
  -e GRAPH_BOLT_NODE_ADDRESSES=node-0=127.0.0.1:7687 \
  -e GRAPH_ADVERTISED_BOLT_ADDR=127.0.0.1:7687 \
  -e GRAPH_DATA_CACHE_DIR=/data/cache \
  -e GRAPH_AUTH_TOKEN_FILE=/data/auth-token \
  -e GRAPH_ALLOW_PLAINTEXT=true -e RUST_MIN_STACK=33554432 \
  ghcr.io/hydra-db/hydradb:latest
```

**Critical:** the container runs as uid 10001 — `chown -R 10001:10001
hydradb-data` or every write fails with Permission denied inside writer leases.

## Verify (a listening port is not proof)

```python
import asyncio
from cogym_kernel.experience.client import HydraClient

async def main():
    c = HydraClient()
    print("ready:", c.ready(), "| available:", await c.available())
asyncio.run(main())
```

## What the kernel writes

Association-node schema (`docs/` in legacy repo has full rationale):
- `(REL_RAN_ON {src_key, dst_key, quality_pass, mean_utility_bps, cash_cost…})`
- `(REL_IMPROVED_ON|REGRESSION {delta_bps, vs})`, `(REL_MUTATED_FROM {})`
- epistemic chain: Experiment—TESTED→Hypothesis—PRODUCED→Finding—SEEDS→next

Read path (the learning loop):
```python
rows = await client.query(
  "MATCH (e:REL_RAN_ON {dst_key: $f}) WHERE e.quality_pass = true "
  "RETURN e.src_key AS pk, e.cash_cost AS cost ORDER BY cost ASC LIMIT $n",
  {"f": "worldfamily:toy.signal_game"}, ("pk", "cost"))
```

## Verified quirks of image db78309a (see legacy INTEGRATION-NOTES)

- Writes ONLY via HTTP :8443 (Bolt is read-only)
- CREATE = one-hop edge pattern, both endpoints born in-statement
- No MATCH+CREATE / MERGE+SET / UNWIND → association nodes + ensure_node()
- Node ids are integers; our string keys are the logical identity
- Only the boot env's graph scope is authorized (`default/graphs/cogym`)
- Reads: no bare `MATCH (n)`; VLP needs fixed int-id source

## Rebuild test (§56, CI-gated)

```bash
python3 -m cogym_kernel.experience.rebuild    # wipe → replay receipts → diff
# exit 0 + lost==[] means the graph is fully derivable from canonical files
```
