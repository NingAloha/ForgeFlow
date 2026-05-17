from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .execution_request import ensure_safe_run_id
from .lineage import invalidated_artifacts, load_lineage
from .needs_rerun import compute_needs_rerun
from .pause import load_runtime_pause_state
from .review_state import load_review_state


@dataclass(slots=True)
class RerunPlanResult:
    path: Path
    plan_status: str


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _approvals_summary(approvals_dir: Path) -> dict[str, int]:
    summary: dict[str, int] = {
        "total": 0,
        "approved": 0,
        "rejected": 0,
        "pending": 0,
        "invalidated": 0,
        "stale": 0,
        "invalid": 0,
    }
    if not approvals_dir.exists() or not approvals_dir.is_dir():
        return summary
    for path in approvals_dir.glob("*.json"):
        approval = _load_json_object(path)
        if not approval:
            continue
        summary["total"] += 1
        status = str(approval.get("approval_status", "")).strip()
        if status in {"approved", "rejected", "pending", "invalidated"}:
            summary[status] += 1
        else:
            summary["invalid"] += 1
        if bool(approval.get("stale", False)):
            summary["stale"] += 1
    return summary


def write_rerun_plan(
    *,
    state_dir: Path,
    run_id: str,
) -> RerunPlanResult:
    rid = ensure_safe_run_id(run_id)
    runs_root = state_dir.parent / "runs"
    run_dir = runs_root / rid
    if not run_dir.exists() or not run_dir.is_dir():
        raise FileNotFoundError(f"run directory not found: {run_dir}")

    pause_state = load_runtime_pause_state(state_dir)
    lineage = load_lineage(run_dir)
    invalidated = invalidated_artifacts(lineage) if lineage is not None else []

    review_state = load_review_state(run_dir)
    pending_reviews: list[str] = []
    rejected_reviews: list[str] = []
    if review_state is not None:
        for item in review_state.items:
            if not item.artifact:
                continue
            if item.review_status == "pending":
                pending_reviews.append(item.artifact)
            elif item.review_status == "rejected":
                rejected_reviews.append(item.artifact)
    pending_reviews = sorted(set(pending_reviews))
    rejected_reviews = sorted(set(rejected_reviews))

    approvals_dir = run_dir / "approvals"
    approvals_summary = _approvals_summary(approvals_dir)

    needs = compute_needs_rerun(
        invalidated_artifacts=invalidated,
        pending_review_artifacts=pending_reviews,
        rejected_review_artifacts=rejected_reviews,
    )

    block_reasons: list[str] = []
    if pause_state.paused:
        block_reasons.append("runtime_paused")
    if needs.artifacts:
        block_reasons.append("needs_rerun")
    if pending_reviews:
        block_reasons.append("pending_reviews")
    if rejected_reviews:
        block_reasons.append("rejected_reviews")
    if approvals_summary["total"] == 0:
        block_reasons.append("no_approvals")

    notes: list[str] = []
    if pending_reviews:
        notes.append("Resolve pending reviews before rerun planning can be acted upon.")
    if rejected_reviews:
        notes.append("Address rejected artifacts before attempting downstream reruns.")
    if needs.stages:
        notes.append(f"Suggested rerun stages (manual): {needs.stages}")
    if approvals_summary["stale"] > 0:
        notes.append("Some approvals are marked stale; re-approval may be required in Phase F.")

    payload = {
        "schema_version": "1",
        "run_id": rid,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "needs_rerun": {"artifacts": needs.artifacts, "stages": needs.stages},
        "review_state_summary": {"pending": pending_reviews, "rejected": rejected_reviews},
        "approvals_summary": approvals_summary,
        "decision": {"plan_status": "blocked", "block_reasons": block_reasons},
        "notes": notes,
    }

    path = run_dir / "rerun_plan.json"
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)
    return RerunPlanResult(path=path, plan_status="blocked")

