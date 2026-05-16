from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal


ReviewStatus = Literal["pending", "approved", "rejected"]


@dataclass(slots=True)
class ReviewItem:
    artifact: str
    review_status: ReviewStatus
    reviewed_by: str
    reviewed_at: str
    review_reason: str


@dataclass(slots=True)
class ReviewState:
    schema_version: str
    run_id: str
    items: list[ReviewItem]


def _review_state_path(run_dir: Path) -> Path:
    return run_dir / "review_state.json"


def load_review_state(run_dir: Path) -> ReviewState | None:
    path = _review_state_path(run_dir)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None

    schema_version = str(payload.get("schema_version", "")).strip()
    run_id = str(payload.get("run_id", "")).strip()
    raw_items = payload.get("items", [])
    if not isinstance(raw_items, list):
        return None

    items: list[ReviewItem] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            return None
        artifact = str(raw.get("artifact", "")).strip()
        status = str(raw.get("review_status", "")).strip()
        if status not in {"pending", "approved", "rejected"}:
            return None
        items.append(
            ReviewItem(
                artifact=artifact,
                review_status=status,  # type: ignore[arg-type]
                reviewed_by=str(raw.get("reviewed_by", "")).strip(),
                reviewed_at=str(raw.get("reviewed_at", "")).strip(),
                review_reason=str(raw.get("review_reason", "")).strip(),
            )
        )

    return ReviewState(schema_version=schema_version, run_id=run_id, items=items)


def upsert_pending_review(
    *,
    run_dir: Path,
    run_id: str,
    artifact: str,
) -> None:
    """
    Ensure an artifact has a review item.

    v1 semantics:
    - when an artifact is (re)generated and persisted, its review status becomes pending
    - review decisions are external/manual (not handled here)
    """
    existing = load_review_state(run_dir)
    items = [] if existing is None else list(existing.items)

    by_artifact: dict[str, ReviewItem] = {item.artifact: item for item in items if item.artifact}
    by_artifact[str(artifact)] = ReviewItem(
        artifact=str(artifact),
        review_status="pending",
        reviewed_by="",
        reviewed_at="",
        review_reason="",
    )
    merged = list(by_artifact.values())
    merged.sort(key=lambda item: item.artifact)

    payload = {
        "schema_version": "1",
        "run_id": str(run_id).strip(),
        "items": [
            {
                "artifact": item.artifact,
                "review_status": item.review_status,
                "reviewed_by": item.reviewed_by,
                "reviewed_at": item.reviewed_at,
                "review_reason": item.review_reason,
            }
            for item in merged
        ],
    }

    path = _review_state_path(run_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def set_review_decision(
    *,
    run_dir: Path,
    run_id: str,
    artifact: str,
    review_status: Literal["approved", "rejected"],
    reviewed_by: str,
    review_reason: str,
    reviewed_at: str | None = None,
) -> None:
    """
    Write an explicit human review decision for a single artifact.

    This is an explicit write-path (not used by status). The "approval queue"
    is materialized read-only from review_state.json.
    """
    existing = load_review_state(run_dir)
    items = [] if existing is None else list(existing.items)

    timestamp = (reviewed_at or "").strip()
    if not timestamp:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    by_artifact: dict[str, ReviewItem] = {item.artifact: item for item in items if item.artifact}
    by_artifact[str(artifact)] = ReviewItem(
        artifact=str(artifact),
        review_status=review_status,
        reviewed_by=str(reviewed_by).strip(),
        reviewed_at=timestamp,
        review_reason=str(review_reason).strip(),
    )
    merged = list(by_artifact.values())
    merged.sort(key=lambda item: item.artifact)

    payload = {
        "schema_version": "1",
        "run_id": str(run_id).strip(),
        "items": [
            {
                "artifact": item.artifact,
                "review_status": item.review_status,
                "reviewed_by": item.reviewed_by,
                "reviewed_at": item.reviewed_at,
                "review_reason": item.review_reason,
            }
            for item in merged
        ],
    }

    path = _review_state_path(run_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)
