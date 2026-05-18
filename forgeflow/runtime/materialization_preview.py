from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .events import append_runtime_event
from .execution_gate import build_execution_gate_snapshot
from .execution_request import ensure_safe_run_id
from .review_state import load_review_state


REQUIRED_REVIEW_ARTIFACTS = [
    "spec",
    "solution",
    "system_design",
    "implementation_status",
    "test_report",
]


class MaterializationError(Exception):
    pass


def _utc_timestamp_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _render_preview_readme(*, run_id: str, generated_root: str, writes: list[dict[str, str]]) -> str:
    lines: list[str] = []
    lines.append("# ForgeFlow Sandbox Preview")
    lines.append("")
    lines.append(f"- run_id: {run_id}")
    lines.append(f"- generated_root: {generated_root}")
    lines.append("")
    lines.append("Writes:")
    for item in writes:
        path = str(item.get("path", "")).strip()
        op = str(item.get("type", "")).strip() or "unknown"
        if path:
            lines.append(f"- {op}: {path}")
    lines.append("")
    lines.append("Notes:")
    lines.append("- These artifacts are materialized previews only.")
    lines.append("- They do not perform mutation, patch application, or execution.")
    lines.append("")
    return "\n".join(lines)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def materialize_sandbox_preview(
    *,
    state_dir: Path,
    run_id: str,
) -> dict[str, Any]:
    """
    First governed materialization (v0.2):
    - allowed writes: `.forgeflow/generated/<run_id>/README.md` only
    - run-scoped metadata: `runs/<run_id>/execution_preview.json`
    - append execution events
    """
    rid = ensure_safe_run_id(run_id)
    runs_root = state_dir.parent / "runs"
    run_dir = runs_root / rid
    if not run_dir.exists() or not run_dir.is_dir():
        raise MaterializationError(f"run directory not found: {run_dir}")

    review_state = load_review_state(run_dir)
    if review_state is None:
        raise MaterializationError("review_state.json is missing")

    approved = {item.artifact for item in review_state.items if item.review_status == "approved" and item.artifact}
    missing = [name for name in REQUIRED_REVIEW_ARTIFACTS if name not in approved]
    if missing:
        raise MaterializationError(f"review not approved for artifacts: {missing}")

    request_path = run_dir / "execution_request.json"
    if not request_path.exists():
        raise MaterializationError("execution_request.json is missing")

    gate = build_execution_gate_snapshot(state_dir=state_dir, run_id=rid)
    if not gate.eligible_for_materialization:
        raise MaterializationError(f"materialization gate blocked: {gate.materialization_reasons}")

    generated_root = state_dir.parent / "generated" / rid
    allowed_root = (state_dir.parent / "generated" / rid).resolve()
    resolved_generated_root = generated_root.resolve()
    if resolved_generated_root != allowed_root:
        raise MaterializationError("generated_root resolution mismatch")
    generated_root.mkdir(parents=True, exist_ok=True)

    writes = [
        {
            "path": f".forgeflow/generated/{rid}/README.md",
            "type": "create_or_overwrite",
        }
    ]

    append_runtime_event(
        run_dir=run_dir,
        event_type="materialization_preview_started",
        run_id=rid,
        payload={
            "mode": "sandbox_preview",
            "generated_root": f".forgeflow/generated/{rid}/",
        },
    )

    # Status semantics:
    # - started: an attempt began but did not close (block further attempts)
    # - failed: attempt failed (retry allowed in v0.2.1+)
    # - completed: terminal success (no-op on rerun in v0.2.1+)
    preview_payload: dict[str, Any] = {
        "schema_version": "1",
        "run_id": rid,
        "mode": "sandbox_preview",
        "status": "started",
        "generated_root": f".forgeflow/generated/{rid}/",
        "writes": writes,
        "generated_at": _utc_timestamp_z(),
    }
    preview_path = run_dir / "execution_preview.json"
    _write_json_atomic(preview_path, preview_payload)

    try:
        readme_path = generated_root / "README.md"
        readme_path.write_text(
            _render_preview_readme(run_id=rid, generated_root=f".forgeflow/generated/{rid}/", writes=writes),
            encoding="utf-8",
        )

        append_runtime_event(
            run_dir=run_dir,
            event_type="materialization_preview_written",
            run_id=rid,
            payload={
                "path": str(writes[0]["path"]),
                "type": str(writes[0]["type"]),
            },
        )

        preview_payload["status"] = "completed"
        _write_json_atomic(preview_path, preview_payload)

        append_runtime_event(
            run_dir=run_dir,
            event_type="materialization_preview_finished",
            run_id=rid,
            payload={
                "status": "completed",
                "execution_preview_path": "execution_preview.json",
            },
        )
    except Exception as exc:
        # Record a failed attempt. This does not imply the run failed.
        preview_payload["status"] = "failed"
        preview_payload["error"] = str(exc)
        _write_json_atomic(preview_path, preview_payload)
        append_runtime_event(
            run_dir=run_dir,
            event_type="materialization_preview_failed",
            run_id=rid,
            payload={
                "status": "failed",
                "error": str(exc),
                "execution_preview_path": "execution_preview.json",
            },
        )
        raise

    return preview_payload
