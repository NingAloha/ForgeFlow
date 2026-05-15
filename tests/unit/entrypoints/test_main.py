from __future__ import annotations

import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from agents.base import AgentResult
from agents.orchestrator import OrchestrationResult, Stage, TransitionDecision
from main import (
    changed_state_keys,
    classify_decision,
    format_diagnostic_report,
    main,
)
from forgeflow.runtime.replay import load_replay_snapshot, render_replay
from schemas.llm_trace import LLMTraceModel


class MainDiagnosticViewTests(unittest.TestCase):
    def test_classify_decision_marks_bootstrap_runs(self) -> None:
        result = OrchestrationResult(
            decision=TransitionDecision(
                computed_stage=Stage.INIT,
                final_stage=Stage.INIT,
                should_stay=True,
                reason="Stay on current stage.",
            ),
            executed_stage=Stage.REQUIREMENTS,
            summary="Resolved stage to INIT; executed REQUIREMENTS via Requirements Engineer.",
        )

        self.assertEqual(classify_decision(result), "BOOTSTRAP")

    def test_classify_decision_uses_stage_enum_for_bootstrap(self) -> None:
        result = OrchestrationResult(
            decision=TransitionDecision(
                computed_stage=Stage.INIT,
                final_stage=Stage.INIT,
                should_stay=False,
                reason="Bootstrap run.",
            ),
            executed_stage=Stage.REQUIREMENTS,
        )
        self.assertEqual(classify_decision(result), "BOOTSTRAP")

    def test_changed_state_keys_returns_only_modified_states(self) -> None:
        result = OrchestrationResult(
            decision=TransitionDecision(
                computed_stage=Stage.REQUIREMENTS,
                final_stage=Stage.REQUIREMENTS,
                should_stay=True,
                reason="Stay on current stage.",
            ),
            states_before={
                "spec": {"project_goal": ""},
                "question_state": {"status": "idle"},
            },
            states_after={
                "spec": {"project_goal": "Build a workflow"},
                "question_state": {"status": "awaiting_user"},
            },
        )

        self.assertEqual(changed_state_keys(result), ["question_state", "spec"])

    def test_format_diagnostic_report_surfaces_wait_and_question_state(self) -> None:
        result = OrchestrationResult(
            decision=TransitionDecision(
                computed_stage=Stage.REQUIREMENTS,
                final_stage=Stage.REQUIREMENTS,
                wait_for_user_input=True,
                should_stay=True,
                reason="Waiting for user input.",
                evidence=["question_state is blocking and awaiting user response."],
            ),
            executed_stage=None,
            agent_result=AgentResult(
                agent_name="Requirements Engineer",
                stage_name="REQUIREMENTS",
                state_key="spec",
                updated_state={"open_questions": ["project_goal"]},
                summary="Requirements need clarification before spec can be completed.",
                handoff_ready=False,
                requires_user_input=True,
            ),
            states_before={
                "spec": {"project_goal": ""},
                "question_state": {"status": "idle"},
            },
            states_after={
                "spec": {"project_goal": ""},
                "question_state": {
                    "status": "awaiting_user",
                    "stage_name": "REQUIREMENTS",
                    "state_key": "spec",
                    "blocking": True,
                    "questions": [{"id": "project_goal"}],
                },
            },
            summary="Resolved stage to REQUIREMENTS; waiting for user input.",
        )

        report = format_diagnostic_report(result)

        self.assertIn("Decision: WAIT", report)
        self.assertIn("question state: awaiting_user (blocking)", report)
        self.assertIn("changed states: question_state", report)
        self.assertIn("Evidence:", report)

    def test_format_diagnostic_report_surfaces_state_validation_errors(self) -> None:
        result = OrchestrationResult(
            decision=TransitionDecision(
                computed_stage=Stage.INIT,
                final_stage=Stage.INIT,
                should_stay=True,
                reason="Stay on current stage.",
            ),
            diagnostic={
                "decision_type": "STAY",
                "state_changes": [],
                "question_state": {"status": "idle"},
                "transition": {"reason": "Stay on current stage.", "evidence": []},
                "stages": {
                    "computed": "INIT",
                    "source": "",
                    "final": "INIT",
                    "executed": "",
                },
                "state_validation_errors": {"spec": "Input should be a valid string"},
            },
            summary="ok",
        )
        report = format_diagnostic_report(result)
        self.assertIn("State Validation Errors:", report)
        self.assertIn("spec: Input should be a valid string", report)

    def test_format_diagnostic_report_surfaces_llm_trace(self) -> None:
        result = OrchestrationResult(
            decision=TransitionDecision(
                computed_stage=Stage.REQUIREMENTS,
                final_stage=Stage.REQUIREMENTS,
                should_stay=True,
                reason="Stay on current stage.",
            ),
            diagnostic={
                "decision_type": "STAY",
                "state_changes": ["spec"],
                "question_state": {"status": "idle"},
                "transition": {"reason": "Stay on current stage.", "evidence": []},
                "stages": {
                    "computed": "REQUIREMENTS",
                    "source": "REQUIREMENTS",
                    "final": "REQUIREMENTS",
                    "executed": "REQUIREMENTS",
                },
                "llm_trace": {
                    "status": "retryable_error",
                    "failure_type": "timeout",
                    "provider": "deepseek",
                    "model": "deepseek-v4-flash",
                    "protocol": "openai",
                    "latency_ms": 42,
                    "error": "timeout",
                },
            },
            summary="ok",
        )
        report = format_diagnostic_report(result)
        self.assertIn("LLM Trace:", report)
        self.assertIn("status: retryable_error", report)
        self.assertIn("invoked: yes", report)
        self.assertIn("failure type: timeout", report)
        self.assertIn("outcome: retry exhausted", report)
        self.assertIn("error: timeout", report)

    def test_format_diagnostic_report_accepts_typed_llm_trace(self) -> None:
        result = OrchestrationResult(
            decision=TransitionDecision(
                computed_stage=Stage.REQUIREMENTS,
                final_stage=Stage.REQUIREMENTS,
                should_stay=True,
                reason="Stay on current stage.",
            ),
            diagnostic={
                "decision_type": "STAY",
                "state_changes": [],
                "question_state": {"status": "idle"},
                "transition": {"reason": "Stay on current stage.", "evidence": []},
                "stages": {
                    "computed": "REQUIREMENTS",
                    "source": "REQUIREMENTS",
                    "final": "REQUIREMENTS",
                    "executed": "REQUIREMENTS",
                },
                "llm_trace": LLMTraceModel(
                    status="success",
                    failure_type="none",
                    repair_attempts=0,
                    validation_errors=[],
                    raw_excerpt="{}",
                    model="m",
                    provider="p",
                    protocol="openai",
                    latency_ms=1,
                    error=None,
                ),
            },
            summary="ok",
        )
        report = format_diagnostic_report(result)
        self.assertIn("status: success", report)
        self.assertIn("outcome: success", report)

    def test_format_diagnostic_report_uses_status_failure_without_legacy_flags(
        self,
    ) -> None:
        for status, failure, expect_outcome in [
            ("success", "none", "success"),
            ("retryable_error", "schema_error", "retry exhausted"),
            ("fatal_error", "auth_error", "blocked"),
            ("needs_user_input", "policy_block", "needs user input"),
        ]:
            with self.subTest(status=status):
                result = OrchestrationResult(
                    decision=TransitionDecision(
                        computed_stage=Stage.REQUIREMENTS,
                        final_stage=Stage.REQUIREMENTS,
                        should_stay=True,
                        reason="Stay on current stage.",
                    ),
                    diagnostic={
                        "decision_type": "STAY",
                        "state_changes": ["spec"],
                        "question_state": {"status": "idle"},
                        "transition": {
                            "reason": "Stay on current stage.",
                            "evidence": [],
                        },
                        "stages": {
                            "computed": "REQUIREMENTS",
                            "source": "REQUIREMENTS",
                            "final": "REQUIREMENTS",
                            "executed": "REQUIREMENTS",
                        },
                        "llm_trace": {
                            "status": status,
                            "failure_type": failure,
                            "latency_ms": 10,
                        },
                    },
                    summary="ok",
                )
                report = format_diagnostic_report(result)
                self.assertIn(f"status: {status}", report)
                expected_invoked = "no" if status == "none" else "yes"
                self.assertIn(f"invoked: {expected_invoked}", report)
                self.assertIn(f"failure type: {failure}", report)
                self.assertIn(f"outcome: {expect_outcome}", report)

    def test_format_diagnostic_report_ignores_legacy_flags_when_status_exists(
        self,
    ) -> None:
        result = OrchestrationResult(
            decision=TransitionDecision(
                computed_stage=Stage.REQUIREMENTS,
                final_stage=Stage.REQUIREMENTS,
                should_stay=True,
                reason="Stay on current stage.",
            ),
            diagnostic={
                "decision_type": "STAY",
                "state_changes": ["spec"],
                "question_state": {"status": "idle"},
                "transition": {"reason": "Stay on current stage.", "evidence": []},
                "stages": {
                    "computed": "REQUIREMENTS",
                    "source": "REQUIREMENTS",
                    "final": "REQUIREMENTS",
                    "executed": "REQUIREMENTS",
                },
                "llm_trace": {
                    "status": "fatal_error",
                    "failure_type": "auth_error",
                    "enabled": True,
                    "used": False,
                    "fallback_used": False,
                },
            },
            summary="ok",
        )
        report = format_diagnostic_report(result)
        self.assertIn("status: fatal_error", report)
        self.assertIn("outcome: blocked", report)

    def test_format_diagnostic_report_surfaces_command_override_trace(self) -> None:
        result = OrchestrationResult(
            decision=TransitionDecision(
                computed_stage=Stage.TESTING,
                final_stage=Stage.TESTING,
                should_stay=True,
                reason="Stay on current stage.",
            ),
            diagnostic={
                "decision_type": "STAY",
                "state_changes": ["test_report"],
                "question_state": {"status": "idle"},
                "transition": {"reason": "Stay on current stage.", "evidence": []},
                "stages": {
                    "computed": "TESTING",
                    "source": "TESTING",
                    "final": "TESTING",
                    "executed": "TESTING",
                },
                "execution_trace": {
                    "workspace_path": "/tmp/generated/x",
                    "suggested_command": ["pytest", "-q"],
                    "executed_command": [
                        "python3",
                        "-m",
                        "unittest",
                        "discover",
                        "-s",
                        "tests",
                        "-p",
                        "test_*.py",
                        "-v",
                    ],
                    "command_results": [],
                },
            },
            summary="ok",
        )
        report = format_diagnostic_report(result)
        self.assertIn("suggested command: pytest -q", report)
        self.assertIn(
            "executed command: python3 -m unittest discover -s tests -p test_*.py -v",
            report,
        )

    @patch("main.print")
    @patch("main.Orchestrator")
    @patch("main.StateManager")
    def test_main_accepts_state_dir_argument(
        self,
        mock_state_manager: MagicMock,
        mock_orchestrator_cls: MagicMock,
        _mock_print: MagicMock,
    ) -> None:
        mock_orchestrator = MagicMock()
        mock_orchestrator.orchestrate.return_value = OrchestrationResult(
            decision=TransitionDecision(
                computed_stage=Stage.INIT,
                final_stage=Stage.INIT,
                should_stay=True,
                reason="Stay on current stage.",
            ),
            summary="ok",
        )
        mock_orchestrator_cls.return_value = mock_orchestrator

        with patch(
            "sys.argv",
            ["main.py", "--state-dir", "/tmp/forgeflow-demo", "build", "todo"],
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        mock_state_manager.assert_called_once_with(state_dir="/tmp/forgeflow-demo")
        mock_orchestrator_cls.assert_called_once()
        self.assertEqual(
            mock_orchestrator_cls.call_args.kwargs["state_manager"],
            mock_state_manager.return_value,
        )

    @patch("main.print")
    @patch("main.Orchestrator")
    def test_main_auto_run_stops_when_done(
        self,
        mock_orchestrator_cls: MagicMock,
        _mock_print: MagicMock,
    ) -> None:
        mock_orchestrator = MagicMock()
        mock_orchestrator.orchestrate.side_effect = [
            OrchestrationResult(
                decision=TransitionDecision(
                    computed_stage=Stage.INIT,
                    final_stage=Stage.REQUIREMENTS,
                    should_stay=False,
                    next_stage_to_execute=Stage.REQUIREMENTS,
                    reason="Forward transition available.",
                ),
                executed_stage=Stage.REQUIREMENTS,
                summary="step1",
            ),
            OrchestrationResult(
                decision=TransitionDecision(
                    computed_stage=Stage.DONE,
                    final_stage=Stage.DONE,
                    should_stay=True,
                    reason="Stay on current stage.",
                ),
                summary="done",
            ),
        ]
        mock_orchestrator_cls.return_value = mock_orchestrator

        with patch(
            "sys.argv", ["main.py", "--auto-run", "--max-steps", "5", "build", "todo"]
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(mock_orchestrator.orchestrate.call_count, 2)
        first_call = mock_orchestrator.orchestrate.call_args_list[0]
        second_call = mock_orchestrator.orchestrate.call_args_list[1]
        self.assertEqual(first_call.args[0], "build todo")
        self.assertEqual(second_call.args[0], "")
        self.assertEqual(first_call.kwargs.get("original_request"), "build todo")
        self.assertEqual(second_call.kwargs.get("original_request"), "build todo")

    @patch("main.print")
    @patch("main.Orchestrator")
    def test_main_auto_run_stops_on_no_progress_and_records_summary_metadata(
        self,
        mock_orchestrator_cls: MagicMock,
        mock_print: MagicMock,
    ) -> None:
        mock_orchestrator = MagicMock()
        stay_result = OrchestrationResult(
            decision=TransitionDecision(
                computed_stage=Stage.IMPLEMENTATION,
                final_stage=Stage.IMPLEMENTATION,
                should_stay=True,
                reason="Stay on current stage.",
            ),
            diagnostic={
                "decision_type": "STAY",
                "state_changes": [],
                "question_state": {"status": "idle"},
                "transition": {"reason": "Stay on current stage.", "evidence": []},
                "stages": {
                    "computed": "IMPLEMENTATION",
                    "source": "IMPLEMENTATION",
                    "final": "IMPLEMENTATION",
                    "executed": "IMPLEMENTATION",
                },
            },
            summary="stay",
        )
        mock_orchestrator.orchestrate.side_effect = [
            stay_result,
            stay_result,
            stay_result,
        ]
        mock_orchestrator_cls.return_value = mock_orchestrator

        with patch(
            "sys.argv",
            ["main.py", "--auto-run", "--max-steps", "20", "build", "todo"],
        ):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(mock_orchestrator.orchestrate.call_count, 2)
        mock_orchestrator.record_auto_run_stop.assert_called_once_with(
            stop_reason="no_progress",
            repeated_stage=Stage.IMPLEMENTATION,
            repeated_decision="STAY",
            step_index=2,
        )
        printed = "\n".join(
            str(call.args[0]) for call in mock_print.call_args_list if call.args
        )
        self.assertIn("NO_PROGRESS", printed)

    def test_load_replay_snapshot_reads_expected_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir) / "state"
            run_id = "20260101T000000Z-demo"
            summary_dir = Path(temp_dir) / "runs" / run_id
            summary_dir.mkdir(parents=True, exist_ok=True)
            summary_path = summary_dir / "summary.json"
            summary_path.write_text(
                (
                    '{"schema_version":"1","run_id":"20260101T000000Z-demo",'
                    '"original_request":"build todo","generated_project_dir":"/tmp/generated/demo",'
                    '"state_dir":"/tmp/state","latest_summary":"ok","latest_final_stage":"REQUIREMENTS",'
                    '"latest_decision_type":"STAY","steps":[]}\n'
                ),
                encoding="utf-8",
            )
            snapshot = load_replay_snapshot(run_id, str(state_dir))
            self.assertEqual(snapshot.run_id, run_id)

    def test_render_replay_renders_sections_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_id = "20260101T000000Z-demo"
            runs_dir = Path(temp_dir) / "runs" / run_id
            runs_dir.mkdir(parents=True, exist_ok=True)
            (runs_dir / "approvals").mkdir(parents=True, exist_ok=True)
            (runs_dir / "approvals" / "a.json").write_text("{}", encoding="utf-8")
            (runs_dir / "summary.json").write_text(
                (
                    '{"schema_version":"1","run_id":"20260101T000000Z-demo",'
                    '"original_request":"build todo","generated_project_dir":"/tmp/generated/demo",'
                    '"state_dir":"/tmp/state","latest_summary":"ok","latest_final_stage":"DESIGN",'
                    '"latest_decision_type":"FORWARD","steps":[{"timestamp":"2026-05-10T00:00:00Z",'
                    '"input":"x","decision_type":"FORWARD","computed_stage":"SOLUTION","final_stage":"DESIGN",'
                    '"executed_stage":"DESIGN","question_state":{"status":"idle","blocking":false},"execution_trace":{}}]}\n'
                ),
                encoding="utf-8",
            )
            snapshot = load_replay_snapshot(run_id, str(Path(temp_dir) / "state"))
            report = render_replay(snapshot)
        self.assertIn("ForgeFlow Replay", report)
        self.assertIn("Stages:", report)
        self.assertIn("Decisions:", report)
        self.assertIn("Blockers:", report)
        self.assertIn("Artifacts:", report)
        self.assertIn("approval_count: 1", report)

    @patch("main.print")
    @patch("main.Orchestrator")
    def test_main_replay_mode_does_not_create_orchestrator(
        self,
        mock_orchestrator_cls: MagicMock,
        mock_print: MagicMock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_id = "20260101T000000Z-demo"
            runs_dir = Path(temp_dir) / "runs" / run_id
            runs_dir.mkdir(parents=True, exist_ok=True)
            (runs_dir / "summary.json").write_text(
                (
                    '{"schema_version":"1","run_id":"20260101T000000Z-demo",'
                    '"original_request":"build todo","generated_project_dir":"/tmp/generated/demo",'
                    '"state_dir":"/tmp/state","latest_summary":"ok","latest_final_stage":"REQUIREMENTS",'
                    '"latest_decision_type":"STAY","steps":[]}\n'
                ),
                encoding="utf-8",
            )
            state_dir = Path(temp_dir) / "state"
            with patch(
                "sys.argv",
                [
                    "main.py",
                    "--state-dir",
                    str(state_dir),
                    "--replay-run",
                    run_id,
                ],
            ):
                exit_code = main()
        self.assertEqual(exit_code, 0)
        mock_orchestrator_cls.assert_not_called()
        mock_print.assert_called()

    @patch("main.print")
    @patch("main.Orchestrator")
    def test_main_replay_mode_missing_run_returns_error(
        self,
        mock_orchestrator_cls: MagicMock,
        mock_print: MagicMock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir) / "state"
            with patch(
                "sys.argv",
                [
                    "main.py",
                    "--state-dir",
                    str(state_dir),
                    "--replay-run",
                    "missing-run",
                ],
            ):
                exit_code = main()
        self.assertEqual(exit_code, 1)
        mock_orchestrator_cls.assert_not_called()
        printed = [
            call.args[0]
            for call in mock_print.call_args_list
            if call.args and call.kwargs.get("file") is sys.stderr
        ]
        self.assertTrue(any("Replay error:" in str(item) for item in printed))

    @patch("main.print")
    @patch("main.Orchestrator")
    def test_main_replay_mode_invalid_json_returns_error(
        self,
        mock_orchestrator_cls: MagicMock,
        mock_print: MagicMock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_id = "bad-json-run"
            runs_dir = Path(temp_dir) / "runs" / run_id
            runs_dir.mkdir(parents=True, exist_ok=True)
            (runs_dir / "summary.json").write_text("{bad json", encoding="utf-8")
            state_dir = Path(temp_dir) / "state"
            with patch(
                "sys.argv",
                [
                    "main.py",
                    "--state-dir",
                    str(state_dir),
                    "--replay-run",
                    run_id,
                ],
            ):
                exit_code = main()
        self.assertEqual(exit_code, 1)
        mock_orchestrator_cls.assert_not_called()
        printed = [
            call.args[0]
            for call in mock_print.call_args_list
            if call.args and call.kwargs.get("file") is sys.stderr
        ]
        self.assertTrue(any("Replay error:" in str(item) for item in printed))

    @patch("main.print")
    @patch("main.Orchestrator")
    def test_main_replay_mode_schema_invalid_returns_error(
        self,
        mock_orchestrator_cls: MagicMock,
        mock_print: MagicMock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_id = "invalid-schema-run"
            runs_dir = Path(temp_dir) / "runs" / run_id
            runs_dir.mkdir(parents=True, exist_ok=True)
            (runs_dir / "summary.json").write_text(
                '{"run_id":"invalid-schema-run","steps":[]}\n',
                encoding="utf-8",
            )
            state_dir = Path(temp_dir) / "state"
            with patch(
                "sys.argv",
                [
                    "main.py",
                    "--state-dir",
                    str(state_dir),
                    "--replay-run",
                    run_id,
                ],
            ):
                exit_code = main()
        self.assertEqual(exit_code, 0)
        mock_orchestrator_cls.assert_not_called()
        self.assertTrue(mock_print.called)


if __name__ == "__main__":
    unittest.main()
