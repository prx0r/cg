# HERMES.md — optional orchestration adapter

cogymkernel's default scheduler is EMBEDDED (SQLite WAL, atomic claims —
`orchestration/scheduler.py`). Zero external dependencies.

Use the Hermes adapter only when you want profile-based workers, messaging
delivery, or cross-machine boards. It is optional and swappable: both implement
`enqueue / claim_next / complete / block`.

## Setup

```bash
hermes kanban --board cogym-lab init     # durable SQLite board
```

## Bridge usage

```python
from cogym_kernel.orchestration.hermes_adapter import HermesBoard
board = HermesBoard("cogym-lab")          # shells `hermes kanban …`
job = board.claim_next()                  # atomic; None when idle
# ... execute with cogym_kernel runners ...
board.complete(job["job_id"], "OK receipt=…")
```

CLI equivalents:
```bash
hermes kanban --board cogym-lab list --json
hermes kanban --board cogym-lab reclaim <task_id> --reason "orphaned"
```

## Known races (documented in legacy ORCHESTRATION §5)

Simultaneous claims of one task can double-start a worker. Mitigations already
in place: receipt idempotency per job_id, flock fail-fast, reclaim for orphans.
