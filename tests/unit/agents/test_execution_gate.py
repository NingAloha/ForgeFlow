from __future__ import annotations

import copy
import unittest

from agents.implementation_engineer.execution_approval import build_pending_approval
from agents.implementation_engineer.execution_gate import can_execute_contract


class ExecutionGateTests(unittest.TestCase):
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
            "rationale": "review only",
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

    def test_invalid_contract_blocks_with_contract_issues(self) -> None:
        bad_contract = dict(self.contract)
        bad_contract["mutation_performed"] = "true"
        result = can_execute_contract(bad_contract, self.patch_draft, approval={})
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reason"], "execution contract is invalid")
        self.assertTrue(result["issues"])

    def test_missing_approval_blocks(self) -> None:
        result = can_execute_contract(self.contract, self.patch_draft, approval={})
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reason"], "approval is missing")

    def test_invalid_approval_blocks(self) -> None:
        pending = build_pending_approval(self.contract, self.patch_draft)
        pending["approval_status"] = "unknown"
        result = can_execute_contract(self.contract, self.patch_draft, approval=pending)
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reason"], "approval is invalid")
        self.assertTrue(result["issues"])

    def test_approval_not_approved_blocks(self) -> None:
        pending = build_pending_approval(self.contract, self.patch_draft)
        result = can_execute_contract(self.contract, self.patch_draft, approval=pending)
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reason"], "approval status is not approved")

    def test_stale_approval_blocks(self) -> None:
        approved = build_pending_approval(self.contract, self.patch_draft)
        approved["approval_status"] = "approved"
        approved["review_decision"] = "approved"
        approved["stale"] = True
        result = can_execute_contract(
            self.contract, self.patch_draft, approval=approved
        )
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reason"], "approval is stale")
        self.assertEqual(result["issues"], [])

    def test_hash_mismatch_without_stale_flag_returns_approval_invalid(self) -> None:
        approved = build_pending_approval(self.contract, self.patch_draft)
        approved["approval_status"] = "approved"
        approved["review_decision"] = "approved"
        approved["approved_by"] = "user"
        approved["approved_at"] = "2026-01-01T00:00:00+00:00"
        approved["contract_hash"] = "0" * 64
        approved["stale"] = False

        result = can_execute_contract(
            self.contract, self.patch_draft, approval=approved
        )
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reason"], "approval is invalid")
        self.assertIn("approval artifact is stale", result["issues"])

    def test_valid_approved_still_blocked_by_mutation_runtime_disabled(self) -> None:
        approved = build_pending_approval(self.contract, self.patch_draft)
        approved["approval_status"] = "approved"
        approved["review_decision"] = "approved"
        approved["approved_by"] = "user"
        approved["approved_at"] = "2026-01-01T00:00:00+00:00"
        result = can_execute_contract(
            self.contract, self.patch_draft, approval=approved
        )
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reason"], "mutation runtime is not enabled")
        self.assertEqual(result["issues"], [])

    def test_gate_has_no_side_effect_fields(self) -> None:
        approved = build_pending_approval(self.contract, self.patch_draft)
        approved["approval_status"] = "approved"
        approved["review_decision"] = "approved"
        result = can_execute_contract(
            self.contract, self.patch_draft, approval=approved
        )
        self.assertNotIn("commands_executed", result)
        self.assertNotIn("artifacts_generated", result)
        self.assertNotIn("file_writes", result)

    def test_gate_does_not_mutate_inputs(self) -> None:
        approved = build_pending_approval(self.contract, self.patch_draft)
        approved["approval_status"] = "approved"
        approved["review_decision"] = "approved"

        contract_before = copy.deepcopy(self.contract)
        draft_before = str(self.patch_draft)
        approval_before = copy.deepcopy(approved)

        _ = can_execute_contract(self.contract, self.patch_draft, approval=approved)

        self.assertEqual(self.contract, contract_before)
        self.assertEqual(self.patch_draft, draft_before)
        self.assertEqual(approved, approval_before)

    def test_reason_priority_contract_invalid_before_approval_missing(self) -> None:
        bad_contract = dict(self.contract)
        bad_contract["mutation_performed"] = "true"
        result = can_execute_contract(bad_contract, self.patch_draft, approval={})
        self.assertEqual(result["reason"], "execution contract is invalid")

    def test_rejected_approval_is_not_allowed(self) -> None:
        rejected = build_pending_approval(self.contract, self.patch_draft)
        rejected["approval_status"] = "rejected"
        rejected["review_decision"] = "rejected"
        rejected["review_reason"] = "manual reject"
        result = can_execute_contract(
            self.contract, self.patch_draft, approval=rejected
        )
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reason"], "approval status is not approved")


if __name__ == "__main__":
    unittest.main()
