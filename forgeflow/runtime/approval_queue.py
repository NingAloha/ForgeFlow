from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .review_state import load_review_state


@dataclass(slots=True)
class PendingReview:
    run_id: str
    artifact: str


def materialize_pending_reviews(runs_root: Path) -> list[PendingReview]:
    """
    Read-only materialization of the human review queue from run-scoped review_state.json files.
    """
    pending: list[PendingReview] = []
    if not runs_root.exists():
        return pending

    for run_dir in runs_root.iterdir():
        if not run_dir.is_dir():
            continue
        state = load_review_state(run_dir)
        if state is None:
            continue
        for item in state.items:
            if item.review_status != "pending":
                continue
            pending.append(PendingReview(run_id=run_dir.name, artifact=item.artifact))

    pending.sort(key=lambda item: (item.run_id, item.artifact), reverse=True)
    return pending

