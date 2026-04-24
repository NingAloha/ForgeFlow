from __future__ import annotations

import unittest

from agents.base import AgentContext, AgentResult, QuestionItem, QuestionState
from agents.orchestrator import Stage
from agents.orchestrator.question_flow import QuestionFlow
from tests.unit.support.orchestrator_fixtures import make_empty_states


class QuestionFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.flow = QuestionFlow()

    def test_default_question_state_payload_is_idle_shape(self) -> None:
        self.assertEqual(
            self.flow.default_question_state_payload(),
            make_empty_states()["question_state"],
        )

    def test_should_clear_question_state_only_after_same_stage_answer_consumption(
        self,
    ) -> None:
        context = AgentContext(
            states=make_empty_states(),
            question_state=QuestionState(
                status="answered",
                stage_name="REQUIREMENTS",
                state_key="spec",
                blocking=True,
                questions=[
                    QuestionItem(
                        id="goal",
                        title="Goal",
                        description="Need the primary project goal.",
                    )
                ],
            ),
        )
        result = AgentResult(
            agent_name="Requirements Engineer",
            stage_name="REQUIREMENTS",
            state_key="spec",
            updated_state=make_empty_states()["spec"],
            summary="Consumed answer.",
        )

        self.assertTrue(self.flow.should_clear_question_state(context, result))

    def test_should_not_clear_question_state_when_reasking_or_stage_mismatches(
        self,
    ) -> None:
        context = AgentContext(
            states=make_empty_states(),
            question_state=QuestionState(
                status="answered",
                stage_name="SOLUTION",
                state_key="solution",
                blocking=True,
                questions=[
                    QuestionItem(
                        id="stack",
                        title="Stack",
                        description="Need a backend choice.",
                    )
                ],
            ),
        )
        result = AgentResult(
            agent_name="Requirements Engineer",
            stage_name="REQUIREMENTS",
            state_key="spec",
            updated_state=make_empty_states()["spec"],
            summary="Asked again.",
            requires_user_input=True,
            question_state_update=QuestionState(
                status="awaiting_user",
                stage_name="REQUIREMENTS",
                state_key="spec",
                blocking=True,
                questions=[
                    QuestionItem(
                        id="goal",
                        title="Goal",
                        description="Need the primary project goal.",
                    )
                ],
            ),
        )

        self.assertFalse(self.flow.should_clear_question_state(context, result))

    def test_get_blocking_question_stage_uses_valid_stage_and_falls_back_otherwise(
        self,
    ) -> None:
        valid_states = make_empty_states()
        valid_states["question_state"]["stage_name"] = "TESTING"
        self.assertEqual(
            self.flow.get_blocking_question_stage(valid_states, Stage.REQUIREMENTS),
            Stage.TESTING,
        )

        invalid_states = make_empty_states()
        invalid_states["question_state"]["stage_name"] = "BROKEN"
        self.assertEqual(
            self.flow.get_blocking_question_stage(invalid_states, Stage.SOLUTION),
            Stage.SOLUTION,
        )

    def test_is_waiting_for_user_input_requires_blocking_awaiting_and_questions(
        self,
    ) -> None:
        states = make_empty_states()
        states["question_state"] = {
            "status": "awaiting_user",
            "stage_name": "REQUIREMENTS",
            "state_key": "spec",
            "blocking": True,
            "questions": [{"id": "goal"}],
            "created_by": "Requirements Engineer",
            "resolution_summary": "",
        }
        self.assertTrue(self.flow.is_waiting_for_user_input(states))

        states["question_state"]["status"] = "answered"
        self.assertFalse(self.flow.is_waiting_for_user_input(states))

        states["question_state"]["status"] = "awaiting_user"
        states["question_state"]["questions"] = []
        self.assertFalse(self.flow.is_waiting_for_user_input(states))


if __name__ == "__main__":
    unittest.main()
