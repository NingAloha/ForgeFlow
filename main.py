from __future__ import annotations

import argparse
import sys
from typing import Any

from agents.orchestrator import OrchestrationResult, Orchestrator


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
    if decision.forward_target is not None:
        return "FORWARD"
    if decision.final_stage == "INIT" and result.executed_stage is not None:
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

    if decision.forward_target is not None:
        lines.append(
            f"- forward target: {transition_view.get('forward_target', decision.forward_target)}"
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
    args = parser.parse_args()

    orchestrator = Orchestrator()
    result = orchestrator.orchestrate(build_user_input(args))
    print(format_diagnostic_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
