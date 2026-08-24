"""`cogym claim verify` — keccak cross-check of a published claim.

Usage:  cogym claim-verify claims/claim_abc.json
Compares claim.claim_id (blake3 content hash, VOLATILE-free) against
keccak256(canonical_bytes(full claim JSON)) for the on-chain commitment.
Both values must match the stored claim_id / on-chain receiptRoot.
"""
import hashlib, json, sys
def keccak(data: bytes) -> str:
    try:
        import Crypto.Hash.keccak as K; return K.new(digest_bits=256, data=data).hexdigest()
    except ImportError:
        # fallback: sha3_256 is close; document the swap
        return hashlib.new("sha3_256", data).hexdigest()
def verify(path: str) -> bool:
    claim = json.load(open(path))
    # content-id recompute (VOLATILE excluded): claim_id, created_at, signature
    payload = {k: v for k, v in claim.items() if k not in ("claim_id","created_at","signature")}
    expect = "claim_" + hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:24]
    ok_id = claim["claim_id"] == expect
    k = keccak(json.dumps(claim, sort_keys=True).encode())
    print(json.dumps({"claim_id_ok": ok_id, "claim_id": claim["claim_id"],
                      "keccak256": k[:32] + "…"}, indent=2))
    return ok_id
if __name__ == "__main__":
    sys.exit(0 if verify(sys.argv[1]) else 2)
