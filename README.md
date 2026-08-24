# cogymkernel

**Deterministic agentic evolution laboratory.**
Worlds are replayable. Runs are content-addressed proofs. Quality gates are
hard constraints. An experience graph remembers everything.

```
pip install -e ".[dev]"        # or: uv pip install -e .
python3 -m pytest tests/ -q    # determinism is CI-enforced
python3 -m cogym_kernel.cli status
python3 -m cogym_kernel.cli run --seed 42
```

That last command prints a **RunReceipt** with a `run_id` — a blake3 content
hash over worldpack + scenario + candidate + seed + merkle root of every event.
Anyone, anywhere, re-running it gets the identical id. That is the proof
primitive the whole stack builds on.

## What's inside

| Module | Role |
|---|---|
| `kernel/` | contracts · async runner · content-addressed run ids |
| `executors.py` | deterministic · replay-tape · cached-model executors |
| `eval/` | quality gates · lexicographic selection · layered suites (dev/validation/secret) · Wilson/bootstrap stats |
| `evo/` | 10 evolution recipes · 33 reasoning styles (16 families) · typed search spaces |
| `experience/` | async HydraDB client (capability probe, batching) · learning loop |
| `orchestration/` | embedded SQLite scheduler (WAL, atomic claims); hermes adapter optional |
| `science/` | experiment cycle · three-tier verification |
| `worlds/` | registry + shipped toy worldpack |

## Documentation

- [`docs/GUIDE.md`](docs/GUIDE.md) — **start here**: full operational guide
- [`docs/GIT-LEDGER.md`](docs/GIT-LEDGER.md) — run hashing + git-as-ledger design
- [`docs/HYDRA.md`](docs/HYDRA.md) — experience graph setup, quirks, rebuild
- [`docs/HERMES.md`](docs/HERMES.md) — optional kanban adapter usage
- `AGENTS.md` — binding rules for coding agents
- Legacy lab docs: `/root/cogym/docs/` (METHODS, RECIPES, VALIDATION…)

## One-click bring-up (fresh machine)

```bash
git clone <this repo> && cd cogymkernel
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,mcp]"
pytest tests/ -q                       # no keys needed for core tests
# optional experience memory (see docs/HYDRA.md):
docker start hydradb || true
python3 -m cogym_kernel.cli status     # hydra: ready/available
```

Everything degrades gracefully without Hydra: runs work, receipts stay local,
profiles queue for later flush.
