# HydraDB — Official Integration Reference

> **Status:** `cogymkernel` integration `v0.1.0` · HydraDB image `db78309a` (2026-08-12) · Upstream: [hydra-db/hydradb](https://github.com/hydra-db/hydradb) (docs describe `main`; this file documents the **verified** surface of the pinned image).
>
> **Role in cogymkernel:** derived experience memory. Truth lives in files (`runs/*.json`, `claims/*.json`). Hydra is a queryable *view* — `experience/rebuild` recreates it from scratch. If Hydra died, nothing is lost.

---

## 1. What HydraDB actually is

HydraDB is a Rust graph database (30+ crates) built on **SlateDB**, an LSM-tree that writes to S3-compatible object storage. In development the "object store" is a local directory (`/data/store`); in production it is S3. No Postgres. No RocksDB. The only durable thing is objects in a bucket — everything else (WAL, manifests, indexes) is cache that can be rebuilt.

```
your code  →  HydraClient  ──HTTP :8443──►  graph-node (query + WAL writer, one per cell)
                                    └──Bolt :7687──►  (read-only on this image)
                                            │
                                            ▼
                                     SlateDB WAL + SSTs + manifests  →  /data/store  (or S3)
                                            │
                                            └────►  graph-indexer  →  CSC generations  →  /data/store/_graph_index/
```

**GraphScope** = `namespace / graph_id / cell`. Every deployment pins one scope per request. We use a single scope:

| Field | Value |
|-------|-------|
| `GRAPH_NAMESPACE` | `default` |
| `GRAPH_ID` | `cogym` |
| `GRAPH_CELL_ID` | `cell-0` |
| `GRAPH_CELLS` | `cell-0` |

Graph-scope + cell + read epoch pins every query to one SlateDB snapshot — no torn reads, no phantom writes.

### Upstream docs (read these first)

| Doc | What it covers |
|-----|----------------|
| HydraDB [README](https://github.com/hydra-db/hydradb#readme) | Why object-store-native, disaggregated compute, safe writer handoff |
| [Architecture](https://github.com/hydra-db/hydradb/blob/main/architecture.md) | SlateDB WAL/SST lifecycle, writer leases, CSC index generations, cache hierarchy |
| [Cypher compatibility](https://github.com/hydra-db/hydradb/blob/main/cypher-compat.md) | Full OpenCypher surface (describes `main`, not our pinned image — see §4) |

---

## 2. Base URL & authentication

All HTTP calls in this integration target the **query endpoint**:

```
POST http://localhost:8443/v1/graphs/{graph_id}/query
```

| Header | Value | Notes |
|--------|-------|-------|
| `Authorization` | `Bearer <token>` | Token read from `hydradb-data/auth-token` (strip optional `neo4j/` prefix) |
| `X-Graph-Namespace` | `default` | Must match `GRAPH_NAMESPACE` |
| `Content-Type` | `application/json` | |

Default `graph_id` is `cogym` (from `GRAPH_ID`). Admin health lives separately:

```
GET http://localhost:9090/readyz   →  200 when the node is writable
GET http://localhost:9090/metrics  →  Prometheus
```

Bolt (`bolt://localhost:7687`) is **read-only** on the pinned image — writes over Bolt return `ClientProtocol query is not supported yet`. All writes in this repo go over HTTP.

---

## 3. Endpoints

### 3.1 Execute a query (reads + writes)

```http
POST /v1/graphs/{graph_id}/query
Content-Type: application/json
Authorization: Bearer <token>
X-Graph-Namespace: default

{
  "cell_id": "cell-0",
  "query": "MATCH (e:REL_RAN_ON {dst_key: $f}) WHERE e.quality_pass = true RETURN e.src_key AS pk ORDER BY pk LIMIT $n",
  "parameters": { "f": "worldfamily:toy.signal_game", "n": 5 }
}
```

**Response**

```json
{
  "query_id": "http-query-42",
  "columns": ["pk"],
  "rows": [[{"type": "string", "value": "policy:toy.signal_game:cand_abc123"}]],
  "read_epoch": 17,
  "bookmark": "sgk:1:64656661756c74:636f67796d:63656c6c2d30:17",
  "next_cursor": null
}
```

Typed cells: `{"type":"string"|"integer"|"float"|"boolean","value": ...}`.

**Optional fields on the request**

| Field | Type | Effect |
|-------|------|--------|
| `bookmark` | `string` | Causal read: wait until this `bookmark`'s epoch is visible before pinning snapshot |
| `consistency` | `"causal"` \| `"strong"` | `strong` forces a SlateDB refresh from object storage before pinning (pays remote latency) |

### 3.2 Health

```http
GET /readyz          → 200 / 503
GET /metrics         → Prometheus text
```

---

## 4. Verified OpenCypher surface (image `db78309a`)

> Upstream `cypher-compat.md` describes `main`. This table is what the **pinned image actually accepts** (probed 2026-08-24).

| Clause | Support | Notes |
|--------|---------|-------|
| `MATCH (n:Label {key: $k})` | ✅ | Label + property predicate required |
| `MATCH (n)` / `MATCH (n) WHERE n.key IS NOT NULL` | ❌ | Rejected — always add a label or property |
| `WHERE` | ✅ | Boolean combos of property comparisons; `IS NOT NULL` is rejected |
| `RETURN n.key AS k ORDER BY k LIMIT n` | ✅ | Typed projections only |
| `CREATE (a:L {id, key})-[:EDGE]->(b:L {id, key})` | ✅ | **Exactly one hop, one path**, both endpoints born in-statement. No other form. |
| `MATCH (...) SET n.prop = $v` | ✅ | After a `MATCH` |
| `MATCH (...) DETACH DELETE n` | ✅ | |
| `MERGE ... SET`, `MATCH ... CREATE` | ❌ | Rejected (`MERGE with following clauses…`, `write query is not executable…`) |
| `UNWIND` | ❌ | Rejected on this image |
| Variable-length | ⚠️ | `MATCH (a {id: 7001})-[:REL*1..2]->(v)` works; needs fixed integer `id` source |
| `algo.SSpaths` / `algo.SPpaths` | ✅ | GraphBLAS path procedures work (`sourceNode` must be integer id + `relTypes`, `maxLen`) |

---

## 5. How cogym uses Hydra (and why the quirks don't hurt)

### Write path — why 4 round trips

Because only the `CREATE pair` form works, `ensure_node()` does:

```
MATCH {key} → CREATE (n:Label {id, key})-[:BORN]->(:_Scratch {id, key})
            → DETACH DELETE _Scratch twin → SET props
```

When the image upgrades to `MERGE {id} SET`, this collapses to 1 trip — the client **capability-probes at startup** and auto-selects. Callers don't change.

### Schema — association nodes

You can't `MATCH a,b CREATE (a)-[:REL]->(b)` between existing nodes on this image, so each logical edge becomes a node:

| Node label | Meaning | Created by |
|------------|---------|------------|
| `Policy`, `WorldFamily`, `ActionKind` | experience catalog | `experience/projection.py` |
| `REL_RAN_ON`, `REL_IMPROVED_ON`, `REL_USED`, … | one node per logical edge (`Edge.to_node()`) | same |
| `Experiment`, `Hypothesis`, `Finding` | epistemic chain per cycle | `science/cycle.py` |

Queries join on `src_key`/`dst_key` properties instead of traversing edges. When the image supports real edges, `to_node()` is replaced — no caller changes.

### Read path — the learning loop

```python
from cogym_kernel.experience.client import HydraClient
client = HydraClient()  # reads token, http_url, graph from env

# leaders = best verified policies on a world family
rows = await client.query(
    "MATCH (e:REL_RAN_ON {dst_key: $f}) WHERE e.quality_pass = true "
    "RETURN e.src_key AS pk, e.cash_cost AS cost ORDER BY cost ASC LIMIT $n",
    {"f": "worldfamily:toy.signal_game", "n": 5},
    ("pk", "cost"))
```

Reads are snapshot-pinned (`read_epoch` / `bookmark`), so concurrent writes never tear a query.

---

## 6. Error reference

| HTTP | Body `error.message` | Cause |
|------|----------------------|-------|
| 401 | `principal bearer principal is not authorized…` | Wrong token, namespace, or graph scope |
| 400 | `OpenCypher query is not supported yet: …` | Clause from §4's ❌ column |
| 400 | `node-only MATCH requires an id, label, or property predicate` | Bare `MATCH (n)` |
| 400 | `VLP requires a fixed source id` | Variable-length without integer `id` source |

Deterministic writes that fail due to capability (❌ rows) must be retried with a different form — never with the same query.

---

## 7. Operational checklist

```bash
chown -R 10001:10001 hydradb-data          # container runs as uid 10001; otherwise: Permission denied on writer leases
curl -fsS http://localhost:9090/readyz    # → 200 means writable
python3 -c "import asyncio; from cogym_kernel.experience.client import HydraClient; print(asyncio.run(HydraClient().available()))"
# → True means you can project
```

Rebuild test (CI gate): `python3 -m cogym_kernel.experience.rebuild --check` — wipes the derived graph, replays canonical `runs/*.json` + `claims/*.json`, diffs. Exit 2 if `lost != 0`; CI fails the PR.

---

## 8. Further reading

- `docs/HYDRA.md` — bring-up commands, env table, and the 30-second checklist (operational companion to this reference).
- `docs/hydradb/architecture.md` (vendored) — deep dive on WAL/SST/indexer/cache.
- Upstream source of truth: [hydra-db/hydradb](https://github.com/hydra-db/hydradb) (`main`).

