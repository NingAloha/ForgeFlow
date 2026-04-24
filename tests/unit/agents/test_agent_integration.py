from __future__ import annotations

import unittest

from agents.base import AgentContext, QuestionAnswer, QuestionItem, QuestionState
from agents.requirements_engineer import RequirementsEngineerAgent
from agents.solution_engineer import SolutionEngineerAgent
from tests.unit.support.orchestrator_fixtures import (
    make_empty_states,
    make_requirements_ready_states,
)


class RequirementsEngineerAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = RequirementsEngineerAgent()

    def test_agent_extracts_core_spec_fields_from_user_input(self) -> None:
        context = AgentContext(
            user_input=(
                "Build a chat-first engineering workflow that collects requirements "
                "and generates solution artifacts."
            ),
            states=make_empty_states(),
        )

        result = self.agent.run(context)

        self.assertEqual(
            result.updated_state["project_goal"],
            "A chat-first engineering workflow that collects requirements and generates solution artifacts",
        )
        self.assertTrue(result.updated_state["functional_requirements"])
        self.assertTrue(result.updated_state["acceptance_criteria"])
        self.assertFalse(result.requires_user_input)
        self.assertTrue(result.handoff_ready)

    def test_agent_asks_blocking_questions_when_core_inputs_are_missing(self) -> None:
        context = AgentContext(user_input="", states=make_empty_states())
        result = self.agent.run(context)
        self.assertTrue(result.requires_user_input)
        self.assertIsNotNone(result.question_state_update)
        self.assertEqual(result.question_state_update.status, "awaiting_user")
        self.assertEqual(
            [question.id for question in result.question_state_update.questions],
            ["project_goal", "functional_requirements", "acceptance_criteria"],
        )
        self.assertEqual(
            result.updated_state["open_questions"],
            ["project_goal", "functional_requirements", "acceptance_criteria"],
        )

    def test_agent_consumes_answered_question_state(self) -> None:
        states = make_empty_states()
        context = AgentContext(
            user_input="",
            states=states,
            question_state=QuestionState(
                status="answered",
                stage_name="REQUIREMENTS",
                state_key="spec",
                blocking=True,
                questions=[
                    QuestionItem(
                        id="project_goal",
                        title="What are we building?",
                        description="Describe the primary goal.",
                        response_type="free_text",
                        allow_free_text=True,
                        answer=QuestionAnswer(
                            selected_values=[],
                            free_text="A workflow assistant for solo builders",
                        ),
                    ),
                    QuestionItem(
                        id="functional_requirements",
                        title="What must it do?",
                        description="List core capabilities.",
                        response_type="free_text",
                        allow_free_text=True,
                        answer=QuestionAnswer(
                            selected_values=[],
                            free_text=(
                                "Collect requirements; produce a solution outline; "
                                "track implementation progress"
                            ),
                        ),
                    ),
                    QuestionItem(
                        id="acceptance_criteria",
                        title="How will we know it works?",
                        description="Describe the acceptance signal.",
                        response_type="free_text",
                        allow_free_text=True,
                        answer=QuestionAnswer(
                            selected_values=[],
                            free_text="The user can capture a request and receive a structured spec",
                        ),
                    ),
                ],
                created_by="Requirements Engineer",
            ),
        )

        result = self.agent.run(context)

        self.assertEqual(
            result.updated_state["project_goal"],
            "A workflow assistant for solo builders",
        )
        self.assertIn(
            "Collect requirements",
            result.updated_state["functional_requirements"],
        )
        self.assertEqual(
            result.updated_state["acceptance_criteria"],
            ["The user can capture a request and receive a structured spec"],
        )
        self.assertFalse(result.requires_user_input)
        self.assertIsNone(result.question_state_update)


class SolutionEngineerAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = SolutionEngineerAgent()

    def test_agent_generates_stack_and_module_mapping_from_requirements(self) -> None:
        context = AgentContext(user_input="", states=make_requirements_ready_states())
        result = self.agent.run(context)
        self.assertEqual(result.updated_state["selected_stack"]["backend"], "Python")
        self.assertTrue(result.updated_state["selected_stack"]["frontend"])
        self.assertTrue(result.updated_state["module_mapping"])
        first_module = result.updated_state["module_mapping"][0]
        self.assertTrue(first_module["module"])
        self.assertTrue(first_module["responsibilities"])
        self.assertTrue(first_module["covers_requirements"])
        self.assertFalse(result.requires_user_input)
        self.assertTrue(result.handoff_ready)

    def test_agent_asks_questions_when_requirements_are_not_ready(self) -> None:
        context = AgentContext(user_input="", states=make_empty_states())
        result = self.agent.run(context)
        self.assertTrue(result.requires_user_input)
        self.assertIsNotNone(result.question_state_update)
        self.assertEqual(result.question_state_update.status, "awaiting_user")
        self.assertEqual(
            [question.id for question in result.question_state_update.questions],
            ["backend_preference", "interaction_surface"],
        )
        self.assertEqual(result.blockers, ["requirements_not_ready"])

    def test_agent_consumes_answered_solution_questions(self) -> None:
        states = make_requirements_ready_states()
        context = AgentContext(
            user_input="",
            states=states,
            question_state=QuestionState(
                status="answered",
                stage_name="SOLUTION",
                state_key="solution",
                blocking=True,
                questions=[
                    QuestionItem(
                        id="backend_preference",
                        title="What backend constraint should guide the solution?",
                        description="Need a runtime direction.",
                        response_type="free_text",
                        allow_free_text=True,
                        answer=QuestionAnswer(selected_values=[], free_text="Python"),
                    ),
                    QuestionItem(
                        id="interaction_surface",
                        title="What interaction surface should we prioritize?",
                        description="Need an interface direction.",
                        response_type="free_text",
                        allow_free_text=True,
                        answer=QuestionAnswer(selected_values=[], free_text="TUI first"),
                    ),
                ],
                created_by="Solution Engineer",
            ),
        )

        result = self.agent.run(context)

        self.assertEqual(result.updated_state["selected_stack"]["backend"], "Python")
        self.assertEqual(result.updated_state["selected_stack"]["frontend"], "Textual")
        self.assertTrue(result.updated_state["module_mapping"])
        self.assertFalse(result.requires_user_input)
        self.assertIsNone(result.question_state_update)


if __name__ == "__main__":
    unittest.main()
