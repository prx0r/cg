"""Embedded scheduler: standalone default (ADR-4).

SQLite WAL queue with atomic claims — same semantics we proved on hermes
kanban, zero external deps. Hermes kanban remains an optional adapter.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path


class EmbeddedScheduler:
    def __init__(self, path: str = "cogym-scheduler.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS jobs(
            job_id TEXT PRIMARY KEY, kind TEXT DEFAULT 'campaign',
            body TEXT NOT NULL, status TEXT DEFAULT 'ready',
            claim_owner TEXT, claimed_at REAL, result TEXT);
        """)
        self.conn.commit()

    def enqueue(self, job: dict) -> str:
        self.conn.execute(
            "INSERT OR IGNORE INTO jobs(job_id,kind,body) VALUES (?,?,?)",
            (job["job_id"], job.get("type", "campaign"),
             json.dumps(job, sort_keys=True)))
        self.conn.commit()
        return job["job_id"]

    def claim_next(self, worker_id: str) -> dict | None:
        """Atomic: only the winning UPDATE flips ready->running."""
        cur = self.conn.execute(
            "SELECT job_id, body FROM jobs WHERE status='ready' "
            "ORDER BY rowid LIMIT 1")
        row = cur.fetchone()
        if not row:
            return None
        cur2 = self.conn.execute(
            "UPDATE jobs SET status='running', claim_owner=?, claimed_at=? "
            "WHERE job_id=? AND status='ready'", (worker_id, time.time(), row[0]))
        self.conn.commit()
        if cur2.rowcount != 1:
            return None                      # lost race
        return {"job_id": row[0], **json.loads(row[1])}

    def complete(self, job_id: str, result: str) -> None:
        self.conn.execute(
            "UPDATE jobs SET status='done', result=? WHERE job_id=?",
            (result[:500], job_id))
        self.conn.commit()

    def block(self, job_id: str, reason: str) -> None:
        self.conn.execute(
            "UPDATE jobs SET status='blocked', result=? WHERE job_id=?",
            (reason[:500], job_id))
        self.conn.commit()
