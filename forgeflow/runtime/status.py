from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.orchestrator import Orchestrator
from agents.orchestrator.backflow_evaluator import BackflowEvaluator
from agents.orchestrator.models import Stage
from agents.orchestrator.question_flow import QuestionFlow
from agents.orchestrator.stage_evaluator import StageEvaluator
from agents.state_manager import StateManager
from schemas.run_summary import RunSummaryModel
from forgeflow.runtime.pause import load_runtime_pause_state
from forgeflow.runtime.run_index import load_run_index
from forgeflow.runtime.lineage import invalidated_artifacts, load_lineage
from forgeflow.runtime.approval_queue import materialize_pending_reviews
def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


@dataclass(slots=True)
class RuntimeStatus:
    current_stage: str
    executed_stage: str
    next_stage: str | None
    artifacts: dict[str, bool]
    mutation_enabled: bool
    execution_mode: str
    blockers: list[str]
    last_decision: dict[str, str] | None = None
    lineage_entries: list[dict[str, Any]] = field(default_factory=list)
    invalidated_artifacts: list[str] = field(default_factory=list)
    pending_reviews: list[dict[str, Any]] = field(default_factory=list)
    runtime_paused: bool = False
    pause_reason: str = ""
    approval_artifacts: list[dict[str, Any]] = field(default_factory=list)


def _default_runs_root(state_dir: str | Path | None) -> Path:
    # Deprecated: prefer deriving from the resolved StateManager.state_dir to avoid
    # mixing state snapshots from one runtime root with run summaries from CWD.
    if state_dir:
        return Path(state_dir).parent / "runs"
    return Path.cwd() / ".forgeflow" / "runs"


def _find_latest_summary_path_from_index(runs_root: Path) -> Path | None:
    index = load_run_index(runs_root)
    if index is None or not index.runs:
        return None
    for entry in index.runs:
        rel = str(entry.summary_path).strip()
        if not rel:
            continue
        candidate = runs_root / rel
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _find_latest_summary_path_by_scan(runs_root: Path) -> Path | None:
    if not runs_root.exists():
        return None
    candidates = list(runs_root.glob("*/summary.json"))
    if not candidates:
        return None

    def _run_prefix_key(run_id: str) -> datetime:
        match = re.match(r"^(?P<prefix>\d{8}T\d{6}Z)-", run_id)
        if not match:
            return datetime.min.replace(tzinfo=timezone.utc)
        prefix = match.group("prefix")
        try:
            return datetime.strptime(prefix, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)

    def _parse_step_timestamp(raw: object) -> datetime:
        if not isinstance(raw, str):
            return datetime.min.replace(tzinfo=timezone.utc)
        text = raw.strip()
        if not text:
            return datetime.min.replace(tzinfo=timezone.utc)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed

    def _summary_step_key(path: Path) -> datetime:
        # Prefer payload timestamps to break ties when multiple run IDs share the
        # same second-level prefix (YYYYMMDDTHHMMSSZ-...).
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return datetime.min.replace(tzinfo=timezone.utc)
        if not isinstance(payload, dict):
            return datetime.min.replace(tzinfo=timezone.utc)
        steps = payload.get("steps", [])
        if not isinstance(steps, list) or not steps:
            return datetime.min.replace(tzinfo=timezone.utc)
        last = steps[-1]
        if not isinstance(last, dict):
            return datetime.min.replace(tzinfo=timezone.utc)
        return _parse_step_timestamp(last.get("timestamp"))

    def _run_key(path: Path) -> tuple[datetime, datetime, str]:
        run_id = path.parent.name
        return (
            _run_prefix_key(run_id),
            _summary_step_key(path),
            run_id,
        )

    # Prefer run identity over filesystem mtime: run IDs are timestamp-prefixed.
    candidates.sort(key=_run_key)
    return candidates[-1]


def _find_latest_summary_path(runs_root: Path) -> Path | None:
    return _find_latest_summary_path_from_index(runs_root) or _find_latest_summary_path_by_scan(
        runs_root
    )


def _load_summary_payload(summary_path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    try:
        model = RunSummaryModel.model_validate(payload)
    except Exception:
        return None
    return model.model_dump(mode="python")


def _load_latest_run_summary(runs_root: Path) -> dict[str, Any] | None:
    payload, _ = _load_latest_run_summary_with_path(runs_root)
    return payload


def _load_latest_run_summary_with_path(
    runs_root: Path,
) -> tuple[dict[str, Any] | None, Path | None]:
    index_path = _find_latest_summary_path_from_index(runs_root)
    if index_path is not None:
        loaded = _load_summary_payload(index_path)
        if loaded is not None:
            return loaded, index_path

    scan_path = _find_latest_summary_path_by_scan(runs_root)
    if scan_path is None:
        return None, None
    return _load_summary_payload(scan_path), scan_path


def _build_orchestrator_shell() -> Orchestrator:
    # Intentionally bypass Orchestrator.__init__ to keep this API read-only and
    # side-effect free (no new runs/ dirs created).
    shell = object.__new__(Orchestrator)
    stage_evaluator = StageEvaluator()
    shell.stage_evaluator = stage_evaluator  # type: ignore[attr-defined]
    shell.question_flow = QuestionFlow()  # type: ignore[attr-defined]
    shell.backflow_evaluator = BackflowEvaluator(  # type: ignore[attr-defined]
        is_requirements_ready=stage_evaluator.is_requirements_ready,
        is_solution_ready=stage_evaluator.is_solution_ready,
    )
    # resolve_transition() checks membership in self.agents for answered questions.
    # Provide a minimal stage-key mapping without constructing real agents.
    shell.agents = {  # type: ignore[attr-defined]
        Stage.REQUIREMENTS: None,
        Stage.SOLUTION: None,
        Stage.DESIGN: None,
        Stage.IMPLEMENTATION: None,
        Stage.TESTING: None,
    }
    return shell


def _artifact_availability(state_manager: StateManager) -> dict[str, bool]:
    available: dict[str, bool] = {}
    for state_key in state_manager.STATE_FILES:
        try:
            available[state_key] = state_manager.get_state_path(state_key).exists()
        except KeyError:
            continue
    return available


def _collect_blockers(
    states: dict[str, dict[str, Any]],
    validation_errors: dict[str, str],
) -> list[str]:
    blockers: list[str] = []

    question_state = states.get("question_state", {})
    if (
        question_state.get("blocking")
        and question_state.get("status") == "awaiting_user"
        and question_state.get("questions")
    ):
        stage_name = str(question_state.get("stage_name", "")).strip() or "UNKNOWN"
        blockers.append(f"waiting_user_input(stage={stage_name})")

    implementation = states.get("implementation_status", {})
    impl_blockers = implementation.get("blockers", [])
    if isinstance(impl_blockers, list):
        for item in impl_blockers:
            text = str(item).strip()
            if text:
                blockers.append(f"implementation: {text}")

    if validation_errors:
        for state_key, message in sorted(validation_errors.items()):
            msg = str(message).strip()
            if msg:
                blockers.append(f"state_validation({state_key}): {msg}")

    test_report = states.get("test_report", {})
    issues = test_report.get("issues", [])
    if isinstance(issues, list):
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            status = str(issue.get("status", "")).strip().lower()
            severity = str(issue.get("severity", "")).strip().lower()
            if status not in {"open", "confirmed"}:
                continue
            if severity not in {"high", "critical"}:
                continue
            title = str(issue.get("title", "")).strip() or "testing_issue"
            blockers.append(f"testing({severity}): {title}")

    return blockers


def build_status_snapshot(state_dir: str | None = None) -> RuntimeStatus:
    state_manager = StateManager(state_dir=state_dir)
    states = state_manager.load_all_states()
    pause_state = load_runtime_pause_state(state_dir=state_manager.state_dir)

    orchestrator_shell = _build_orchestrator_shell()
    decision = Orchestrator.resolve_transition(orchestrator_shell, states)

    # Always derive runs root from the resolved state directory (not CWD), so
    # status reads a consistent runtime snapshot even when invoked from another
    # working directory.
    runs_root = Path(state_manager.state_dir).parent / "runs"
    summary, summary_path = _load_latest_run_summary_with_path(runs_root)

    executed_stage = ""
    last_decision: dict[str, str] | None = None
    if summary:
        steps = summary.get("steps", [])
        if isinstance(steps, list) and steps:
            last_step = steps[-1] if isinstance(steps[-1], dict) else {}
            executed_stage = str(last_step.get("executed_stage", "")).strip()
        last_decision = {
            "action": str(summary.get("latest_decision_type", "")).strip(),
            "final_stage": str(summary.get("latest_final_stage", "")).strip(),
            "summary": str(summary.get("latest_summary", "")).strip(),
        }

    blockers = _collect_blockers(states, getattr(state_manager, "validation_errors", {}))
    if pause_state.paused:
        blockers = list(blockers) + ["runtime_paused"]

    lineage_entries: list[dict[str, Any]] = []
    invalidated: list[str] = []
    if summary_path is not None:
        lineage = load_lineage(summary_path.parent)
        if lineage is not None:
            lineage_entries = [
                {
                    "artifact": item.artifact,
                    "depends_on": list(item.depends_on),
                    "generated_by": item.generated_by,
                    "invalidated_by": list(item.invalidated_by),
                }
                for item in lineage.entries
            ]
            invalidated = invalidated_artifacts(lineage)

    pending_reviews: list[dict[str, Any]] = []
    pending = materialize_pending_reviews(runs_root)
    pending_reviews = [{"run_id": item.run_id, "artifact": item.artifact} for item in pending[:50]]

    approval_artifacts: list[dict[str, Any]] = []
    if summary_path is not None:
        approvals_dir = summary_path.parent / "approvals"
        if approvals_dir.exists() and approvals_dir.is_dir():
            for path in sorted(approvals_dir.glob("*.json"))[:50]:
                approval = _load_json_object(path)
                if not approval:
                    continue
                approval_artifacts.append(
                    {
                        "contract_hash": str(approval.get("contract_hash", "")).strip(),
                        "approval_status": str(approval.get("approval_status", "")).strip(),
                        "target_module": str(approval.get("target_module", "")).strip(),
                        "stale": bool(approval.get("stale", False)),
                    }
                )

    return RuntimeStatus(
        current_stage=str(decision.final_stage),
        executed_stage=executed_stage,
        next_stage=str(decision.next_stage_to_execute)
        if decision.next_stage_to_execute is not None
        else None,
        artifacts=_artifact_availability(state_manager),
        mutation_enabled=False,
        execution_mode="preview-only",
        blockers=blockers,
        last_decision=last_decision,
        lineage_entries=lineage_entries,
        invalidated_artifacts=invalidated,
        pending_reviews=pending_reviews,
        runtime_paused=pause_state.paused,
        pause_reason=pause_state.reason,
        approval_artifacts=approval_artifacts,
    )
