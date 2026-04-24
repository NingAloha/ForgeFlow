from __future__ import annotations

import unittest

from agents.base import AgentContext, QuestionAnswer, QuestionItem, QuestionState
from agents.solution_engineer import SolutionEngineerAgent
from tests.unit.support.orchestrator_fixtures import (
    make_empty_states,
    make_requirements_ready_states,
)


class SolutionEngineerHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = SolutionEngineerAgent()

    def test_normalize_text_and_dedupe_items_strip_noise_and_merge_case(self) -> None:
        self.assertEqual(
            self.agent.normalize_text("  - Build workflow plans...  "),
            "Build workflow plans",
        )
        self.assertEqual(
            self.agent.dedupe_items(
                [
                    " collect requirements ",
                    "Collect requirements",
                    "",
                    "track progress",
                ]
            ),
            ["Collect requirements", "Track progress"],
        )

    def test_slugify_and_infer_module_name_map_common_requirement_shapes(self) -> None:
        self.assertEqual(
            self.agent.slugify_requirement("Track implementation progress!"),
            "track_implementation_progress",
        )
        self.assertEqual(
            self.agent.infer_module_name("Generate solution design"),
            "planning_engine",
        )
        self.assertEqual(
            self.agent.infer_module_name("Collect user input from chat"),
            "interaction_layer",
        )
        self.assertEqual(
            self.agent.infer_module_name(""),
            "workflow_core",
        )

    def test_extract_answers_only_consumes_answered_solution_question_state(self) -> None:
        answered_context = AgentContext(
            states=make_requirements_ready_states(),
            question_state=QuestionState(
                status="answered",
                stage_name="SOLUTION",
                state_key="solution",
                blocking=True,
                questions=[
                    QuestionItem(
                        id="backend_preference",
                        title="Backend",
                        description="Pick a backend.",
                        answer=QuestionAnswer(
                            selected_values=[],
                            free_text="Python",
                        ),
                    ),
                    QuestionItem(
                        id="interaction_surface",
                        title="Surface",
                        description="Pick a surface.",
                        answer=QuestionAnswer(
                            selected_values=["TUI"],
                            free_text="",
                        ),
                    ),
                ],
            ),
        )
        self.assertEqual(
            self.agent.extract_answers(answered_context),
            {
                "backend_preference": "Python",
                "interaction_surface": "TUI",
            },
        )

        wrong_stage_context = AgentContext(
            states=make_requirements_ready_states(),
            question_state=QuestionState(
                status="answered",
                stage_name="REQUIREMENTS",
                state_key="spec",
                blocking=True,
                questions=[],
            ),
        )
        self.assertEqual(self.agent.extract_answers(wrong_stage_context), {})

    def test_pick_stack_respects_answers_and_infers_local_workflow_defaults(self) -> None:
        spec = make_requirements_ready_states()["spec"]
        spec["preferences"] = ["Local-first workflow"]
        selected_stack = self.agent.pick_stack(
            spec,
            {
                "backend_preference": "Go",
                "interaction_surface": "chat-first TUI",
            },
            current_state={},
        )

        self.assertEqual(selected_stack["backend"], "Go")
        self.assertEqual(selected_stack["frontend"], "Textual")
        self.assertEqual(selected_stack["database"], "JSON files")
        self.assertEqual(selected_stack["agent_framework"], "Custom orchestrator")
        self.assertEqual(selected_stack["deployment"], "Local CLI")

    def test_pick_stack_preserves_existing_choices_when_present(self) -> None:
        spec = make_requirements_ready_states()["spec"]
        current_state = {
            "selected_stack": {
                "frontend": "Web",
                "backend": "Rust",
                "database": "Postgres",
                "agent_framework": "LangGraph",
                "deployment": "Cloud app",
            }
        }

        selected_stack = self.agent.pick_stack(spec, {}, current_state)

        self.assertEqual(
            selected_stack,
            {
                "frontend": "Web",
                "backend": "Rust",
                "database": "Postgres",
                "agent_framework": "LangGraph",
                "deployment": "Cloud app",
            },
        )

    def test_build_module_mapping_groups_related_requirements_and_sets_dependency_chain(
        self,
    ) -> None:
        spec = make_requirements_ready_states()["spec"]
        spec["functional_requirements"] = [
            "Collect requirements",
            "Capture user input",
            "Generate solution outline",
            "Generate design plan",
            "Track implementation progress",
        ]

        module_mapping = self.agent.build_module_mapping(spec)
        module_names = [item["module"] for item in module_mapping]

        self.assertEqual(
            module_names,
            [
                "execution_tracker",
                "interaction_layer",
                "planning_engine",
                "requirements_engine",
            ],
        )
        self.assertEqual(
            module_mapping[0]["covers_requirements"],
            ["Track implementation progress"],
        )
        self.assertIn(
            "Collect requirements",
            module_mapping[3]["covers_requirements"],
        )
        self.assertEqual(module_mapping[1]["depends_on"], ["Execution_tracker"])
        self.assertEqual(module_mapping[2]["depends_on"], ["Execution_tracker"])
        self.assertEqual(module_mapping[3]["depends_on"], ["Execution_tracker"])

    def test_build_risks_and_alternatives_emit_only_relevant_first_pass_items(
        self,
    ) -> None:
        spec = make_requirements_ready_states()["spec"]
        spec["functional_requirements"] = [
            "Collect requirements",
            "Generate solution outline",
            "Generate design plan",
            "Track implementation progress",
        ]
        selected_stack = {
            "frontend": "Textual",
            "backend": "Python",
            "database": "JSON files",
            "agent_framework": "Custom orchestrator",
            "deployment": "Local CLI",
        }

        risks = self.agent.build_risks(spec, selected_stack)
        alternatives = self.agent.build_alternatives(selected_stack)

        self.assertEqual(
            risks,
            [
                "Requirement scope may still be broad for a first deliverable",
                "Terminal UX decisions may affect how quickly the first interaction loop stabilizes",
            ],
        )
        self.assertEqual(
            alternatives,
            [
                "Move to SQLite if local state management becomes too complex for flat files",
                "Use a simpler plain CLI interface if terminal UI complexity slows delivery",
            ],
        )

    def test_build_clarifying_questions_returns_blocking_solution_prompt(self) -> None:
        question_state = self.agent.build_clarifying_questions()

        self.assertEqual(question_state.status, "awaiting_user")
        self.assertEqual(question_state.stage_name, "SOLUTION")
        self.assertTrue(question_state.blocking)
        self.assertEqual(
            [question.id for question in question_state.questions],
            ["backend_preference", "interaction_surface"],
        )


if __name__ == "__main__":
    unittest.main()
