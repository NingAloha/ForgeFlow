from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ReplayStep:
    timestamp: str
    input: str
    decision_type: str
    computed_stage: str
    final_stage: str
    executed_stage: str
    question_state: dict[str, Any]
    execution_trace: dict[str, Any]


@dataclass(slots=True)
class RuntimeReplaySnapshot:
    run_id: str
    final_stage: str
    executed_steps: list[ReplayStep]
    latest_decision: dict[str, str]
    artifacts: dict[str, object]
    blockers: list[str]


@dataclass(slots=True)
class ReplayLoadError(Exception):
    code: str
    message: str
    details: dict[str, object] | None = None

    def __str__(self) -> str:  # pragma: no cover
        return self.message


def _ensure_safe_run_id(run_id: str) -> str:
    value = str(run_id).strip()
    if not value:
        raise ReplayLoadError(code="invalid_run_id", message="run_id is empty.")
    if "/" in value or "\\" in value:
        raise ReplayLoadError(
            code="invalid_run_id",
            message="run_id must not contain path separators.",
            details={"run_id": value},
        )
    if ".." in value:
        raise ReplayLoadError(
            code="invalid_run_id",
            message="run_id must not contain traversal segments.",
            details={"run_id": value},
        )
    return value


def _runs_root(state_dir: str | None) -> Path:
    if state_dir:
        return Path(state_dir).parent / "runs"
    return Path(".forgeflow") / "runs"


def _normalize_step(raw: object) -> ReplayStep | None:
    if not isinstance(raw, dict):
        return None
    question_state = raw.get("question_state", {})
    if not isinstance(question_state, dict):
        question_state = {}
    execution_trace = raw.get("execution_trace", {})
    if not isinstance(execution_trace, dict):
        execution_trace = {}
    return ReplayStep(
        timestamp=str(raw.get("timestamp", "")).strip(),
        input=str(raw.get("input", "")).strip(),
        decision_type=str(raw.get("decision_type", "")).strip(),
        computed_stage=str(raw.get("computed_stage", "")).strip(),
        final_stage=str(raw.get("final_stage", "")).strip(),
        executed_stage=str(raw.get("executed_stage", "")).strip(),
        question_state=question_state,
        execution_trace=execution_trace,
    )


def _collect_blockers(steps: list[ReplayStep]) -> list[str]:
    blockers: list[str] = []

    for step in steps:
        qs = step.question_state
        status = str(qs.get("status", "")).strip()
        blocking = bool(qs.get("blocking", False))
        has_questions = bool(qs.get("questions"))
        if blocking and status == "awaiting_user" and has_questions:
            stage = str(qs.get("stage_name", "")).strip() or "UNKNOWN"
            blockers.append(f"waiting_user_input(stage={stage})")

    # Keep stable ordering and avoid duplicates.
    seen: set[str] = set()
    normalized: list[str] = []
    for item in blockers:
        if item in seen:
            continue
        seen.add(item)
        normalized.append(item)
    return normalized


def load_replay_snapshot(run_id: str, state_dir: str | None = None) -> RuntimeReplaySnapshot:
    safe_run_id = _ensure_safe_run_id(run_id)
    runs_root = _runs_root(state_dir)
    run_dir = runs_root / safe_run_id

    artifacts: dict[str, object] = {
        "run_dir_exists": run_dir.exists(),
        "summary_json": False,
        "approvals_dir": False,
        "approval_count": 0,
    }

    if not run_dir.exists():
        raise ReplayLoadError(
            code="run_not_found",
            message=f"Run directory not found: {run_dir}",
            details={"run_id": safe_run_id, "runs_root": str(runs_root)},
        )
    if not run_dir.is_dir():
        raise ReplayLoadError(
            code="run_not_directory",
            message=f"Run path is not a directory: {run_dir}",
            details={"run_id": safe_run_id},
        )

    summary_path = run_dir / "summary.json"
    artifacts["summary_json"] = summary_path.exists()
    if not summary_path.exists():
        raise ReplayLoadError(
            code="summary_missing",
            message=f"Run summary not found: {summary_path}",
            details={"run_id": safe_run_id},
        )

    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReplayLoadError(
            code="summary_invalid_json",
            message=f"Run summary is not valid JSON: {summary_path}",
            details={"run_id": safe_run_id, "error": str(exc)},
        ) from exc
    except OSError as exc:
        raise ReplayLoadError(
            code="summary_read_failed",
            message=f"Failed to read run summary: {summary_path}",
            details={"run_id": safe_run_id, "error": str(exc)},
        ) from exc

    if not isinstance(payload, dict):
        raise ReplayLoadError(
            code="summary_invalid",
            message="Run summary payload must be a JSON object.",
            details={"run_id": safe_run_id},
        )

    raw_steps = payload.get("steps", [])
    if not isinstance(raw_steps, list):
        raw_steps = []

    steps: list[ReplayStep] = []
    for raw in raw_steps:
        normalized = _normalize_step(raw)
        if normalized is not None:
            steps.append(normalized)

    approvals_dir = run_dir / "approvals"
    artifacts["approvals_dir"] = approvals_dir.exists() and approvals_dir.is_dir()
    if bool(artifacts["approvals_dir"]):
        try:
            artifacts["approval_count"] = sum(
                1 for item in approvals_dir.glob("*.json") if item.is_file()
            )
        except OSError:
            artifacts["approval_count"] = 0

    final_stage = ""
    if isinstance(payload.get("latest_final_stage"), str):
        final_stage = str(payload.get("latest_final_stage", "")).strip()
    if not final_stage and steps:
        final_stage = steps[-1].final_stage

    latest_decision: dict[str, str] = {
        "decision_type": "",
        "computed_stage": "",
        "final_stage": "",
        "executed_stage": "",
    }
    if steps:
        last = steps[-1]
        latest_decision = {
            "decision_type": last.decision_type,
            "computed_stage": last.computed_stage,
            "final_stage": last.final_stage,
            "executed_stage": last.executed_stage,
        }
    else:
        latest_decision = {
            "decision_type": str(payload.get("latest_decision_type", "")).strip(),
            "computed_stage": "",
            "final_stage": final_stage,
            "executed_stage": "",
        }

    return RuntimeReplaySnapshot(
        run_id=str(payload.get("run_id", safe_run_id)).strip() or safe_run_id,
        final_stage=final_stage,
        executed_steps=steps,
        latest_decision=latest_decision,
        artifacts=artifacts,
        blockers=_collect_blockers(steps),
    )


def render_replay(snapshot: RuntimeReplaySnapshot) -> str:
    lines: list[str] = ["ForgeFlow Replay"]
    lines.append(f"Run ID: {snapshot.run_id}")
    lines.append(f"Final Stage: {snapshot.final_stage}")

    lines.append("Stages:")
    if snapshot.executed_steps:
        for idx, step in enumerate(snapshot.executed_steps, start=1):
            lines.append(
                f"- {idx}. computed={step.computed_stage} final={step.final_stage} executed={step.executed_stage}"
            )
    else:
        lines.append("- (no steps)")

    lines.append("Decisions:")
    if snapshot.executed_steps:
        for idx, step in enumerate(snapshot.executed_steps, start=1):
            lines.append(
                f"- {idx}. time={step.timestamp} decision={step.decision_type} input_len={len(step.input)}"
            )
    else:
        lines.append("- (no decisions)")

    lines.append("Blockers:")
    if snapshot.blockers:
        for item in snapshot.blockers:
            lines.append(f"- {item}")
    else:
        lines.append("- None")

    lines.append("Artifacts:")
    for key in ["run_dir_exists", "summary_json", "approvals_dir", "approval_count"]:
        lines.append(f"- {key}: {snapshot.artifacts.get(key)}")

    return "\n".join(lines)

