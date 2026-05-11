from __future__ import annotations

import copy
import unittest

from agents.implementation_engineer.execution_approval import build_pending_approval
from agents.implementation_engineer.execution_apply_plan import (
    build_dry_run_apply_plan,
    validate_apply_plan,
)


class ExecutionApplyPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = {
            "_contract_boundary_present": True,
            "execution_contract_version": "v1",
            "execution_intent": "review_only",
            "mutation_performed": "false",
            "target_module": "markdown_parser",
            "plan_type": "patch_preview+patch_draft",
            "create": [
                "src/markdown_parser/README.md",
                "tests/markdown_parser/README.md",
            ],
            "modify": [],
            "delete": [],
            "rationale": "review-only apply planning",
            "risk": "contract drift",
            "test_plan": ["pytest tests/markdown_parser"],
            "rollback_expectation": "pre_patch_snapshot+patch_id+rollback_available",
        }
        self.patch_draft = "\n".join(
            [
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
            ]
        )

    def _approved(self) -> dict:
        approval = build_pending_approval(self.contract, self.patch_draft)
        approval["approval_status"] = "approved"
        approval["review_decision"] = "approved"
        approval["approved_by"] = "user"
        approval["approved_at"] = "2026-01-01T00:00:00+00:00"
        approval["stale"] = False
        return approval

    def test_valid_contract_and_approved_approval_yields_blocked_dry_run_plan(self) -> None:
        plan = build_dry_run_apply_plan(self.contract, self.patch_draft, self._approved())
        self.assertEqual(plan["apply_plan_status"], "blocked")
        self.assertFalse(plan["mutation_performed"])

    def test_plan_contains_patch_id(self) -> None:
        plan = build_dry_run_apply_plan(self.contract, self.patch_draft, self._approved())
        self.assertTrue(plan["patch_id"])
        self.assertEqual(len(plan["patch_id"]), 64)

    def test_target_module_comes_from_contract(self) -> None:
        plan = build_dry_run_apply_plan(self.contract, self.patch_draft, self._approved())
        self.assertEqual(plan["target_module"], "markdown_parser")

    def test_files_to_create_comes_from_contract_create(self) -> None:
        plan = build_dry_run_apply_plan(self.contract, self.patch_draft, self._approved())
        self.assertEqual(
            plan["files_to_create"],
            ["src/markdown_parser/README.md", "tests/markdown_parser/README.md"],
        )

    def test_files_to_modify_and_delete_are_empty(self) -> None:
        plan = build_dry_run_apply_plan(self.contract, self.patch_draft, self._approved())
        self.assertEqual(plan["files_to_modify"], [])
        self.assertEqual(plan["files_to_delete"], [])

    def test_post_apply_test_plan_comes_from_contract(self) -> None:
        plan = build_dry_run_apply_plan(self.contract, self.patch_draft, self._approved())
        self.assertEqual(plan["post_apply_test_plan"], ["pytest tests/markdown_parser"])

    def test_gate_reason_is_mutation_runtime_disabled_for_valid_approval(self) -> None:
        plan = build_dry_run_apply_plan(self.contract, self.patch_draft, self._approved())
        self.assertEqual(plan["gate_result"]["reason"], "mutation runtime is not enabled")

    def test_missing_approval_produces_blocked_plan_with_missing_reason(self) -> None:
        plan = build_dry_run_apply_plan(self.contract, self.patch_draft, approval={})
        self.assertEqual(plan["apply_plan_status"], "blocked")
        self.assertEqual(plan["gate_result"]["reason"], "approval is missing")

    def test_invalid_contract_produces_blocked_plan_with_contract_invalid_reason(self) -> None:
        bad = dict(self.contract)
        bad["mutation_performed"] = "true"
        plan = build_dry_run_apply_plan(bad, self.patch_draft, approval={})
        self.assertEqual(plan["apply_plan_status"], "blocked")
        self.assertEqual(plan["gate_result"]["reason"], "execution contract is invalid")

    def test_plan_builder_has_no_side_effects_and_does_not_mutate_inputs(self) -> None:
        approval = self._approved()
        contract_before = copy.deepcopy(self.contract)
        draft_before = str(self.patch_draft)
        approval_before = copy.deepcopy(approval)

        plan = build_dry_run_apply_plan(self.contract, self.patch_draft, approval)

        self.assertEqual(self.contract, contract_before)
        self.assertEqual(self.patch_draft, draft_before)
        self.assertEqual(approval, approval_before)
        self.assertNotIn("commands_executed", plan)
        self.assertNotIn("artifacts_generated", plan)
        self.assertNotIn("file_writes", plan)

    def test_validate_apply_plan_accepts_current_valid_dry_run_plan(self) -> None:
        approval = self._approved()
        plan = build_dry_run_apply_plan(self.contract, self.patch_draft, approval)
        self.assertEqual(validate_apply_plan(plan, self.contract, self.patch_draft), [])

    def test_validate_apply_plan_reports_missing_required_key(self) -> None:
        plan = build_dry_run_apply_plan(self.contract, self.patch_draft, self._approved())
        plan.pop("patch_id")
        issues = validate_apply_plan(plan, self.contract, self.patch_draft)
        self.assertIn("missing required apply plan key: patch_id", issues)

    def test_validate_apply_plan_reports_patch_id_mismatch(self) -> None:
        plan = build_dry_run_apply_plan(self.contract, self.patch_draft, self._approved())
        plan["patch_id"] = "badhash"
        issues = validate_apply_plan(plan, self.contract, self.patch_draft)
        self.assertIn("patch_id does not match execution contract fingerprint", issues)

    def test_validate_apply_plan_reports_target_module_mismatch(self) -> None:
        plan = build_dry_run_apply_plan(self.contract, self.patch_draft, self._approved())
        plan["target_module"] = "summary_extractor"
        issues = validate_apply_plan(plan, self.contract, self.patch_draft)
        self.assertIn("target_module does not match execution contract", issues)

    def test_validate_apply_plan_reports_files_to_create_mismatch(self) -> None:
        plan = build_dry_run_apply_plan(self.contract, self.patch_draft, self._approved())
        plan["files_to_create"] = ["src/markdown_parser/OTHER.md"]
        issues = validate_apply_plan(plan, self.contract, self.patch_draft)
        self.assertIn(
            "files_to_create does not match execution contract create list",
            issues,
        )

    def test_validate_apply_plan_reports_non_empty_modify_or_delete(self) -> None:
        plan = build_dry_run_apply_plan(self.contract, self.patch_draft, self._approved())
        plan["files_to_modify"] = ["src/markdown_parser/README.md"]
        issues = validate_apply_plan(plan, self.contract, self.patch_draft)
        self.assertIn(
            "files_to_modify/delete must be empty for dry-run apply plan",
            issues,
        )

    def test_validate_apply_plan_reports_gate_result_allowed_true(self) -> None:
        plan = build_dry_run_apply_plan(self.contract, self.patch_draft, self._approved())
        plan["gate_result"] = {"allowed": True, "reason": "mutation runtime is not enabled"}
        issues = validate_apply_plan(plan, self.contract, self.patch_draft)
        self.assertIn(
            "apply plan gate result must remain blocked while mutation runtime is disabled",
            issues,
        )

    def test_validate_apply_plan_reports_mutation_performed_true(self) -> None:
        plan = build_dry_run_apply_plan(self.contract, self.patch_draft, self._approved())
        plan["mutation_performed"] = True
        issues = validate_apply_plan(plan, self.contract, self.patch_draft)
        self.assertIn("apply plan must not perform mutation", issues)

    def test_validate_apply_plan_reports_non_blocked_status(self) -> None:
        plan = build_dry_run_apply_plan(self.contract, self.patch_draft, self._approved())
        plan["apply_plan_status"] = "ready"
        issues = validate_apply_plan(plan, self.contract, self.patch_draft)
        self.assertIn(
            "apply plan status must be blocked before mutation runtime exists",
            issues,
        )

    def test_validate_apply_plan_reports_disallowed_post_apply_command(self) -> None:
        plan = build_dry_run_apply_plan(self.contract, self.patch_draft, self._approved())
        plan["post_apply_test_plan"] = ["pytest tests/markdown_parser", "sudo rm -rf /tmp/x"]
        issues = validate_apply_plan(plan, self.contract, self.patch_draft)
        self.assertIn("post-apply test plan contains disallowed command: rm -rf", issues)

    def test_validate_apply_plan_reports_denied_path(self) -> None:
        plan = build_dry_run_apply_plan(self.contract, self.patch_draft, self._approved())
        plan["files_to_create"] = ["src/markdown_parser/README.md", ".git/config"]
        issues = validate_apply_plan(plan, self.contract, self.patch_draft)
        self.assertIn(
            "files_to_create does not match execution contract create list",
            issues,
        )
        self.assertIn("apply plan path is outside allowed scope: .git/config", issues)

    def test_validate_apply_plan_has_no_side_effects_and_does_not_mutate_inputs(self) -> None:
        approval = self._approved()
        plan = build_dry_run_apply_plan(self.contract, self.patch_draft, approval)
        plan_before = copy.deepcopy(plan)
        contract_before = copy.deepcopy(self.contract)
        draft_before = str(self.patch_draft)

        issues = validate_apply_plan(plan, self.contract, self.patch_draft)

        self.assertEqual(issues, [])
        self.assertEqual(plan, plan_before)
        self.assertEqual(self.contract, contract_before)
        self.assertEqual(self.patch_draft, draft_before)


if __name__ == "__main__":
    unittest.main()
