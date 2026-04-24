from __future__ import annotations

import unittest

from agents.base import AgentContext, QuestionAnswer, QuestionItem, QuestionState
from agents.requirements_engineer import RequirementsEngineerAgent
from tests.unit.support.orchestrator_fixtures import make_empty_states


class RequirementsEngineerHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = RequirementsEngineerAgent()

    def test_normalize_text_and_dedupe_items_strip_noise_and_merge_case(self) -> None:
        self.assertEqual(
            self.agent.normalize_text("  - Build workflow orchestration...  "),
            "Build workflow orchestration",
        )
        self.assertEqual(
            self.agent.dedupe_items(
                [
                    "collect requirements",
                    " Collect requirements ",
                    "",
                    "track progress",
                ]
            ),
            ["Collect requirements", "Track progress"],
        )

    def test_extract_goal_from_input_strips_leading_request_phrases(self) -> None:
        self.assertEqual(
            self.agent.extract_goal_from_input(
                "Please help me build a chat-first workflow assistant."
            ),
            "A chat-first workflow assistant",
        )
        self.assertEqual(
            self.agent.extract_goal_from_input("we need to create a release dashboard"),
            "Create a release dashboard",
        )
        self.assertEqual(self.agent.extract_goal_from_input(""), "")

    def test_extract_requirements_from_input_prefers_bullets_and_then_clauses(self) -> None:
        self.assertEqual(
            self.agent.extract_requirements_from_input(
                "- collect requirements\n- generate solution outline\n- track progress"
            ),
            [
                "Collect requirements",
                "Generate solution outline",
                "Track progress",
            ],
        )
        self.assertEqual(
            self.agent.extract_requirements_from_input(
                "Build a workflow assistant and generate solution artifacts then track implementation progress."
            ),
            [
                "A workflow assistant",
                "Generate solution artifacts",
                "Track implementation progress",
            ],
        )

    def test_extract_requirements_from_input_returns_empty_for_too_thin_input(self) -> None:
        self.assertEqual(self.agent.extract_requirements_from_input("ship"), [])
        self.assertEqual(self.agent.extract_requirements_from_input(""), [])

    def test_derive_acceptance_criteria_uses_top_three_requirements_or_goal_fallback(
        self,
    ) -> None:
        self.assertEqual(
            self.agent.derive_acceptance_criteria(
                "A workflow assistant",
                [
                    "Collect requirements",
                    "Generate solution outline",
                    "Track implementation progress",
                    "Validate delivery",
                ],
            ),
            [
                "The system can collect requirements",
                "The system can generate solution outline",
                "The system can track implementation progress",
            ],
        )
        self.assertEqual(
            self.agent.derive_acceptance_criteria("A workflow assistant", []),
            [
                "The delivered workflow satisfies the core goal: a workflow assistant"
            ],
        )

    def test_extract_answers_only_consumes_answered_requirements_question_state(
        self,
    ) -> None:
        answered_context = AgentContext(
            states=make_empty_states(),
            question_state=QuestionState(
                status="answered",
                stage_name="REQUIREMENTS",
                state_key="spec",
                blocking=True,
                questions=[
                    QuestionItem(
                        id="project_goal",
                        title="Goal",
                        description="Primary goal.",
                        answer=QuestionAnswer(
                            selected_values=[],
                            free_text="A workflow assistant for solo builders",
                        ),
                    ),
                    QuestionItem(
                        id="functional_requirements",
                        title="Requirements",
                        description="Core capabilities.",
                        answer=QuestionAnswer(
                            selected_values=["Collect requirements", "Track progress"],
                            free_text="",
                        ),
                    ),
                ],
            ),
        )
        self.assertEqual(
            self.agent.extract_answers(answered_context),
            {
                "project_goal": "A workflow assistant for solo builders",
                "functional_requirements": "Collect requirements, Track progress",
            },
        )

        wrong_state_context = AgentContext(
            states=make_empty_states(),
            question_state=QuestionState(
                status="answered",
                stage_name="SOLUTION",
                state_key="solution",
                blocking=True,
                questions=[],
            ),
        )
        self.assertEqual(self.agent.extract_answers(wrong_state_context), {})

    def test_build_clarifying_questions_returns_blocking_spec_prompt(self) -> None:
        question_state = self.agent.build_clarifying_questions(make_empty_states()["spec"])

        self.assertEqual(question_state.status, "awaiting_user")
        self.assertEqual(question_state.stage_name, "REQUIREMENTS")
        self.assertTrue(question_state.blocking)
        self.assertEqual(
            [question.id for question in question_state.questions],
            ["project_goal", "functional_requirements", "acceptance_criteria"],
        )


if __name__ == "__main__":
    unittest.main()
