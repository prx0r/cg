"""Embedded scheduler parity + hermes adapter against the real board."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_embedded_scheduler_atomic_claim():
    from cogym_kernel.orchestration.scheduler import EmbeddedScheduler
    s = EmbeddedScheduler(":memory:")
    job = {"job_id": "j1", "type": "campaign", "world_kind": "toy.signal_game"}
    assert s.enqueue(job) == "j1"
    claimed = s.claim_next("w1")
    assert claimed and claimed["job_id"] == "j1"
    assert s.claim_next("w2") is None            # nothing ready while running
    s.complete("j1", "ok")
    assert s.claim_next("w1") is None


def _hermes_available() -> bool:
    import subprocess
    try:
        return subprocess.run(["hermes", "--version"], capture_output=True,
                              timeout=10).returncode == 0
    except Exception:
        return False


def test_hermes_board_roundtrip_live():
    if not _hermes_available():
        print("hermes CLI absent; skipping live adapter test")
        return
    from cogym_kernel.orchestration.hermes_adapter import HermesBoard
    b = HermesBoard("cogym-kernel-test")
    b.ensure_board()
    job = {"job_id": "ktest-1", "type": "campaign",
           "world_kind": "toy.signal_game", "suite": [["t", 42]]}
    tid = b.enqueue(job, title="[test] ktest-1")
    claimed = b.claim_next()
    assert claimed and claimed["job_id"] == "ktest-1"
    b.complete(tid, "OK test-complete")
