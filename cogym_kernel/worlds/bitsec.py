"""BitSec CG World — wraps ScaBench as a deterministic CG world.

This is how BitSec plugs into the learning loop:
1. CG runner calls world.reset() → get a ScaBench project
2. Worker observes the code (no ground truth)
3. Worker calls FIND_VULNERABILITIES action
4. world.apply() records findings
5. world.terminal() returns True after analysis
6. world.score() compares findings against hidden ground truth
7. CG produces RunReceipt with metrics
8. qdw-workbench RunEvaluator scores across 9 dimensions
9. CGE reads failures, proposes mutations
10. CG runs paired evaluation (v0 vs v1)

The ground truth is NEVER visible to the worker during execution.
Only world.score() and the evaluator see it.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path("/root/cg")))
sys.path.insert(0, str(Path("/root/bitt")))
sys.path.insert(0, str(Path("/root/bitt/private-lab")))

from cogym_kernel.kernel.contracts import (
    ActionResult, ActionSpec, Metric, MetricVector, WorldSpec,
)
from cogym_kernel.kernel.ids import content_id


SCABENCH_DIR = Path("/root/bitt/subnets/sn60-bitsec/tools/scabench")
REPOS_DIR = Path("/root/bitt/data/scabench-repos")


@dataclass
class BitSecState:
    """State of a BitSec evaluation episode."""
    seed: int
    project_id: str
    project_name: str
    platform: str
    repo_url: str
    commit: str
    code: str
    ground_truth: list[dict]  # hidden from worker
    findings: list[dict] = field(default_factory=list)
    step: int = 0
    max_steps: int = 3
    terminal: bool = False


class BitSecWorld:
    """CG World wrapping ScaBench security benchmark.

    Deterministic: same (instance_id, seed) → same project, same code, same ground truth.
    Hidden state: ground truth vulnerabilities are never in observations.
    Scoring: Jaccard + detection rate + precision + F1 against hidden ground truth.
    """

    def __init__(self, split: str = "DEV", max_projects: int = 31):
        self.split = split
        self.max_projects = max_projects
        self._projects = None
        self._spec = None

    def _load_projects(self):
        if self._projects is not None:
            return self._projects

        import json as _json
        for p in SCABENCH_DIR.rglob("curated-*.json"):
            if "baseline" not in str(p):
                raw = _json.loads(p.read_text())
                self._projects = []
                for proj in raw[:self.max_projects]:
                    vulns = proj.get("vulnerabilities", [])
                    codebases = proj.get("codebases", [])
                    repo_url = codebases[0].get("repo_url", "") if codebases else ""
                    commit = codebases[0].get("commit", "") if codebases else ""
                    self._projects.append({
                        "project_id": proj.get("project_id", ""),
                        "name": proj.get("name", ""),
                        "platform": proj.get("platform", ""),
                        "repo_url": repo_url,
                        "commit": commit,
                        "vulnerabilities": [
                            {"finding_id": v.get("finding_id", ""), "severity": v.get("severity", ""),
                             "title": v.get("title", ""), "description": v.get("description", "")}
                            for v in vulns
                        ],
                    })
                break

        if self._projects is None:
            self._projects = []
        return self._projects

    def _load_code(self, project_id: str) -> str:
        repo_dir = REPOS_DIR / project_id
        if not repo_dir.is_dir():
            return ""

        sol_parts = []
        other_parts = []
        for root, dirs, files in os.walk(repo_dir):
            dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', 'target', 'deps', 'test', 'tests', 'script']]
            for f in files:
                fp = os.path.join(root, f)
                rel = os.path.relpath(fp, repo_dir)
                if any(skip in rel.lower() for skip in ['test/', 'tests/', 'script/', 'hardhat.config', 'foundry.toml']):
                    continue
                try:
                    content = open(fp).read()
                    if len(content) > 50:
                        entry = f'// File: {rel}\n{content}'
                        if f.endswith('.sol'):
                            sol_parts.append(entry)
                        elif f.endswith(('.rs', '.js', '.ts', '.py', '.go')):
                            other_parts.append(entry)
                except:
                    pass

        return '\n\n'.join(sol_parts + other_parts)[:15000]

    @property
    def world_spec(self) -> WorldSpec:
        if self._spec is None:
            self._spec = WorldSpec(
                world_kind="bitsec.scabench",
                version="1",
                instance_set_hash=f"scaBench-{self.split}-v1",
                environment_hash="solidity-audit-v1",
                oracle_hash="jaccard-detection-rate-v1",
            )
        return self._spec

    @property
    def worldpack_id(self) -> str:
        return content_id("wp", {"kind": "bitsec.scabench", "v": 1, "split": self.split})

    def reset(self, *, instance_id: str, seed: int) -> BitSecState:
        projects = self._load_projects()
        if not projects:
            raise RuntimeError("DATASET_UNAVAILABLE: No ScaBench projects loaded")

        rng = random.Random(seed)
        proj = rng.choice(projects)
        code = self._load_code(proj["project_id"])

        return BitSecState(
            seed=seed,
            project_id=proj["project_id"],
            project_name=proj["name"],
            platform=proj["platform"],
            repo_url=proj["repo_url"],
            commit=proj["commit"],
            code=code,
            ground_truth=proj["vulnerabilities"],
        )

    def observe(self, state: BitSecState) -> dict:
        """Worker sees ONLY the code and project metadata. Never ground truth."""
        return {
            "project_id": state.project_id,
            "name": state.project_name,
            "platform": state.platform,
            "code": state.code[:10000],  # truncated observation
            "step": state.step,
            "max_steps": state.max_steps,
            "findings_so_far": len(state.findings),
        }

    def actions(self, state: BitSecState) -> tuple[ActionSpec, ...]:
        if state.terminal:
            return ()
        return (
            ActionSpec(
                kind="FIND_VULNERABILITIES",
                executor_kind="llm",
                estimated_cost=0.005,
                timeout_ms=60000,
            ),
            ActionSpec(
                kind="SUBMIT_FINDINGS",
                executor_kind="deterministic",
                estimated_cost=0.0,
            ),
        )

    def apply(self, state: BitSecState, action: ActionSpec,
              result: ActionResult) -> BitSecState:
        state.step += 1

        if action.kind == "FIND_VULNERABILITIES" and result.status == "ok":
            findings = result.payload.get("findings", [])
            state.findings.extend(findings)

        if action.kind == "SUBMIT_FINDINGS" or state.step >= state.max_steps:
            state.terminal = True

        return state

    def terminal(self, state: BitSecState) -> bool:
        return state.terminal

    def score(self, state: BitSecState) -> MetricVector:
        """Score against hidden ground truth. This is the authoritative evaluator."""
        ground_truth = state.ground_truth
        findings = state.findings

        # Title-based matching (ScaBench has no categories)
        matched_gt = set()
        matched_findings = []

        for f in findings:
            f_title = f.get("title", "").lower().strip()
            f_desc = f.get("description", "").lower().strip()[:200]
            best_match = None
            best_score = 0

            for j, gt in enumerate(ground_truth):
                if j in matched_gt:
                    continue
                gt_title = gt.get("title", "").lower().strip()
                gt_desc = gt.get("description", "").lower().strip()[:200]

                score = 0.0
                # Title word overlap
                f_words = set(f_title.split())
                gt_words = set(gt_title.split())
                if f_words and gt_words:
                    score += len(f_words & gt_words) / max(len(f_words | gt_words), 1) * 0.5
                # Description overlap
                if f_desc and gt_desc:
                    f_dw = set(f_desc.split())
                    gt_dw = set(gt_desc.split())
                    if f_dw and gt_dw:
                        score += len(f_dw & gt_dw) / max(len(f_dw | gt_dw), 1) * 0.3
                # Severity match
                if f.get("severity", "").lower() == gt.get("severity", "").lower():
                    score += 0.1

                if score > best_score and score >= 0.15:
                    best_score = score
                    best_match = j

            if best_match is not None:
                matched_gt.add(best_match)
                matched_findings.append({"finding": f, "truth": ground_truth[best_match], "score": best_score})

        tp = len(matched_gt)
        fp = len(findings) - tp
        fn = len(ground_truth) - tp
        n_expected = max(len(ground_truth), 1)

        detection_rate = tp / n_expected
        precision = tp / max(tp + fp, 1)
        f1 = 2 * precision * detection_rate / max(precision + detection_rate, 0.001)
        jaccard = 0.0  # no categories in ScaBench

        return MetricVector(metrics=(
            Metric(name="detection_rate", value=detection_rate, direction="max"),
            Metric(name="f1_score", value=f1, direction="max"),
            Metric(name="precision", value=precision, direction="max"),
            Metric(name="jaccard", value=jaccard, direction="max"),
            Metric(name="true_positives", value=float(tp), direction="max"),
            Metric(name="false_positives", value=float(fp), direction="min"),
            Metric(name="false_negatives", value=float(fn), direction="min"),
            Metric(name="n_expected", value=float(n_expected), direction="max"),
            Metric(name="n_found", value=float(len(findings)), direction="max"),
        ))


import os
