# ETHEREUM VISION — Proof-of-Competence for the Agentic Economy

**Brainstorm · 2026-08-24 · for ETH-global-style hackathon consideration**

---

## 1. The ecosystem gap (researched live)

The 2026 agentic-economy stack has settled its lower layers:

| Layer | Standard | Status |
|---|---|---|
| Payments | **x402** (HTTP 402 + USDC, Linux Foundation; ~165M txns, 85% on Base) | production |
| Identity | **ERC-8004** agent identity tokens (Base mainnet, Mar 2026) | shipping |
| Communication | A2A protocol (150+ orgs) | growing |
| Attestations | EAS (Ethereum Attestation Service) | standard |
| **Verifiable competence** | ❓ | **THE MISSING LAYER** |

Everyone is building rails for agents to pay each other. Almost nobody answers
the question an agent actually faces before paying: *"Agent B claims it
solves X at cost Y — prove it."* Centralized reputation = lock-in + opacity +
manipulation. That is exactly the hole cogymkernel occupies:

> **cogymkernel turns capability claims into content-addressed, re-runnable
> proofs.** Deterministic worlds + frozen scenarios + receipt-hash comparison.
> We already built this. Ethereum adds the economic game around it.

## 2. The fit — our existing machinery maps 1:1

| cogymkernel mechanism | Ethereum counterpart |
|---|---|
| CapabilityClaim (content-addressed, schema v1) | attestation payload (EAS on Base) |
| Three-tier verification (deterministic → binary → review) | optimistic fraud-proof lifecycle |
| **DISPUTED status** | **challenge window** — literally already modeled |
| Secret splits (fresh OS entropy, proposer-blind) | why `submit(candidate) → score` must be a *paid service* |
| Receipt hashes | on-chain commitments (`keccak256(receipts)` vs our sha256 — normalize) |
| ERC-8004 agent id | the subject of the attestation; claim history = portable on-chain CV |

## 3. The protocol — "Proof-of-Competence" (PoC)

### Flow
```
1. AGENT builds policy, runs it on DEV split locally (free, own hardware)
2. AGENT posts ClaimRegistry.attest(claimHash, bond)     ← bond staked
   - claimHash = keccak(canonical claim JSON)
   - challenge window opens (e.g. 3 days)
3. ANYONE can challenge(msg.sender, stake):
   - download committed receipts (IPFS/Arweave pointer in the claim)
   - re-run the deterministic world at pinned git commit (our §56 machinery)
   - diff receipt hashes
4a. No challenge in window ⇒ claim FINALIZES; attestation minted to agent
    (EAS + ERC-8004 profile); bond returned + fee
4b. Challenge ⇒ off-chain verification game (both sides submit replay
    hashes; mismatch resolves against claimant) ⇒ loser's stake pays winner
```

This is optimistic-rollup logic applied to *cognition*: cheap happy path,
expensive dispute path, deterministic referee. Our DISPUTED/BLOCKED statuses
were designed for science and turn out to be the exact contract states.

### Why x402 slots in perfectly
The one evaluation an agent can NEVER self-serve: the **secret split** (fresh
entropy, labels hidden — that's the whole point). So:

```
POST cogym-lab.example/v1/evaluate        # hidden-suite evaluation service
→ 402 Payment Required: 0.05 USDC, Base
→ agent pays via x402 header
→ sealed evaluator runs candidate on fresh secret instances
→ returns MetricVector + signed receipt (commitment posted for PoC)
```

Hidden evaluation is the canonical x402 service: non-self-servable,
micropriced, instant. Same for `submit(worldpack)` hosting and
`fork_decision` queries against the experience graph.

## 4. Smart contract surface (Base L2, minimal)

```solidity
contract ProofOfCompetence {
    struct Claim {
        bytes32 claimHash;        // keccak of canonical claim JSON
        address agent;            // ERC-8004 identity holder
        uint256 bond;
        uint64  challengeUntil;
        Status  status;           // Pending | Finalized | Refuted
        bytes32 worldCommitment;  // scenario+suite config hash
    }

    function attest(bytes32 claimHash, bytes32 worldCommitment) external payable;
    function challenge(uint256 claimId) external payable;      // stake >= bond
    function resolve(uint256 claimId,
                     bytes32 challengerReceiptRoot,
                     bytes32 claimantReceiptRoot) external;     // after replay
}
```

Layered certificate honesty (from school/pack_v2): layer-1 commitments are
fully trustless today; layer-3 capability deltas verify optimistically;
layer-2 zkML inference proofs (DeepProve/EZKL) are the future upgrade that
makes even API-model claims partially provable. Until then: **deterministic-
world claims verify trustlessly NOW; open-weight LLM-subject claims verify
optimistically with bonds; closed-API claims carry PROVISIONAL badges.**
That honesty ladder is itself a feature, not a bug.

## 5. Hackathon pitch (60 seconds)

> Agents are starting to hire agents. x402 gives them wallets, ERC-8004 gives
> them IDs — but nothing tells them who can actually do the work.
>
> We built cogymkernel: deterministic worlds where any capability claim becomes
> a re-runnable proof. Post your claim with a bond. Challengers re-execute the
> exact frozen scenario and compare receipt hashes — same hashes, claim
> finalizes as an on-chain attestation; different hashes, you lose your stake
> to the challenger. Hidden evaluations are sold over x402, because secret
> benchmarks are the one thing nobody can grade for themselves.
>
> It's not a prompt marketplace. It's the trust layer the agentic economy is
> missing: **Proof-of-Competence.**

## 6. Build plan for a hackathon weekend

| Phase | Deliverable |
|---|---|
| 0–4h | Foundry project: ClaimRegistry + challenge/settle (sketch above compiles) |
| 4–8h | EAS integration: attest finalized claims to ERC-8004 agent profiles (Base Sepolia) |
| 8–16h | x402 middleware on the kernel's `/v1/evaluate` (hidden toy-world suite) |
| 16–24h | End-to-end demo: agent A posts claim → agent B challenges with tampered receipts → slashed → agent C verifies honestly → finalized; site renders on-chain badge next to PROVISIONAL/SUPPORTED statuses |
| 24h+ | Deploy demo UI (existing website/ gains an on-chain badge column) |

## 7. Honest risks

1. **Provider nondeterminism**: API-model subjects can't be bit-replayed; only
   deterministic-executor and open-weight claims get full trustlessness.
2. **Verification cost**: replays are cheap for toy/market worlds; factcheck
   worlds with live retrieval need tape-freezing first.
3. **Bond economics**: needs sizing work; too small = griefing, too large =
   chill effect. Hackathon scope: fixed-value bonds.
