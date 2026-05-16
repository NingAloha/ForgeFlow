from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .review_state import set_review_decision


@dataclass(slots=True)
class ReviewDecisionResult:
    run_id: str
    artifact: str
    review_status: str


def write_review_decision(
    *,
    runs_root: Path,
    run_id: str,
    artifact: str,
    review_status: str,
    reviewed_by: str,
    review_reason: str,
) -> ReviewDecisionResult:
    rid = str(run_id).strip()
    if not rid:
        raise ValueError("run_id must be non-empty")
    if "/" in rid or "\\" in rid or ".." in rid:
        raise ValueError("run_id must not contain path separators or traversal segments")

    status = str(review_status).strip().lower()
    if status not in {"approved", "rejected"}:
        raise ValueError("review_status must be 'approved' or 'rejected'")

    run_dir = runs_root / rid
    if not run_dir.exists() or not run_dir.is_dir():
        raise FileNotFoundError(f"run directory not found: {run_dir}")

    set_review_decision(
        run_dir=run_dir,
        run_id=rid,
        artifact=str(artifact).strip(),
        review_status=status,  # type: ignore[arg-type]
        reviewed_by=reviewed_by,
        review_reason=review_reason,
    )

    return ReviewDecisionResult(run_id=rid, artifact=str(artifact).strip(), review_status=status)

