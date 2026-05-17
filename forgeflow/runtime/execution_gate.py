from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .approval_queue import materialize_pending_reviews
from .lineage import invalidated_artifacts, load_lineage
from .pause import load_runtime_pause_state
from .run_index import load_run_index
from .review_state import load_review_state
from .needs_rerun import compute_needs_rerun


@dataclass(slots=True)
class ExecutionGateSnapshot:
    gate_status: str
    reasons: list[str]
    paused: bool
    pending_reviews: int
    pending_review_samples: list[dict[str, str]]
    approval_summary: dict[str, int]
    lineage_missing: list[str]
    invalidated_artifacts: list[str]
    rejected_review_artifacts: list[str]
    needs_rerun: dict[str, Any]
    latest_run_id: str


EXPECTED_LINEAGE_ARTIFACTS = [
    "spec",
    "solution",
    "system_design",
    "implementation_status",
    "test_report",
]


def _latest_run_dir(runs_root: Path) -> Path | None:
    if not runs_root.exists():
        return None

    # Source of truth is the filesystem. runs/index.json is a cache and can lag behind,
    # be unsorted, or contain only a subset of runs. Prefer the newest run directory by name,
    # but still consult the index to avoid missing runs when the filesystem view is partial.
    scan_candidates = [p for p in runs_root.iterdir() if p.is_dir()]
    scan_candidates.sort(key=lambda p: p.name, reverse=True)
    scan_latest = scan_candidates[0] if scan_candidates else None

    index = load_run_index(runs_root)
    index_latest: Path | None = None
    if index is not None and index.runs:
        # Do not trust index ordering. Pick the max run_id that exists on disk.
        for entry in sorted(index.runs, key=lambda e: e.run_id, reverse=True):
            candidate = runs_root / str(entry.run_id).strip()
            if candidate.exists() and candidate.is_dir():
                index_latest = candidate
                break

    if scan_latest is None:
        return index_latest
    if index_latest is None:
        return scan_latest
    return scan_latest if scan_latest.name >= index_latest.name else index_latest


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

    pending_review_samples = [
        {"run_id": item.run_id, "artifact": item.artifact} for item in pending[:10]
    ]

    latest_run_dir = _latest_run_dir(runs_root)
    latest_run_id = latest_run_dir.name if latest_run_dir is not None else ""

    # approvals: read-only scan of latest run approvals
    approval_summary: dict[str, int] = {
        "total": 0,
        "approved": 0,
        "rejected": 0,
        "pending": 0,
        "invalidated": 0,
        "stale": 0,
        "invalid": 0,
    }
    if latest_run_dir is not None:
        approvals_dir = latest_run_dir / "approvals"
        if approvals_dir.exists() and approvals_dir.is_dir():
            for path in approvals_dir.glob("*.json"):
                approval = _load_json_object(path)
                if not approval:
                    continue
                approval_summary["total"] += 1
                status = str(approval.get("approval_status", "")).strip()
                if status in {"approved", "rejected", "pending", "invalidated"}:
                    approval_summary[status] += 1
                else:
                    approval_summary["invalid"] += 1
                if bool(approval.get("stale", False)):
                    approval_summary["stale"] += 1

    if approval_summary["total"] == 0:
        reasons.append("no_approvals")

    lineage_missing: list[str] = []
    invalidated: list[str] = []
    rejected_review_artifacts: list[str] = []
    if latest_run_dir is not None:
        lineage = load_lineage(latest_run_dir)
        present = set()
        if lineage is not None:
            present = {str(item.artifact).strip() for item in lineage.entries}
            invalidated = invalidated_artifacts(lineage)
        lineage_missing = [item for item in EXPECTED_LINEAGE_ARTIFACTS if item not in present]
        if lineage_missing:
            reasons.append("lineage_incomplete")
        if invalidated:
            reasons.append("artifacts_invalidated")

        review_state = load_review_state(latest_run_dir)
        if review_state is not None:
            rejected_review_artifacts = sorted(
                {
                    item.artifact
                    for item in review_state.items
                    if item.review_status == "rejected" and item.artifact
                }
            )
            if rejected_review_artifacts:
                reasons.append("rejected_reviews")
    else:
        reasons.append("no_runs")
        lineage_missing = list(EXPECTED_LINEAGE_ARTIFACTS)

    needs = compute_needs_rerun(
        invalidated_artifacts=invalidated,
        pending_review_artifacts=[item["artifact"] for item in pending_review_samples if item.get("artifact")],
        rejected_review_artifacts=rejected_review_artifacts,
    )
    if needs.stages:
        reasons.append("needs_rerun")

    gate_status = "blocked" if reasons else "ready"
    return ExecutionGateSnapshot(
        gate_status=gate_status,
        reasons=reasons,
        paused=pause_state.paused,
        pending_reviews=len(pending),
        pending_review_samples=pending_review_samples,
        approval_summary=approval_summary,
        lineage_missing=lineage_missing,
        invalidated_artifacts=invalidated,
        rejected_review_artifacts=rejected_review_artifacts,
        needs_rerun={"artifacts": needs.artifacts, "stages": needs.stages},
        latest_run_id=latest_run_id,
    )


def render_execution_gate(snapshot: ExecutionGateSnapshot) -> str:
    lines: list[str] = []
    lines.append("ForgeFlow Execution Gate")
    lines.append(f"Gate: {snapshot.gate_status}")
    if snapshot.latest_run_id:
        lines.append(f"Latest Run: {snapshot.latest_run_id}")
    else:
        lines.append("Latest Run: None")
    lines.append("Signals")
    lines.append(f"- paused: {snapshot.paused}")
    lines.append(f"- pending_reviews: {snapshot.pending_reviews}")
    if snapshot.pending_review_samples:
        lines.append(f"- pending_review_samples: {snapshot.pending_review_samples}")
    else:
        lines.append("- pending_review_samples: []")
    lines.append(f"- approvals: {snapshot.approval_summary}")
    if snapshot.lineage_missing:
        lines.append(f"- lineage_missing: {snapshot.lineage_missing}")
    else:
        lines.append("- lineage_missing: []")
    if snapshot.invalidated_artifacts:
        lines.append(f"- invalidated_artifacts: {snapshot.invalidated_artifacts}")
    else:
        lines.append("- invalidated_artifacts: []")
    if snapshot.rejected_review_artifacts:
        lines.append(f"- rejected_review_artifacts: {snapshot.rejected_review_artifacts}")
    else:
        lines.append("- rejected_review_artifacts: []")
    lines.append(f"- needs_rerun: {snapshot.needs_rerun}")
    lines.append("Reasons")
    if snapshot.reasons:
        for reason in snapshot.reasons:
            lines.append(f"- {reason}")
    else:
        lines.append("- none")
    return "\n".join(lines)
