from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from agents.orchestrator import OrchestrationResult, Orchestrator
from agents.orchestrator.models import Stage
from agents.state_manager import StateManager


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


def normalize_mapping(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="python")  # type: ignore[attr-defined]
        return dumped if isinstance(dumped, dict) else {}
    if isinstance(value, dict):
        return value
    return {}


def format_diagnostic_report(result: OrchestrationResult) -> str:
    decision = result.decision
    diagnostic = result.diagnostic
    changed_states = changed_state_keys(result)
    question_view = diagnostic.get(
        "question_state", result.states_after.get("question_state", {})
    )
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
            ("- question state: " + format_question_state(question_view)),
        ]
    )

    evidence = transition_view.get("evidence", decision.evidence)
    if evidence:
        lines.append("Evidence:")
        lines.extend(f"- {item}" for item in evidence)

    llm_trace = normalize_mapping(diagnostic.get("llm_trace", {}))
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
            lines.append(
                f"- generated project dir: {run_meta.get('generated_project_dir')}"
            )
        if run_meta.get("runs_dir"):
            lines.append(f"- run summary dir: {run_meta.get('runs_dir')}")

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
        "--run-id",
        dest="run_id",
        default=None,
        help="Target run_id for run-scoped write commands.",
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
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print a read-only runtime status overview and exit.",
    )
    parser.add_argument(
        "--repair-run-index",
        action="store_true",
        help="Rebuild runs/index.json from run directories and exit.",
    )
    parser.add_argument(
        "--review-run",
        dest="review_run",
        default=None,
        help="Target run_id for writing an explicit review decision (write-path).",
    )
    parser.add_argument(
        "--review-artifact",
        dest="review_artifact",
        default=None,
        help="Target artifact name for --review-run (e.g. spec/solution/system_design/implementation_status/test_report).",
    )
    parser.add_argument(
        "--review-approve",
        action="store_true",
        help="Mark the target artifact as approved in review_state.json.",
    )
    parser.add_argument(
        "--review-reject",
        action="store_true",
        help="Mark the target artifact as rejected in review_state.json.",
    )
    parser.add_argument(
        "--review-by",
        dest="review_by",
        default="",
        help="Optional reviewer identifier for review decisions.",
    )
    parser.add_argument(
        "--review-reason",
        dest="review_reason",
        default="",
        help="Optional human review reason for review decisions.",
    )
    parser.add_argument(
        "--execution-gate",
        action="store_true",
        help="Print read-only controlled-execution gate diagnostics and exit.",
    )
    parser.add_argument(
        "--request-execution",
        action="store_true",
        help="Materialize an execution intent artifact under runs/<run_id>/ (write-path; no execution).",
    )
    parser.add_argument(
        "--requested-by",
        dest="requested_by",
        default="",
        help="Optional requester identifier for --request-execution.",
    )
    parser.add_argument(
        "--notes",
        dest="notes",
        default="",
        help="Optional notes for --request-execution.",
    )
    parser.add_argument(
        "--enable-mutation",
        action="store_true",
        help="Attempt to enable mutation (Phase E remains blocked by design; diagnostic only).",
    )
    parser.add_argument(
        "--rerun-plan",
        action="store_true",
        help="Materialize an approval-aware rerun plan under runs/<run_id>/ and exit (write-path; no rerun).",
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Start the minimal ForgeShell TUI wrapper.",
    )
    args = parser.parse_args()

    if args.repair_run_index:
        from forgeflow.runtime.run_index_repair import repair_run_index

        state_manager = StateManager(state_dir=args.state_dir) if args.state_dir is not None else StateManager()
        runs_root = Path(state_manager.state_dir).parent / "runs"
        result = repair_run_index(runs_root)
        print(f"Repaired runs index: runs_written={result.runs_written}")
        return 0

    if args.review_run or args.review_artifact or args.review_approve or args.review_reject:
        from forgeflow.runtime.review_decision import write_review_decision

        if not args.review_run or not args.review_artifact:
            print("Review error: --review-run and --review-artifact are required.", file=sys.stderr)
            return 2
        if args.review_approve and args.review_reject:
            print("Review error: choose exactly one of --review-approve or --review-reject.", file=sys.stderr)
            return 2
        if not args.review_approve and not args.review_reject:
            print("Review error: missing --review-approve/--review-reject.", file=sys.stderr)
            return 2
        status = "approved" if args.review_approve else "rejected"

        state_manager = StateManager(state_dir=args.state_dir) if args.state_dir is not None else StateManager()
        runs_root = Path(state_manager.state_dir).parent / "runs"
        try:
            result = write_review_decision(
                runs_root=runs_root,
                run_id=args.review_run,
                artifact=args.review_artifact,
                review_status=status,
                reviewed_by=args.review_by,
                review_reason=args.review_reason,
            )
        except Exception as exc:
            print(f"Review error: {exc}", file=sys.stderr)
            return 1
        print(
            f"Review decision written: run_id={result.run_id} artifact={result.artifact} status={result.review_status}"
        )
        return 0

    if args.execution_gate:
        from forgeflow.runtime.execution_gate import build_execution_gate_snapshot, render_execution_gate

        state_manager = (
            StateManager(state_dir=args.state_dir)
            if args.state_dir is not None
            else StateManager()
        )
        snapshot = build_execution_gate_snapshot(
            state_dir=Path(state_manager.state_dir),
            run_id=args.run_id,
        )
        print(render_execution_gate(snapshot))
        return 0

    if args.request_execution:
        from forgeflow.runtime.execution_request import write_execution_request

        if not args.run_id:
            print("Execution request error: --run-id is required.", file=sys.stderr)
            return 1
        state_manager = (
            StateManager(state_dir=args.state_dir)
            if args.state_dir is not None
            else StateManager()
        )
        runs_root = Path(state_manager.state_dir).parent / "runs"
        try:
            path = write_execution_request(
                runs_root=runs_root,
                run_id=args.run_id,
                requested_by=args.requested_by,
                notes=args.notes,
            )
        except Exception as exc:
            print(f"Execution request error: {exc}", file=sys.stderr)
            return 1
        print(f"Wrote execution request: {path}")
        return 0

    if args.enable_mutation:
        from forgeflow.runtime.controlled_execution import render_controlled_execution_blocked

        if not args.run_id:
            print("Execution toggle error: --run-id is required.", file=sys.stderr)
            return 1
        state_manager = (
            StateManager(state_dir=args.state_dir)
            if args.state_dir is not None
            else StateManager()
        )
        try:
            result = render_controlled_execution_blocked(
                state_dir=Path(state_manager.state_dir),
                run_id=args.run_id,
                require_request_present=True,
            )
        except Exception as exc:
            print(f"Execution toggle error: {exc}", file=sys.stderr)
            return 1
        print(result.output)
        return 0

    if args.rerun_plan:
        from forgeflow.runtime.rerun_plan import write_rerun_plan

        if not args.run_id:
            print("Rerun plan error: --run-id is required.", file=sys.stderr)
            return 1
        state_manager = (
            StateManager(state_dir=args.state_dir)
            if args.state_dir is not None
            else StateManager()
        )
        try:
            result = write_rerun_plan(
                state_dir=Path(state_manager.state_dir),
                run_id=args.run_id,
            )
        except Exception as exc:
            print(f"Rerun plan error: {exc}", file=sys.stderr)
            return 1
        print(f"Wrote rerun plan: {result.path}")
        print(f"Plan status: {result.plan_status}")
        return 0

    if args.status:
        from forgeflow.runtime.render import render_status
        from forgeflow.runtime.status import build_status_snapshot

        print(render_status(build_status_snapshot(args.state_dir)))
        return 0

    if args.tui:
        from tui.app import ForgeShellApp

        app = ForgeShellApp(state_dir=args.state_dir)
        return app.run()

    if args.replay_run:
        from forgeflow.runtime.replay import ReplayLoadError, load_replay_snapshot, render_replay

        try:
            snapshot = load_replay_snapshot(args.replay_run, args.state_dir)
        except ReplayLoadError as exc:
            suffix = f"{exc.code}: {exc.message}"
            print(f"Replay error: {suffix}", file=sys.stderr)
            if exc.details:
                try:
                    print(json.dumps(exc.details, ensure_ascii=False), file=sys.stderr)
                except TypeError:
                    pass
            return 1
        except Exception as exc:
            print(f"Replay error: {exc}", file=sys.stderr)
            return 1
        print(render_replay(snapshot))
        return 0

    orchestrator = Orchestrator(
        state_manager=StateManager(state_dir=args.state_dir)
        if args.state_dir is not None
        else None
    )
    user_input = build_user_input(args)
    if args.auto_run:
        max_steps = max(1, args.max_steps)
        prev_final_stage = ""
        prev_decision_type = ""
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
            decision_type = classify_decision(result)
            changed_states = changed_state_keys(result)
            same_stage = str(result.decision.final_stage) == prev_final_stage
            same_decision = decision_type == prev_decision_type
            no_state_change = not changed_states
            requires_user_input = bool(
                result.agent_result.requires_user_input
                if result.agent_result is not None
                else False
            )
            if (
                same_stage
                and same_decision
                and no_state_change
                and not result.decision.wait_for_user_input
                and not requires_user_input
            ):
                print(
                    "NO_PROGRESS: stopping auto-run "
                    f"(stage={result.decision.final_stage}, decision={decision_type}, step={step})"
                )
                orchestrator.record_auto_run_stop(
                    stop_reason="no_progress",
                    repeated_stage=result.decision.final_stage,
                    repeated_decision=decision_type,
                    step_index=step,
                )
                break
            prev_final_stage = str(result.decision.final_stage)
            prev_decision_type = decision_type
    else:
        result = orchestrator.orchestrate(
            user_input,
            original_request=user_input,
        )
        print(format_diagnostic_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
