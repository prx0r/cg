# GIT-LEDGER — every deterministic run has a unique, verifiable identity

## The scheme

Every run in cogymkernel produces a **RunReceipt** whose identity is derived
entirely from its content:

```
run_id = blake3( canonical_json({
    worldpack_id,        # content hash of the world package
    scenario: Σ,         # spec + suite config (factminer §48)
    candidate_hash,      # blake3 of canonical candidate config
    seed,
    events_root,         # merkle root over ordered event hashes
}) )
```

Properties:
- **Same inputs ⇒ same run_id**, on any machine, any year. This is the proof
  primitive: two parties comparing `run_id`s compare entire executions.
- **events_root** is a Merkle root over the ordered list of per-event hashes
  (observation hash, action hash, ActionResult receipt hash per step), so a
  receipt can be partially disclosed without losing integrity.
- Timestamps, hostnames and latencies are RECORDED but EXCLUDED from the id
  (they are volatile); they live beside the id inside the receipt.

## Git as the ledger

The chain never stores experiment data; git never stores trust. Division:

| Artifact | Home | Form |
|---|---|---|
| Kernel code | git `main` | normal commits |
| Worldpacks | git tags `worldpack/<kind>-v<ver>` | tarball attached OR tree path |
| Run receipts | `runs/<run_id>.json` committed via PR | append-only files |
| CapabilityClaims | `claims/<claim_id>.json` via PR | schema-validated |
| Trust anchors | Base chain (EAS attestation of claimHash) | keccak commitment |

Publishing flow:
```
1. cogym run --world toy.search_game --candidate my.json
   → writes runs/local/<run_id>.json + prints run_id
2. cogym claim create --from-run <run_id>   → claims/<claim_id>.json
3. open PR adding both files
4. CI: validates schemas, re-executes the run from the pinned worldpack tag,
   diffs events_root. Match ⇒ auto-merge label `verified`.
```

Because `run_id` is content-derived, a PR containing an already-known run_id is
recognized instantly (dedupe) and any tampering with metrics invalidates the id.

## Cross-repo verification

A verifier needs only:
1. the worldpack tag (pinned code),
2. the receipt JSON (inputs + expected events_root),
3. the kernel at the recorded version.

```bash
git clone https://github.com/cogymkernel/worldpacks && cd worldpacks
git checkout worldpack/toy.search_game-v1
cogym verify --receipt ../runs/abc.json     # exit 0 = reproduced exactly
```

No network calls occur for deterministic executors; model/search executors
replay from their embedded tapes (unknown tape keys fail loudly).

## Hash normalization note

Kernel uses blake3 internally. Chain commitments use keccak256(canonical_bytes)
computed at publish time; both values coexist in the receipt (`hashes: {b3,
keccak}`) so EAS contracts and local tools verify against their native scheme.
