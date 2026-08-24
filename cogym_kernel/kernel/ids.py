"""Content-addressed identities. blake3 when available, sha256 otherwise.

Canonical form: sorted-key compact JSON, UTF-8. Volatile fields (timestamps,
latencies, hostnames) must NEVER enter an id — callers filter them first.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

try:
    import blake3  # optional fast path
    def _hash(b: bytes) -> bytes:
        return blake3.blake3(b).digest()
except ImportError:  # pragma: no cover
    def _hash(b: bytes) -> bytes:
        return hashlib.sha256(b).digest()

VOLATILE = {"created_at", "ts", "timestamp", "started_at_ns", "finished_at_ns",
            "wall_ms", "latency_s", "host", "signature"}


def canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str).encode()


def strip_volatile(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: strip_volatile(v) for k, v in obj.items() if k not in VOLATILE}
    if isinstance(obj, list):
        return [strip_volatile(v) for v in obj]
    return obj


def content_id(prefix: str, obj: Any) -> str:
    """Deterministic id: prefix + '_' + hex digest of canonical volatile-free JSON."""
    d = _hash(canonical_bytes(strip_volatile(obj))).hex()
    return f"{prefix}_{d[:32]}"


def events_root(event_hashes: list[str]) -> str:
    """Merkle-style root over ordered event hashes (GIT-LEDGER.md)."""
    if not event_hashes:
        return _hash(b"empty").hex()
    level = [h.encode() for h in event_hashes]
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            pair = level[i] + (level[i + 1] if i + 1 < len(level) else level[i])
            nxt.append(_hash(pair))
        level = nxt
    return level[0].hex()


def keccak256(data: bytes) -> str:
    """On-chain commitment scheme (chain/ edition). Requires pysha3-free path."""
    return hashlib.new("sha3_256", data).hexdigest()  # NIST SHA3; keccak-crypto swap documented


def now_ns() -> int:
    import time
    return time.time_ns()
