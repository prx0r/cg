"""Hermes kanban adapter (optional backend for the orchestration layer).

Same protocol as orchestration/scheduler.EmbeddedScheduler: enqueue/claim_next/
complete/block. Shells out to `hermes kanban`; requires the hermes CLI.
Known race: simultaneous claims may double-start; mitigate with idempotent
receipts keyed by job_id plus reclaim (documented in legacy ORCHESTRATION §5).
"""
from __future__ import annotations

import json
import subprocess


class HermesError(RuntimeError):
    pass


def _kanban(*args: str, board: str | None = None) -> dict | list:
    cmd = ["hermes", "kanban"]
    if board:
        cmd += ["--board", board]
    cmd += list(args)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise HermesError(f"hermes kanban {' '.join(args)}: {proc.stderr[:300]}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"raw": proc.stdout.strip()}


class HermesBoard:
    def __init__(self, board: str = "cogym-lab"):
        self.board = board

    def ensure_board(self) -> None:
        boards = _kanban("boards", "list", board=self.board)
        names = {b.get("name") or b.get("slug")
                 for b in boards} if isinstance(boards, list) else set()
        if self.board not in names:
            _kanban("boards", "create", self.board)

    def enqueue(self, job: dict, title: str | None = None,
                priority: int | None = None) -> str:
        title = title or f"[{job.get('world_kind', job.get('type', 'job'))}] {job.get('job_id', '')}"
        args = ["create", title, "--body",
                json.dumps(job, sort_keys=True), "--json"]
        res = _kanban(*args, board=self.board)
        tid = res.get("id") or res.get("task_id") or \
            (res.get("task") or {}).get("id")
        if not tid:
            raise HermesError(f"no task id: {str(res)[:200]}")
        return str(tid)

    def claim_next(self) -> dict | None:
        res = _kanban("list", "--status", "ready", "--json", board=self.board)
        tasks = res if isinstance(res, list) else res.get("tasks", [])
        for t in tasks:
            tid = t.get("id")
            if not tid:
                continue
            try:
                _kanban("claim", tid, board=self.board)
            except HermesError:
                continue                      # lost race -> next candidate
            body = t.get("body") or "{}"
            return {"job_id": tid, **(json.loads(body) if body else {})}
        return None

    def complete(self, job_id: str, result: str) -> None:
        # resolve task id from job body is caller-side; here we take the id
        _kanban("comment", job_id, result, board=self.board)
        _kanban("complete", job_id, "--summary", result[:200], board=self.board)

    def block(self, job_id: str, reason: str) -> None:
        _kanban("comment", job_id, f"BLOCKED: {reason}", board=self.board)
