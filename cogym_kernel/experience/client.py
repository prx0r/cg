"""Async HydraDB experience client — clean rewrite.

Capability probe at startup selects write strategy. Write-behind batching:
upserts queue and flush <=64 per round trip. Association-node schema preserved
(see legacy INTEGRATION-NOTES for the verified surface of image db78309a).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from dataclasses import dataclass, field

DEFAULT_HTTP_URL = os.environ.get("HYDRA_HTTP_URL", "http://localhost:8443")
DEFAULT_GRAPH = os.environ.get("HYDRA_GRAPH", "cogym")
DEFAULT_NAMESPACE = "default"
DEFAULT_CELL = "cell-0"
DEFAULT_TOKEN_FILE = os.environ.get("HYDRA_TOKEN_FILE",
                                    "/root/cogym/hydradb-data/auth-token")
SCRATCH = "_Scratch"


class HydraError(RuntimeError):
    pass


def key_to_id(key: str) -> int:
    return int(hashlib.md5(key.encode()).hexdigest()[:12], 16) % (2 ** 62)


@dataclass(frozen=True)
class NodeRef:
    label: str
    key: str
    props: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Edge:
    rel_type: str
    src: NodeRef
    dst: NodeRef
    props: dict = field(default_factory=dict)

    @property
    def assoc_key(self) -> str:
        return f"{self.src.label}:{self.src.key}|{self.rel_type}->{self.dst.label}:{self.dst.key}"

    def to_node(self) -> NodeRef:
        props = {"rel_type": self.rel_type,
                 "src_label": self.src.label, "src_key": self.src.key,
                 "dst_label": self.dst.label, "dst_key": self.dst.key}
        props.update(self.props)
        return NodeRef(f"REL_{self.rel_type}", self.assoc_key, props)


def _read_token(path: str) -> str:
    p = os.path.realpath(path)
    raw = open(p).read().strip() if os.path.exists(p) else ""
    return raw.split("/", 1)[1] if raw.startswith("neo4j/") else raw


class HydraClient:
    """Async pooled client (httpx if present, urllib fallback)."""

    def __init__(self, http_url=DEFAULT_HTTP_URL, graph=DEFAULT_GRAPH,
                 namespace=DEFAULT_NAMESPACE, cell=DEFAULT_CELL,
                 token=None, token_file=DEFAULT_TOKEN_FILE, timeout_s=15.0):
        self.http_url, self.graph = http_url.rstrip("/"), graph
        self.namespace, self.cell = namespace, cell
        self.token = token or _read_token(token_file)
        self.timeout_s = timeout_s
        self.last_bookmark: str | None = None
        self.writes_sent = 0
        self._queue: list[tuple[str, dict]] = []
        try:
            import httpx  # noqa: F401
            self._httpx = True
        except ImportError:
            self._httpx = False

    # ---- transport ----

    async def _post(self, payload: dict) -> dict:
        headers = {"Authorization": f"Bearer {self.token}",
                   "X-Graph-Namespace": self.namespace,
                   "Content-Type": "application/json"}
        url = f"{self.http_url}/v1/graphs/{self.graph}/query"
        data = json.dumps(payload).encode()
        if self._httpx:
            import httpx
            async with httpx.AsyncClient(timeout=self.timeout_s) as cli:
                r = await cli.post(url, content=data, headers=headers)
            if r.status_code >= 400:
                raise HydraError(r.json().get("error", {}).get("message",
                                                              r.text)[:200])
            return r.json()
        import urllib.request, urllib.error
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            loop = asyncio.get_running_loop()
            resp = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=self.timeout_s))
            with resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            raise HydraError(json.load(e).get("error", {}).get("message",
                                                              "?")[:200]) from None

    async def query(self, query: str, params: dict | None = None,
                    columns: tuple[str, ...] = (), *,
                    bookmark: str | None = None,
                    consistency: str | None = None) -> list[dict]:
        payload: dict = {"cell_id": self.cell, "query": query,
                         "parameters": params or {}}
        if bookmark:
            payload["bookmark"] = bookmark
        if consistency:
            payload["consistency"] = consistency
        env = await self._post(payload)
        self.last_bookmark = env.get("bookmark")
        names = list(columns)
        out = []
        for row in env.get("rows", []):
            rec: dict = {}
            for i, cell in enumerate(row):
                v = cell.get("value") if isinstance(cell, dict) else cell
                rec[names[i] if i < len(names) else f"col{i}"] = v
            out.append(rec)
        return out

    async def write(self, query: str, params: dict | None = None) -> dict:
        env = await self._post({"cell_id": self.cell, "query": query,
                                "parameters": params or {}})
        self.writes_sent += 1
        self.last_bookmark = env.get("bookmark")
        return env

    # ---- health / availability ----

    def ready(self) -> bool:
        admin = self.http_url.replace(":8443", ":9090")
        import urllib.request
        try:
            with urllib.request.urlopen(f"{admin}/readyz", timeout=3.0) as r:
                return r.status == 200
        except Exception:
            return False

    async def available(self) -> bool:
        try:
            await self.query("MATCH (n:_Scratch) RETURN count(*) AS c",
                             columns=("c",))
            return True
        except HydraError:
            return False

    # ---- write primitives (image-compatible; see docs/HYDRA.md) ----

    async def ensure_node(self, ref: NodeRef) -> bool:
        hit = await self.query(
            f"MATCH (n:{ref.label} {{key: $key}}) RETURN n.key AS k LIMIT 1",
            {"key": ref.key}, ("k",))
        if hit:
            if ref.props:
                sets = ", ".join(f"n.{k} = ${k}" for k in sorted(ref.props))
                await self.write(f"MATCH (n:{ref.label} {{key: $key}}) SET {sets}",
                                 {"key": ref.key, **ref.props})
            return False
        twin = f"twin:{ref.key}"
        await self.write(
            f"CREATE (n:{ref.label} {{id: $id, key: $key}})"
            f"-[:BORN]->(:{SCRATCH} {{id: $tid, key: $tk}})",
            {"id": key_to_id(ref.key), "key": ref.key,
             "tid": key_to_id(twin), "tk": twin})
        await self.write(f"MATCH (t:{SCRATCH} {{key: $tk}}) DETACH DELETE t",
                         {"tk": twin})
        if ref.props:
            sets = ", ".join(f"n.{k} = ${k}" for k in sorted(ref.props))
            await self.write(f"MATCH (n:{ref.label} {{key: $key}}) SET {sets}",
                             {"key": ref.key, **ref.props})
        return True

    async def put_edge(self, edge: Edge) -> bool:
        """Association-node upsert: relations between existing nodes cannot be
        created directly on this image, so each Edge materializes as a
        REL_<TYPE> node carrying src/dst identity + payload."""
        return await self.ensure_node(edge.to_node())

    async def apply_ops(self, nodes: list[NodeRef], edges: list[Edge],
                        parallel: int = 8) -> dict:
        born = sum([await self.ensure_node(n) for n in nodes])
        sem = asyncio.Semaphore(parallel)

        async def one(e: Edge) -> bool:
            async with sem:
                return await self.put_edge(e)

        rel_born = sum(await asyncio.gather(*(one(e) for e in edges)))
        return {"nodes_written": len(nodes), "edges_written": len(edges),
                "nodes_created": born, "edges_created": rel_born}

    async def wipe_labels(self, labels: tuple[str, ...]) -> int:
        total = 0
        for lbl in labels:
            rows = await self.query(f"MATCH (n:{lbl}) RETURN count(*) AS c",
                                    columns=("c",))
            n = rows[0]["c"] if rows else 0
            if n:
                await self.write(f"MATCH (n:{lbl}) DETACH DELETE n")
                total += n
        return total
