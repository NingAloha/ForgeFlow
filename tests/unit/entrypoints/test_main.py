from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from agents.base import AgentResult
from agents.orchestrator import OrchestrationResult, Stage, TransitionDecision
from main import changed_state_keys, classify_decision, format_diagnostic_report, main


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
                "stages": {"computed": "INIT", "source": "", "final": "INIT", "executed": ""},
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
                    "enabled": True,
                    "used": True,
                    "fallback_used": True,
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
        self.assertIn("fallback used: yes", report)
        self.assertIn("error: timeout", report)

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
        self.assertIn("executed command: python3 -m unittest discover -s tests -p test_*.py -v", report)

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

        with patch("sys.argv", ["main.py", "--state-dir", "/tmp/forgeflow-demo", "build", "todo"]):
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

        with patch("sys.argv", ["main.py", "--auto-run", "--max-steps", "5", "build", "todo"]):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(mock_orchestrator.orchestrate.call_count, 2)
        first_call = mock_orchestrator.orchestrate.call_args_list[0]
        second_call = mock_orchestrator.orchestrate.call_args_list[1]
        self.assertEqual(first_call.args[0], "build todo")
        self.assertEqual(second_call.args[0], "")
        self.assertEqual(first_call.kwargs.get("original_request"), "build todo")
        self.assertEqual(second_call.kwargs.get("original_request"), "build todo")


if __name__ == "__main__":
    unittest.main()
