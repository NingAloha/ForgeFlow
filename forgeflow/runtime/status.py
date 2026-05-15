from __future__ import annotations

import json
import re
from dataclasses import dataclass
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


def _default_runs_root(state_dir: str | Path | None) -> Path:
    # Deprecated: prefer deriving from the resolved StateManager.state_dir to avoid
    # mixing state snapshots from one runtime root with run summaries from CWD.
    if state_dir:
        return Path(state_dir).parent / "runs"
    return Path.cwd() / ".forgeflow" / "runs"


def _find_latest_summary_path(runs_root: Path) -> Path | None:
    if not runs_root.exists():
        return None
    candidates = list(runs_root.glob("*/summary.json"))
    if not candidates:
        return None

    def _run_key(path: Path) -> tuple[datetime, str]:
        run_id = path.parent.name
        match = re.match(r"^(?P<prefix>\d{8}T\d{6}Z)-", run_id)
        if match:
            prefix = match.group("prefix")
            try:
                parsed = datetime.strptime(prefix, "%Y%m%dT%H%M%SZ").replace(
                    tzinfo=timezone.utc
                )
                return parsed, run_id
            except ValueError:
                pass
        return datetime.min.replace(tzinfo=timezone.utc), run_id

    # Prefer run identity over filesystem mtime: run IDs are timestamp-prefixed.
    candidates.sort(key=_run_key)
    return candidates[-1]


def _load_latest_run_summary(runs_root: Path) -> dict[str, Any] | None:
    summary_path = _find_latest_summary_path(runs_root)
    if summary_path is None:
        return None
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

    orchestrator_shell = _build_orchestrator_shell()
    decision = Orchestrator.resolve_transition(orchestrator_shell, states)

    # Always derive runs root from the resolved state directory (not CWD), so
    # status reads a consistent runtime snapshot even when invoked from another
    # working directory.
    runs_root = Path(state_manager.state_dir).parent / "runs"
    summary = _load_latest_run_summary(runs_root)

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
    )
