# AGENTS.md — cogymkernel

Binding rules for any coding agent working in this repository.

## Absolute rules

1. **NEVER `git push`.** The owner pushes. You commit locally only when asked.
2. **No domain concepts in `cogym_kernel/kernel/`.** Worlds plug in via
   `worlds/registry.py` only. If kernel code names a market, a claim, or any
   domain object, the architecture has failed.
3. **Gates dominate objectives.** Never introduce a scalar fitness that trades
   quality for cost.
4. **Volatile fields never enter content ids** (see `kernel/ids.VOLATILE`).
   Timestamps live beside ids inside receipts, not inside them.
5. **Executors own all side effects.** `World.apply()` consumes ActionResult;
   it must never perform network calls itself.
6. **Secret layers are proposer-blind**: fresh OS-entropy instances at
   evaluation time; never committed where proposals are generated.
7. **Hydra is derived memory.** Canonical records are the JSONL receipts and
   run files. Deleting Hydra must destroy no evidence — the §56 rebuild test
   is a CI gate.
8. LLM judgment is admissible only as binary, criterion-bound checks layered
   above deterministic verification (docs/VALIDATION.md doctrine).
9. PILOT honesty: n<30 decisions ⇒ directional only, labelled everywhere.
10. Tests from repo root: `python3 -m pytest tests/ -q`. Keep them green.

## Where things are

See README.md table + docs/GUIDE.md. When unsure:
`grep -rn "<concept>" cogym_kernel docs/ | head`.

## Working style

- Async-first: new I/O paths are `async def`.
- Frozen dataclasses for contracts; plain dicts only at edges.
- Every mechanism ships with a test proving its determinism or honesty property.
