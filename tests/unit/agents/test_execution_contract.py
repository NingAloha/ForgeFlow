from __future__ import annotations

import unittest

from agents.base import AgentContext
from agents.implementation_engineer import ImplementationEngineerAgent
from agents.implementation_engineer.execution_contract import (
    parse_execution_contract,
    parse_patch_draft,
    validate_execution_contract,
)
from tests.unit.support.orchestrator_fixtures import make_design_ready_states


class ExecutionContractParserTests(unittest.TestCase):
    def _valid_notes(self) -> str:
        return "\n".join(
            [
                "BEGIN_EXECUTION_CONTRACT",
                "execution_contract_version=v1",
                "execution_intent=review_only",
                "mutation_performed=false",
                "target_module=markdown_parser",
                "plan_type=patch_preview+patch_draft",
                "create=[src/markdown_parser/README.md, tests/markdown_parser/README.md]",
                "modify=[]",
                "delete=[]",
                "rationale=prepare reviewable implementation intent from design without mutation",
                "risk=contract drift or module-boundary mismatch before real execution",
                "test_plan=[pytest tests/markdown_parser]",
                "rollback_expectation=pre_patch_snapshot+patch_id+rollback_available",
                "END_EXECUTION_CONTRACT",
                "BEGIN_PATCH_DRAFT",
                "diff --git a/src/markdown_parser/README.md b/src/markdown_parser/README.md",
                "new file mode 100644",
                "--- /dev/null",
                "+++ b/src/markdown_parser/README.md",
                "@@",
                "+# markdown_parser",
                "diff --git a/tests/markdown_parser/README.md b/tests/markdown_parser/README.md",
                "new file mode 100644",
                "--- /dev/null",
                "+++ b/tests/markdown_parser/README.md",
                "@@",
                "+# markdown_parser test plan",
                "END_PATCH_DRAFT",
            ]
        )

    def test_parse_contract_and_patch_draft_from_valid_notes(self) -> None:
        notes = self._valid_notes()
        contract = parse_execution_contract(notes)
        draft = parse_patch_draft(notes)

        self.assertEqual(contract["execution_contract_version"], "v1")
        self.assertEqual(contract["target_module"], "markdown_parser")
        self.assertEqual(
            contract["create"],
            ["src/markdown_parser/README.md", "tests/markdown_parser/README.md"],
        )
        self.assertIn("diff --git", draft)
        self.assertIn("new file mode 100644", draft)

    def test_missing_contract_boundary_returns_issue(self) -> None:
        notes = self._valid_notes().replace("BEGIN_EXECUTION_CONTRACT\n", "").replace(
            "\nEND_EXECUTION_CONTRACT", ""
        )
        issues = validate_execution_contract(parse_execution_contract(notes), parse_patch_draft(notes))
        self.assertIn("missing execution contract boundary", issues)

    def test_missing_required_key_returns_issue(self) -> None:
        notes = self._valid_notes().replace("execution_intent=review_only\n", "")
        issues = validate_execution_contract(parse_execution_contract(notes), parse_patch_draft(notes))
        self.assertIn("missing required contract key: execution_intent", issues)

    def test_mutation_true_returns_issue(self) -> None:
        notes = self._valid_notes().replace("mutation_performed=false", "mutation_performed=true")
        issues = validate_execution_contract(parse_execution_contract(notes), parse_patch_draft(notes))
        self.assertIn("mutation must be disabled for review-only contract", issues)

    def test_modify_delete_non_empty_returns_issue(self) -> None:
        notes = self._valid_notes().replace("modify=[]", "modify=[src/markdown_parser/README.md]").replace(
            "delete=[]", "delete=[tests/markdown_parser/README.md]"
        )
        issues = validate_execution_contract(parse_execution_contract(notes), parse_patch_draft(notes))
        self.assertIn("modify/delete must be empty for current patch draft contract", issues)

    def test_create_path_outside_allowlist_returns_issue(self) -> None:
        notes = self._valid_notes().replace(
            "create=[src/markdown_parser/README.md, tests/markdown_parser/README.md]",
            "create=[src/markdown_parser/README.md, .github/workflows/x.md]",
        )
        issues = validate_execution_contract(parse_execution_contract(notes), parse_patch_draft(notes))
        self.assertTrue(any("create path" in item for item in issues))

    def test_patch_draft_with_python_code_returns_issue(self) -> None:
        notes = self._valid_notes().replace("+# markdown_parser", "+import os\n+class X:\n+    pass\n+def x():\n+    return 1")
        issues = validate_execution_contract(parse_execution_contract(notes), parse_patch_draft(notes))
        self.assertIn("patch draft must not include python code constructs", issues)

    def test_patch_draft_with_delete_or_rename_returns_issue(self) -> None:
        notes = self._valid_notes().replace(
            "END_PATCH_DRAFT",
            "deleted file mode 100644\nrename from a\nrename to b\nEND_PATCH_DRAFT",
        )
        issues = validate_execution_contract(parse_execution_contract(notes), parse_patch_draft(notes))
        self.assertIn("patch draft must not delete files", issues)
        self.assertIn("patch draft must not rename files", issues)

    def test_contract_create_path_missing_in_draft_returns_issue(self) -> None:
        notes = self._valid_notes().replace("+++ b/tests/markdown_parser/README.md", "+++ b/tests/other/README.md")
        issues = validate_execution_contract(parse_execution_contract(notes), parse_patch_draft(notes))
        self.assertIn(
            "patch draft does not cover declared create path: tests/markdown_parser/README.md",
            issues,
        )

    def test_phase16_execute_notes_pass_validation(self) -> None:
        states = make_design_ready_states()
        states["system_design"] = {
            "project_structure": {
                "directories": [
                    "src/markdown_parser/",
                    "tests/markdown_parser/",
                ],
                "modules": ["markdown_parser"],
            },
            "contracts": [
                {
                    "name": "solution_to_markdown_parser_implementation",
                    "input": [{"name": "markdown input", "required": True}],
                    "output": [{"name": "parsed sections", "required": True}],
                    "constraints": [],
                    "acceptance_criteria": [],
                    "failure_handling": ["input_errors", "processing_errors", "output_errors"],
                }
            ],
            "data_flow": [
                {
                    "step": 1,
                    "contract_name": "solution_to_markdown_parser_implementation",
                    "from": "Design",
                    "to": ["Implementation"],
                    "trigger": "markdown_parser handoff ready",
                    "notes": "module markdown_parser",
                }
            ],
            "mvp_plan": {
                "in_scope": [],
                "out_of_scope": [],
                "milestones": [],
                "first_deliverable": "",
            },
        }

        agent = ImplementationEngineerAgent()
        result = agent.run(
            AgentContext(user_input="", states=states, metadata={"implementation_mode": "execute"})
        )
        notes_text = "\n".join(result.notes)
        issues = validate_execution_contract(
            parse_execution_contract(notes_text),
            parse_patch_draft(notes_text),
        )
        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
