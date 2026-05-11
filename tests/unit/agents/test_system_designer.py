from __future__ import annotations

import unittest

from agents.base import AgentContext
from agents.system_designer import SystemDesignerAgent
from tests.unit.support.orchestrator_fixtures import make_solution_ready_states


class SystemDesignerPlanningQualityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = SystemDesignerAgent()

    def test_design_outputs_module_level_directories_without_file_level_details(
        self,
    ) -> None:
        states = make_solution_ready_states()
        states["solution"]["module_mapping"] = [
            {
                "module": "markdown_parser",
                "responsibilities": ["Parse markdown headings and sections"],
                "covers_requirements": ["Read markdown file and parse sections"],
                "depends_on": [],
                "tech_note": "tech=Python; library=markdown-it-py; reason=stable parsing",
            },
            {
                "module": "summary_extractor",
                "responsibilities": ["Extract title, key points, action items"],
                "covers_requirements": ["Generate title, key points, and action items"],
                "depends_on": ["markdown_parser"],
                "tech_note": "tech=Python; library=regex; reason=deterministic extraction",
            },
        ]

        result = self.agent.run(AgentContext(user_input="", states=states))
        structure = result.updated_state["project_structure"]
        directories = structure["directories"]

        self.assertIn("src/markdown_parser/", directories)
        self.assertIn("src/summary_extractor/", directories)
        self.assertIn("tests/markdown_parser/", directories)
        self.assertIn("tests/summary_extractor/", directories)
        self.assertNotIn("agents/markdown_parser/", directories)
        self.assertFalse(any(item.endswith(".py") for item in directories))

    def test_contracts_include_executable_io_constraints_and_semantic_failure_groups(
        self,
    ) -> None:
        states = make_solution_ready_states()
        states["solution"]["module_mapping"] = [
            {
                "module": "markdown_parser",
                "responsibilities": ["Parse markdown headings and sections"],
                "covers_requirements": ["Read markdown file and parse sections"],
                "depends_on": [],
                "tech_note": "tech=Python; library=markdown-it-py; reason=stable parsing",
            }
        ]

        result = self.agent.run(AgentContext(user_input="", states=states))
        contract = result.updated_state["contracts"][0]

        self.assertGreaterEqual(len(contract["input"]), 2)
        self.assertGreaterEqual(len(contract["output"]), 2)
        self.assertTrue(contract["constraints"])

        failure = "\n".join(contract["failure_handling"])
        self.assertIn("input_errors", failure)
        self.assertIn("processing_errors", failure)
        self.assertIn("output_errors", failure)
        self.assertIn("user_fixable", failure)
        self.assertIn("retryable", failure)

    def test_data_flow_triggers_follow_cli_processing_semantics(self) -> None:
        states = make_solution_ready_states()
        states["solution"]["module_mapping"] = [
            {
                "module": "markdown_parser",
                "responsibilities": ["Parse markdown headings and sections"],
                "covers_requirements": ["Read markdown file and parse sections"],
                "depends_on": [],
                "tech_note": "tech=Python; library=markdown-it-py; reason=stable parsing",
            },
            {
                "module": "summary_extractor",
                "responsibilities": ["Extract title, key points, action items"],
                "covers_requirements": ["Generate title, key points, and action items"],
                "depends_on": ["markdown_parser"],
                "tech_note": "tech=Python; library=regex; reason=deterministic extraction",
            },
        ]

        result = self.agent.run(AgentContext(user_input="", states=states))
        triggers = [item["trigger"] for item in result.updated_state["data_flow"]]

        self.assertTrue(
            any("markdown input" in trigger.lower() for trigger in triggers)
        )
        self.assertTrue(
            any(
                "key-point" in trigger.lower() or "action-item" in trigger.lower()
                for trigger in triggers
            )
        )

    def test_mvp_plan_is_directly_actionable_for_implementation(self) -> None:
        states = make_solution_ready_states()
        states["solution"]["module_mapping"] = [
            {
                "module": "markdown_parser",
                "responsibilities": ["Parse markdown headings and sections"],
                "covers_requirements": ["Read markdown file and parse sections"],
                "depends_on": [],
                "tech_note": "tech=Python; library=markdown-it-py; reason=stable parsing",
            }
        ]

        result = self.agent.run(AgentContext(user_input="", states=states))
        plan = result.updated_state["mvp_plan"]

        self.assertIn("markdown_parser", plan["first_deliverable"])
        self.assertTrue(any("unittest discover" in item for item in plan["milestones"]))
        self.assertTrue(any("No Web UI" in item for item in plan["out_of_scope"]))


if __name__ == "__main__":
    unittest.main()
