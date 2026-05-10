from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from agents.orchestrator import OrchestrationResult, Orchestrator
from agents.orchestrator.models import Stage
from agents.state_manager import StateManager
from schemas.run_summary import RunSummaryModel


def build_user_input(args: argparse.Namespace) -> str:
    if args.user_input:
        return " ".join(args.user_input).strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return ""


def classify_decision(result: OrchestrationResult) -> str:
    if result.diagnostic.get("decision_type"):
        return str(result.diagnostic["decision_type"])
    decision = result.decision
    if decision.wait_for_user_input:
        return "WAIT"
    if decision.backflow_target is not None:
        return "BACKFLOW"
    if decision.next_stage_to_execute is not None:
        return "FORWARD"
    if decision.final_stage == Stage.INIT and result.executed_stage is not None:
        return "BOOTSTRAP"
    if decision.should_stay:
        return "STAY"
    return "EXECUTE"


def changed_state_keys(result: OrchestrationResult) -> list[str]:
    diagnostic_changes = result.diagnostic.get("state_changes")
    if isinstance(diagnostic_changes, list):
        return [str(item) for item in diagnostic_changes]
    changed: list[str] = []
    all_keys = set(result.states_before) | set(result.states_after)
    for state_key in sorted(all_keys):
        if result.states_before.get(state_key) != result.states_after.get(state_key):
            changed.append(state_key)
    return changed


def format_question_state(question_state: dict[str, Any]) -> str:
    status = question_state.get("status", "idle")
    if status == "idle":
        return "idle"

    stage_name = question_state.get("stage_name", "")
    state_key = question_state.get("state_key", "")
    blocking = question_state.get("blocking", False)
    question_count = int(
        question_state.get(
            "question_count",
            len(question_state.get("questions", [])),
        )
    )
    blocking_text = "blocking" if blocking else "non-blocking"
    return (
        f"{status} ({blocking_text}) for {stage_name or 'UNKNOWN'} / "
        f"{state_key or 'unknown'} with {question_count} question(s)"
    )


def llm_outcome_from_status(status: str) -> str:
    return {
        "success": "success",
        "retryable_error": "retry exhausted",
        "fatal_error": "blocked",
        "needs_user_input": "needs user input",
    }.get(status, "unknown")


def format_diagnostic_report(result: OrchestrationResult) -> str:
    decision = result.decision
    diagnostic = result.diagnostic
    changed_states = changed_state_keys(result)
    question_view = diagnostic.get("question_state", result.states_after.get("question_state", {}))
    execution_view = diagnostic.get("execution", {})
    transition_view = diagnostic.get("transition", {})
    stage_view = diagnostic.get("stages", {})
    lines = [
        "ForgeFlow Diagnostic",
        f"Decision: {classify_decision(result)}",
        "Stages:",
        f"- computed: {stage_view.get('computed', decision.computed_stage)}",
        f"- source: {stage_view.get('source', decision.source_stage or 'None') or 'None'}",
        f"- final: {stage_view.get('final', decision.final_stage)}",
        f"- executed: {stage_view.get('executed', result.executed_stage or 'None') or 'None'}",
        "Transition:",
        f"- reason: {transition_view.get('reason', decision.reason)}",
        f"- summary: {result.summary}",
    ]

    if decision.next_stage_to_execute is not None:
        lines.append(
            "- next stage to execute: "
            f"{transition_view.get('next_stage_to_execute', decision.next_stage_to_execute)}"
        )
    if decision.backflow_target is not None:
        lines.append(
            f"- backflow target: {transition_view.get('backflow_target', decision.backflow_target)}"
        )

    if result.agent_result is not None:
        lines.extend(
            [
                "Execution:",
                f"- agent: {execution_view.get('agent_name', result.agent_result.agent_name)}",
                f"- state key: {execution_view.get('state_key', result.agent_result.state_key)}",
                f"- handoff ready: {'yes' if execution_view.get('handoff_ready', result.agent_result.handoff_ready) else 'no'}",
                f"- requires user input: {'yes' if execution_view.get('requires_user_input', result.agent_result.requires_user_input) else 'no'}",
            ]
        )
        blockers = execution_view.get("blockers", result.agent_result.blockers)
        if blockers:
            lines.append(f"- blockers: {', '.join(blockers)}")

    lines.extend(
        [
            "State Changes:",
            f"- changed states: {', '.join(changed_states) if changed_states else 'None'}",
            (
                "- question state: "
                + format_question_state(question_view)
            ),
        ]
    )

    evidence = transition_view.get("evidence", decision.evidence)
    if evidence:
        lines.append("Evidence:")
        lines.extend(f"- {item}" for item in evidence)

    llm_trace = diagnostic.get("llm_trace", {})
    if llm_trace:
        lines.append("LLM Trace:")
        status = str(llm_trace.get("status", ""))
        failure_type = str(llm_trace.get("failure_type", ""))
        if status:
            lines.append(f"- status: {status}")
        if failure_type:
            lines.append(f"- failure type: {failure_type}")
        if status:
            lines.append(f"- invoked: {'yes' if status != 'none' else 'no'}")
            lines.append(f"- outcome: {llm_outcome_from_status(status)}")
        if llm_trace.get("provider"):
            lines.append(f"- provider: {llm_trace.get('provider')}")
        if llm_trace.get("model"):
            lines.append(f"- model: {llm_trace.get('model')}")
        if llm_trace.get("protocol"):
            lines.append(f"- protocol: {llm_trace.get('protocol')}")
        lines.append(f"- latency ms: {llm_trace.get('latency_ms', 0)}")
        if llm_trace.get("error"):
            lines.append(f"- error: {llm_trace.get('error')}")

    validation_errors = diagnostic.get("state_validation_errors", {})
    if validation_errors:
        lines.append("State Validation Errors:")
        for key, message in sorted(validation_errors.items()):
            lines.append(f"- {key}: {message}")

    execution_trace = diagnostic.get("execution_trace", {})
    if execution_trace:
        lines.append("Execution Trace:")
        workspace = execution_trace.get("workspace_path", "")
        if workspace:
            lines.append(f"- workspace: {workspace}")
        file_writes = execution_trace.get("file_writes", [])
        if file_writes:
            lines.append(f"- files written: {len(file_writes)}")
        command_results = execution_trace.get("command_results", [])
        suggested_command = execution_trace.get("suggested_command", [])
        if suggested_command:
            lines.append(f"- suggested command: {' '.join(suggested_command)}")
        executed_command = execution_trace.get("executed_command", [])
        if executed_command:
            lines.append(f"- executed command: {' '.join(executed_command)}")
        for item in command_results:
            cmd = " ".join(item.get("command", []))
            exit_code = item.get("exit_code", "")
            lines.append(f"- command: {cmd} (exit={exit_code})")

    run_meta = diagnostic.get("run", {})
    if run_meta:
        lines.append("Run Artifact:")
        if run_meta.get("run_id"):
            lines.append(f"- run id: {run_meta.get('run_id')}")
        if run_meta.get("generated_project_dir"):
            lines.append(f"- generated project dir: {run_meta.get('generated_project_dir')}")
        if run_meta.get("runs_dir"):
            lines.append(f"- run summary dir: {run_meta.get('runs_dir')}")

    return "\n".join(lines)


def load_run_summary(run_id: str, state_dir: str | None) -> dict[str, Any]:
    if state_dir:
        runs_root = Path(state_dir).parent / "runs"
    else:
        runs_root = Path.cwd() / ".forgeflow" / "runs"
    summary_path = runs_root / run_id / "summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Run summary not found: {summary_path}")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Run summary payload must be an object.")
    return RunSummaryModel.model_validate(payload).model_dump(mode="python")


def format_replay_report(summary: dict[str, Any]) -> str:
    lines = ["ForgeFlow Replay"]
    lines.append(f"Run ID: {summary.get('run_id', '')}")
    lines.append(f"Original Request: {summary.get('original_request', '')}")
    lines.append(f"Generated Project Dir: {summary.get('generated_project_dir', '')}")
    lines.append(f"Latest Decision: {summary.get('latest_decision_type', '')}")
    lines.append(f"Latest Stage: {summary.get('latest_final_stage', '')}")

    steps = summary.get("steps", [])
    if not isinstance(steps, list):
        steps = []
    lines.append(f"Steps: {len(steps)}")

    for idx, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            continue
        lines.append(f"--- Step {idx} ---")
        lines.append(f"time: {step.get('timestamp', '')}")
        lines.append(
            "decision: "
            f"{step.get('decision_type', '')} | "
            f"computed={step.get('computed_stage', '')} "
            f"final={step.get('final_stage', '')} "
            f"executed={step.get('executed_stage', '')}"
        )
        llm_trace = step.get("llm_trace", {})
        if isinstance(llm_trace, dict) and llm_trace:
            status = str(llm_trace.get("status", ""))
            failure_type = str(llm_trace.get("failure_type", ""))
            lines.append(
                "llm: "
                f"status={status} "
                f"failure={failure_type} "
                f"latency_ms={llm_trace.get('latency_ms', 0)} "
                f"outcome={llm_outcome_from_status(status)}"
            )
        execution_trace = step.get("execution_trace", {})
        if isinstance(execution_trace, dict) and execution_trace:
            lines.append(
                "execution: "
                f"workspace={execution_trace.get('workspace_path', '')} "
                f"writes={len(execution_trace.get('file_writes', [])) if isinstance(execution_trace.get('file_writes', []), list) else 0} "
                f"commands={len(execution_trace.get('command_results', [])) if isinstance(execution_trace.get('command_results', []), list) else 0}"
            )
        state_changes = step.get("state_changes", [])
        if isinstance(state_changes, list):
            lines.append(f"state_changes: {', '.join(state_changes) if state_changes else 'None'}")
        question_state = step.get("question_state", {})
        if isinstance(question_state, dict):
            lines.append(
                "question_state: "
                f"{question_state.get('status', 'idle')} "
                f"blocking={question_state.get('blocking', False)} "
                f"stage={question_state.get('stage_name', '')}"
            )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the ForgeFlow orchestrator for a single input."
    )
    parser.add_argument(
        "user_input",
        nargs="*",
        help="User request to send into the orchestrator.",
    )
    parser.add_argument(
        "--state-dir",
        dest="state_dir",
        default=None,
        help="Optional state directory for isolated runs.",
    )
    parser.add_argument(
        "--auto-run",
        action="store_true",
        help="Continuously run until DONE or WAIT.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=20,
        help="Max orchestration steps in --auto-run mode.",
    )
    parser.add_argument(
        "--replay-run",
        dest="replay_run",
        default=None,
        help="Replay diagnostics from runs/<run_id>/summary.json in read-only mode.",
    )
    args = parser.parse_args()

    if args.replay_run:
        try:
            summary = load_run_summary(args.replay_run, args.state_dir)
        except (FileNotFoundError, ValueError) as exc:
            print(f"Replay error: {exc}", file=sys.stderr)
            return 1
        print(format_replay_report(summary))
        return 0

    orchestrator = Orchestrator(
        state_manager=StateManager(state_dir=args.state_dir)
        if args.state_dir is not None
        else None
    )
    user_input = build_user_input(args)
    if args.auto_run:
        max_steps = max(1, args.max_steps)
        for step in range(1, max_steps + 1):
            step_input = user_input if step == 1 else ""
            result = orchestrator.orchestrate(
                step_input,
                original_request=user_input,
            )
            print(f"=== Auto Run Step {step} ===")
            print(format_diagnostic_report(result))
            if result.decision.wait_for_user_input:
                break
            if result.decision.final_stage == Stage.DONE:
                break
    else:
        result = orchestrator.orchestrate(
            user_input,
            original_request=user_input,
        )
        print(format_diagnostic_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
