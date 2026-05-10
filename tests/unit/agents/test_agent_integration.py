from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agents.base import AgentContext, QuestionAnswer, QuestionItem, QuestionState
from agents.implementation_engineer import ImplementationEngineerAgent
from agents.requirements_engineer import RequirementsEngineerAgent
from agents.solution_engineer import SolutionEngineerAgent
from agents.system_designer import SystemDesignerAgent
from agents.test_validation_engineer import TestValidationEngineerAgent
from tests.unit.support.orchestrator_fixtures import (
    make_design_ready_states,
    make_empty_states,
    make_requirements_ready_states,
    make_solution_ready_states,
    make_testing_states,
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


class SystemDesignerAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = SystemDesignerAgent()

    def test_agent_generates_design_artifacts_from_solution_state(self) -> None:
        context = AgentContext(user_input="", states=make_solution_ready_states())
        result = self.agent.run(context)
        self.assertTrue(result.updated_state["project_structure"]["modules"])
        self.assertTrue(result.updated_state["contracts"])
        self.assertTrue(result.updated_state["data_flow"])
        self.assertTrue(result.updated_state["mvp_plan"]["first_deliverable"])
        self.assertTrue(result.handoff_ready)

    def test_agent_blocks_when_solution_mapping_is_missing(self) -> None:
        states = make_solution_ready_states()
        states["solution"]["module_mapping"] = []
        result = self.agent.run(AgentContext(user_input="", states=states))
        self.assertFalse(result.handoff_ready)
        self.assertEqual(result.blockers, ["solution_module_mapping_missing"])


class ImplementationEngineerAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = ImplementationEngineerAgent()

    def test_agent_generates_execution_artifacts_when_design_is_ready(self) -> None:
        context = AgentContext(user_input="", states=make_design_ready_states())
        result = self.agent.run(context)
        self.assertEqual(result.updated_state["implementation_status"], "done")
        self.assertTrue(result.updated_state["files_touched"])
        self.assertTrue(result.updated_state["tests_added_or_updated"])
        self.assertTrue(result.updated_state["contract_compliance"])
        self.assertTrue(result.handoff_ready)

    def test_agent_marks_blocked_when_design_contracts_are_missing(self) -> None:
        states = make_design_ready_states()
        states["system_design"]["contracts"] = []
        result = self.agent.run(AgentContext(user_input="", states=states))
        self.assertEqual(result.updated_state["implementation_status"], "blocked")
        self.assertFalse(result.handoff_ready)
        self.assertTrue(result.blockers)


class TestValidationEngineerAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = TestValidationEngineerAgent()

    def test_agent_produces_pass_result_for_clean_ready_states(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            tests_dir = workspace / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            (tests_dir / "test_smoke.py").write_text(
                "import unittest\n\n"
                "class SmokeTests(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n\n"
                "if __name__ == '__main__':\n"
                "    unittest.main()\n",
                encoding="utf-8",
            )
            states = make_testing_states()
            states["implementation_status"]["workspace_path"] = str(workspace)
            context = AgentContext(user_input="", states=states)
            result = self.agent.run(context)
            self.assertEqual(result.updated_state["result"], "pass")
            self.assertGreater(result.updated_state["tests_run"], 0)
            self.assertEqual(result.updated_state["issues"], [])
            self.assertTrue(result.handoff_ready)

    def test_agent_produces_fail_result_with_blocking_issues(self) -> None:
        states = make_testing_states()
        states["implementation_status"]["workspace_path"] = "/tmp/forgeflow-missing-workspace"
        result = self.agent.run(AgentContext(user_input="", states=states))
        self.assertEqual(result.updated_state["result"], "fail")
        self.assertEqual(result.updated_state["exit_code"], 1)
        self.assertIn("workspace_missing", result.updated_state["failed_tests"])
        self.assertFalse(result.handoff_ready)


if __name__ == "__main__":
    unittest.main()
