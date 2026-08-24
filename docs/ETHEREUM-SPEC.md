# ETHEREUM SPEC — editions, integrations, and what changes in the build

**Status:** spec · 2026-08-24 · companion to ETHEREUM-VISION.md
**Vendored refs in this dir:** `base-docs-index.txt` (84KB Base doc index),
`x402-docs-index.txt`, `eas-quickstart.md`.

---

## 1. Direct answers

| Question | Answer |
|---|---|
| Still use GitHub? | **Yes — more than before.** GitHub remains code host, distribution channel (worldpacks = repo tags), AND the claims ledger's backing store. The chain never stores experiment data; it stores *hashes* of claim JSON whose full bytes live in a git repo. Publishing = PR; verification = CI re-run; trust anchor = on-chain attestation of the content hash. |
| Still use Hydra? | **Yes — unchanged role.** HydraDB stays off-chain derived memory (policy experience, lineage, induction drift). The chain NEVER stores experiment data or graphs — gas economics alone forbid it, and our §56 doctrine says projections must be rebuildable from files. On-chain lives only: claimHash (keccak256), world commitment, bond, status, EAS uid. |
| How does the build change? | One new top-level module `chain/` (Foundry workspace + adapters). Kernel core, worlds, recipes, experience loop: **unchanged**. New: keccak normalization of receipt commitments (we use sha256 today; the claim carries both), an EAS attestation adapter, x402 middleware wrapping `/v1/evaluate`, and an ERC-8004 identity hook. |
| Product versions? | **Three editions, one codebase** — see §2. |
| Built on Base? | **Yes.** Rationale: x402's default settlement L2 (~85% of volume), EAS canonically predeployed at `0x4200…0021` (EAS) / `0x4200…0020` (SchemaRegistry), Coinbase agent-tooling alignment (AgentKit), low fees fit micropayment bonds, OP-stack security inherited from Ethereum. Ethereum mainnet attestation mirror possible later via EAS's multi-chain deployments. |

## 2. The three editions (one repo, layered features)

### Edition A — cogymkernel OSS (exists today)
Deterministic worlds · recipes/styles · HydraDB experience loop · kanban/
embedded orchestration · scientific cycle + three-tier verification ·
worldpack distribution via GitHub. **No chain anything.**
Users: researchers, labs, anyone reproducing claims locally.

### Edition B — Lab Hosted (A + services)
Adds the *served* surface:
- MCP server (tools: run_episode, evaluate_candidate, fork_decision, …)
- x402-gated endpoints:
  - `POST /v1/evaluate` — hidden-suite scoring (fresh entropy secrets;
    labels never leave the evaluator)
  - `GET /v1/worldpack/<hash>` — paid worldpack delivery
  - `POST /v1/fork` — counterfactual replay queries against the experience graph
- Credential proxy (Loom pattern): one process holds provider keys; subjects
  get capability handles.
Users: agents that want honest evaluation they cannot self-serve.

### Edition C — Chain edition (B + Proof-of-Competence)
Adds `chain/`:
- **ClaimRegistry.sol** (Base): attest(claimHash, worldCommitment) + bond,
  challenge(msg.sender, stake), resolve(receiptRoots). Optimistic pattern:
  Pending → Finalized | Refuted; DISPUTED maps to the challenge window.
- **EAS integration**: schema
  `bytes32 claimHash, address agent, bytes32 worldCommitment, string uri`
  attested on finalization; resolver enforces "only resolve() may finalize."
  Agent profile = ERC-8004 token id; claim history = portable on-chain CV.
- **x402 settlement** of bonds/fees in USDC; facilitator handles payment
  verification so the kernel never holds keys for payers.
- Receipt hash normalization: claims carry BOTH sha256 (canonical files) and
  keccak256 (on-chain commitment) — computed at publish, verified at challenge.

## 3. Contract architecture (Edition C)

```solidity
// Base mainnet/sepolia predeploys used:
//   EAS            0x4200000000000000000000000000000000000021
//   SchemaRegistry 0x4200000000000000000000000000000000000020
contract ProofOfCompetence {
    enum Status { Pending, Finalized, Refuted }
    struct Claim {
        bytes32 claimHash;      // keccak256(canonical claim JSON)
        bytes32 worldCommit;    // keccak256(scenario Σ + suite config)
        bytes32 receiptRoot;    // merkle root over receipt hashes
        address agentId;        // ERC-8004 registry token holder
        uint96  bond;
        uint64  challengeUntil;
        Status  status;
    }
    mapping(uint256 => Claim) public claims;

    function attest(bytes32 claimHash, bytes32 worldCommit,
                    bytes32 receiptRoot) external payable;
    function challenge(uint256 id) external payable;   // stake >= bond
    function resolve(uint256 id,
                     bytes32[2] calldata replayRoots) external;
}
```
Resolution rule: replay roots compared off-chain by deterministic re-execution;
either party can push the outcome hash; wrong pusher forfeits (bond math).
zkML inference proofs (DeepProve/EZKL) plug into `resolve` later as a
trustless shortcut — accepted as valid challenger evidence.

## 4. EAS schema (registered once per deployment)

```
bytes32 claimHash,       // keccak256(canonical CapabilityClaim JSON)
address agentId,         // ERC-8004 agent identity
bytes32 worldCommitment, // scenario Σ + suite config commitment
uint64 finalizedAt,
string metadataURI       // IPFS/Arweave pointer: full claim + receipts
```

Attestation lifecycle mirrors our verification statuses exactly:
Pending (challenge open) → Finalized (SUPPORTED after window) → Refuted
(DISPUTED lost / tamper proven). PROVISIONAL claims are attested off-chain
only (EAS off-chain mode) until n ≥ 30 promotes them CONFIRMATORY.

## 5. What each existing component does in the chain edition

| Component | Role under Edition C |
|---|---|
| GitHub | claim bytes storage; PR publishing; CI schema+determinism gates; worldpack tags |
| HydraDB | experience graph (leaders/lineage) feeding proposals; untouched by chain |
| Kanban/orchestrator | runs challenges as jobs: clone pinned commit → replay → submit roots |
| Verification tiers | Tier-1 deterministic = on-chain referee input; Tier-2/3 stay off-chain narrative |
| Website | renders Finalized/Refuted badges from chain events beside PILOT/CONFIRMATORY modes |

## 6. Deployment targets

| Network | Purpose |
|---|---|
| Base Sepolia | hackathon/dev: EAS + SchemaRegistry predeployed (addresses above); free faucets |
| Base mainnet | production attestations; USDC native; x402 default |
| Ethereum mainnet | optional attestation mirror via EAS multi-chain (credibility signal) |

Kernel config gains `[chain]` section: rpc_url, eas_address, schema_uid,
registry_address, bond_amount, challenge_seconds. Absent section ⇒ Edition A/B
behavior (fully standalone).

## 7. Sequencing

1. Edition A hardening continues independently (already 115 tests green).
2. Edition B lands with M4/M5 (MCP + x402 middleware) — no chain needed.
3. Edition C contracts develop in `chain/` behind feature flag; demo path:
   Base Sepolia + toy.search_game claims end-to-end (attest → challenge →
   slash → finalize) before any real-value deployment.
