from __future__ import annotations

import unittest

from agents.base import AgentContext
from agents.implementation_engineer import ImplementationEngineerAgent
from tests.unit.support.orchestrator_fixtures import make_design_ready_states


class ImplementationEngineerHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = ImplementationEngineerAgent()

    def _make_markdown_design_states(self) -> dict[str, dict]:
        states = make_design_ready_states()
        states["system_design"] = {
            "project_structure": {
                "directories": [
                    "src/markdown_parser/",
                    "src/summary_extractor/",
                    "src/cli_interface/",
                    "tests/markdown_parser/",
                    "tests/summary_extractor/",
                    "tests/cli_interface/",
                ],
                "modules": [
                    "markdown_parser",
                    "summary_extractor",
                    "cli_interface",
                ],
            },
            "contracts": [
                {
                    "name": "solution_to_markdown_parser_implementation",
                    "input": [{"name": "markdown input", "required": True}],
                    "output": [{"name": "parsed sections", "required": True}],
                    "constraints": [],
                    "acceptance_criteria": [],
                    "failure_handling": [
                        "input_errors",
                        "processing_errors",
                        "output_errors",
                    ],
                },
                {
                    "name": "solution_to_summary_extractor_implementation",
                    "input": [{"name": "parsed sections", "required": True}],
                    "output": [{"name": "summary items", "required": True}],
                    "constraints": [],
                    "acceptance_criteria": [],
                    "failure_handling": [
                        "input_errors",
                        "processing_errors",
                        "output_errors",
                    ],
                },
                {
                    "name": "solution_to_cli_interface_implementation",
                    "input": [{"name": "summary items", "required": True}],
                    "output": [{"name": "cli output", "required": True}],
                    "constraints": [],
                    "acceptance_criteria": [],
                    "failure_handling": [
                        "input_errors",
                        "processing_errors",
                        "output_errors",
                    ],
                },
            ],
            "data_flow": [
                {
                    "step": 1,
                    "contract_name": "solution_to_markdown_parser_implementation",
                    "from": "Design",
                    "to": ["Implementation"],
                    "trigger": "markdown_parser handoff ready",
                    "notes": "module markdown_parser",
                },
                {
                    "step": 2,
                    "contract_name": "solution_to_summary_extractor_implementation",
                    "from": "Design",
                    "to": ["Implementation"],
                    "trigger": "summary_extractor handoff ready",
                    "notes": "module summary_extractor",
                },
                {
                    "step": 3,
                    "contract_name": "solution_to_cli_interface_implementation",
                    "from": "Design",
                    "to": ["Implementation"],
                    "trigger": "cli_interface handoff ready",
                    "notes": "module cli_interface",
                },
            ],
            "mvp_plan": {
                "in_scope": [],
                "out_of_scope": [],
                "milestones": [],
                "first_deliverable": "",
            },
        }
        return states

    def test_output_modules_come_from_design_modules_and_no_generic_modules(
        self,
    ) -> None:
        states = self._make_markdown_design_states()
        result = self.agent.run(AgentContext(user_input="", states=states))
        status = result.updated_state

        self.assertEqual(status["module_name"], "markdown_parser")
        joined = "\n".join(
            status["files_touched"] + status["tests_added_or_updated"] + result.notes
        )

        self.assertIn("module=markdown_parser", joined)
        self.assertIn("module=summary_extractor", joined)
        self.assertIn("module=cli_interface", joined)
        self.assertNotIn("module=core", joined)
        self.assertNotIn("module=utils", joined)
        self.assertNotIn("module=app", joined)
        self.assertIn("implementation_mode=handoff", result.notes)

    def test_each_module_links_to_contract_and_has_tests_and_done_criteria(
        self,
    ) -> None:
        states = self._make_markdown_design_states()
        result = self.agent.run(AgentContext(user_input="", states=states))

        notes_text = "\n".join(result.notes)
        tests_text = "\n".join(result.updated_state["tests_added_or_updated"])

        for module in ["markdown_parser", "summary_extractor", "cli_interface"]:
            self.assertIn(f"module={module}; steps=[", notes_text)
            self.assertIn("done=[", notes_text)
            self.assertIn(f"module={module}; suggested_tests=[", tests_text)

    def test_output_must_not_include_file_names_or_function_or_class_names(
        self,
    ) -> None:
        states = self._make_markdown_design_states()
        result = self.agent.run(AgentContext(user_input="", states=states))

        payload_text = "\n".join(
            result.updated_state["files_touched"]
            + result.updated_state["tests_added_or_updated"]
            + result.notes
        )

        self.assertNotIn(".py", payload_text)
        self.assertNotIn("class ", payload_text)
        self.assertNotIn("def ", payload_text)

    def test_missing_contract_generates_module_level_blocker(self) -> None:
        states = self._make_markdown_design_states()
        states["system_design"]["contracts"] = [
            states["system_design"]["contracts"][0],
            states["system_design"]["contracts"][1],
        ]

        result = self.agent.run(AgentContext(user_input="", states=states))

        self.assertIn(
            "missing design contract for cli_interface",
            result.updated_state["blockers"],
        )
        self.assertEqual(result.updated_state["implementation_status"], "blocked")

    def test_missing_data_flow_generates_module_level_blocker(self) -> None:
        states = self._make_markdown_design_states()
        states["system_design"]["data_flow"] = [states["system_design"]["data_flow"][0]]

        result = self.agent.run(AgentContext(user_input="", states=states))

        self.assertIn(
            "missing data flow step for summary_extractor",
            result.updated_state["blockers"],
        )
        self.assertIn(
            "missing data flow step for cli_interface", result.updated_state["blockers"]
        )

    def test_contract_compliance_means_handoff_alignment_not_code_implemented(
        self,
    ) -> None:
        states = self._make_markdown_design_states()
        result = self.agent.run(AgentContext(user_input="", states=states))

        self.assertTrue(result.updated_state["contract_compliance"])
        self.assertEqual(result.updated_state["implementation_status"], "done")
        self.assertIn(
            "contract_compliance means handoff package alignment with design contract, not code implementation completeness.",
            result.notes,
        )

    def test_default_mode_is_handoff(self) -> None:
        states = self._make_markdown_design_states()
        result = self.agent.run(AgentContext(user_input="", states=states, metadata={}))

        self.assertEqual(result.updated_state["implementation_status"], "done")
        self.assertIn("implementation_mode=handoff", result.notes)
        self.assertTrue(result.updated_state["files_touched"])
        self.assertTrue(result.updated_state["tests_added_or_updated"])

    def test_execute_mode_returns_structured_blocker_without_execution_side_effects(
        self,
    ) -> None:
        states = self._make_markdown_design_states()
        result = self.agent.run(
            AgentContext(
                user_input="",
                states=states,
                metadata={"implementation_mode": "execute"},
            )
        )

        self.assertEqual(result.updated_state["implementation_status"], "blocked")
        self.assertFalse(result.updated_state["contract_compliance"])
        self.assertIn(
            "code execution mode is not enabled; missing execution safety boundary",
            result.updated_state["blockers"],
        )
        self.assertIn(
            "patch preview generated; no mutation performed",
            result.updated_state["blockers"],
        )
        self.assertIn(
            "single-module patch draft generated; no mutation performed",
            result.updated_state["blockers"],
        )
        known_limitations_text = "\n".join(result.updated_state["known_limitations"])
        self.assertIn("workspace sandbox", known_limitations_text)
        self.assertIn("allowed paths (write)", known_limitations_text)
        self.assertIn("denied paths (write)", known_limitations_text)
        self.assertIn("allowed commands", known_limitations_text)
        self.assertIn("retry limit: max_retries=1", known_limitations_text)
        self.assertIn("patch preview required", known_limitations_text)
        self.assertIn("rollback policy required", known_limitations_text)
        self.assertIn("execution report required", known_limitations_text)
        preview_text = "\n".join(
            result.updated_state["files_touched"]
            + result.updated_state["tests_added_or_updated"]
        )
        payload_text = "\n".join(
            result.updated_state["files_touched"]
            + result.updated_state["tests_added_or_updated"]
            + result.updated_state["known_limitations"]
            + result.notes
        )
        for module in ["markdown_parser", "summary_extractor", "cli_interface"]:
            if module == "markdown_parser":
                self.assertIn(
                    f"module={module}; operation=create_only; files_to_create=[src/{module}/README.md | tests/{module}/README.md]; files_to_modify=[]; files_to_delete=[]",
                    preview_text,
                )
                self.assertIn(
                    f"module={module}; test_plan=[pytest tests/{module}]", preview_text
                )
            else:
                self.assertNotIn(f"module={module}; files_to_create=", preview_text)
                self.assertNotIn(f"module={module}; test_plan=", preview_text)
        self.assertNotIn(".py", preview_text)
        self.assertNotIn("class ", preview_text)
        self.assertNotIn("def ", preview_text)
        self.assertNotIn(".git/", preview_text)
        self.assertNotIn(".env", preview_text)
        self.assertNotIn(".github/", preview_text)
        self.assertNotIn("pyproject.toml", preview_text)
        self.assertNotIn("~/*", preview_text)
        self.assertNotIn("files_to_delete=[src/", payload_text)
        self.assertTrue(result.updated_state["files_touched"])
        self.assertTrue(result.updated_state["tests_added_or_updated"])
        self.assertEqual(result.updated_state["artifacts_generated"], [])
        self.assertEqual(result.updated_state["commands_executed"], [])
        self.assertFalse(result.handoff_ready)

        notes_text = "\n".join(result.notes)
        self.assertIn("BEGIN_EXECUTION_CONTRACT", notes_text)
        self.assertIn("END_EXECUTION_CONTRACT", notes_text)
        self.assertIn("BEGIN_PATCH_DRAFT", notes_text)
        self.assertIn("END_PATCH_DRAFT", notes_text)
        self.assertIn("execution_contract_version=v1", notes_text)
        self.assertIn("execution_intent=review_only", notes_text)
        self.assertIn("mutation_performed=false", notes_text)
        self.assertIn("target_module=markdown_parser", notes_text)
        self.assertIn("plan_type=patch_preview+patch_draft", notes_text)
        self.assertIn(
            "create=[src/markdown_parser/README.md, tests/markdown_parser/README.md]",
            notes_text,
        )
        self.assertIn("modify=[]", notes_text)
        self.assertIn("delete=[]", notes_text)
        self.assertIn("rationale=", notes_text)
        self.assertIn("risk=", notes_text)
        self.assertIn("test_plan=[pytest tests/markdown_parser]", notes_text)
        self.assertIn(
            "rollback_expectation=pre_patch_snapshot+patch_id+rollback_available",
            notes_text,
        )
        self.assertIn(
            "diff --git a/src/markdown_parser/README.md b/src/markdown_parser/README.md",
            notes_text,
        )
        self.assertIn(
            "diff --git a/tests/markdown_parser/README.md b/tests/markdown_parser/README.md",
            notes_text,
        )
        self.assertIn("new file mode 100644", notes_text)
        self.assertNotIn("deleted file mode", notes_text)
        self.assertNotIn("rename from", notes_text)
        self.assertNotIn("rename to", notes_text)
        self.assertNotIn("--- a/", notes_text)
        self.assertNotIn("+++ b/src/summary_extractor/", notes_text)
        self.assertNotIn("+++ b/src/cli_interface/", notes_text)
        self.assertNotIn(".py", notes_text)
        self.assertNotIn("import ", notes_text)
        self.assertNotIn("class ", notes_text)
        self.assertNotIn("def ", notes_text)

    def test_execute_mode_blocks_when_no_design_module_for_patch_draft(self) -> None:
        states = self._make_markdown_design_states()
        states["system_design"]["project_structure"]["modules"] = []

        result = self.agent.run(
            AgentContext(
                user_input="",
                states=states,
                metadata={"implementation_mode": "execute"},
            )
        )

        self.assertEqual(result.updated_state["implementation_status"], "blocked")
        self.assertIn(
            "no design module available for patch draft",
            result.updated_state["blockers"],
        )
        notes_text = "\n".join(result.notes)
        self.assertNotIn("diff --git", notes_text)


if __name__ == "__main__":
    unittest.main()
