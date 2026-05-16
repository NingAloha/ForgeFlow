from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .approval_queue import materialize_pending_reviews
from .lineage import load_lineage
from .pause import load_runtime_pause_state


@dataclass(slots=True)
class ExecutionGateSnapshot:
    gate_status: str
    reasons: list[str]
    paused: bool
    pending_reviews: int
    approval_artifacts: int
    lineage_missing: list[str]


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def build_execution_gate_snapshot(
    *,
    state_dir: Path,
) -> ExecutionGateSnapshot:
    pause_state = load_runtime_pause_state(state_dir)
    runs_root = state_dir.parent / "runs"

    pending = materialize_pending_reviews(runs_root)

    reasons: list[str] = []
    if pause_state.paused:
        reasons.append("runtime_paused")

    if pending:
        reasons.append("pending_reviews")

    # approvals: best-effort scan for latest run approvals (index is a cache; scan is ok for diagnostics)
    approval_artifacts = 0
    latest_run_dir: Path | None = None
    if runs_root.exists():
        candidates = [p for p in runs_root.iterdir() if p.is_dir()]
        candidates.sort(key=lambda p: p.name, reverse=True)
        latest_run_dir = candidates[0] if candidates else None
    if latest_run_dir is not None:
        approvals_dir = latest_run_dir / "approvals"
        if approvals_dir.exists() and approvals_dir.is_dir():
            for path in approvals_dir.glob("*.json"):
                if _load_json_object(path):
                    approval_artifacts += 1

    if approval_artifacts == 0:
        reasons.append("no_approvals")

    lineage_missing: list[str] = []
    if latest_run_dir is not None:
        lineage = load_lineage(latest_run_dir)
        expected = [
            "spec",
            "solution",
            "system_design",
            "implementation_status",
            "test_report",
        ]
        present = set()
        if lineage is not None:
            present = {str(item.artifact).strip() for item in lineage.entries}
        lineage_missing = [item for item in expected if item not in present]
        if lineage_missing:
            reasons.append("lineage_incomplete")
    else:
        reasons.append("no_runs")
        lineage_missing = [
            "spec",
            "solution",
            "system_design",
            "implementation_status",
            "test_report",
        ]

    gate_status = "blocked" if reasons else "ready"
    return ExecutionGateSnapshot(
        gate_status=gate_status,
        reasons=reasons,
        paused=pause_state.paused,
        pending_reviews=len(pending),
        approval_artifacts=approval_artifacts,
        lineage_missing=lineage_missing,
    )


def render_execution_gate(snapshot: ExecutionGateSnapshot) -> str:
    lines: list[str] = []
    lines.append("ForgeFlow Execution Gate")
    lines.append(f"Gate: {snapshot.gate_status}")
    lines.append("Signals")
    lines.append(f"- paused: {snapshot.paused}")
    lines.append(f"- pending_reviews: {snapshot.pending_reviews}")
    lines.append(f"- approval_artifacts: {snapshot.approval_artifacts}")
    if snapshot.lineage_missing:
        lines.append(f"- lineage_missing: {snapshot.lineage_missing}")
    else:
        lines.append("- lineage_missing: []")
    lines.append("Reasons")
    if snapshot.reasons:
        for reason in snapshot.reasons:
            lines.append(f"- {reason}")
    else:
        lines.append("- none")
    return "\n".join(lines)

