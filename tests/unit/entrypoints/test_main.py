from __future__ import annotations

import unittest

from agents.base import AgentResult
from agents.orchestrator import OrchestrationResult, Stage, TransitionDecision
from main import changed_state_keys, classify_decision, format_diagnostic_report


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


if __name__ == "__main__":
    unittest.main()
