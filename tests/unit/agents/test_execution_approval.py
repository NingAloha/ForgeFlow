from __future__ import annotations

import unittest

from agents.implementation_engineer.execution_approval import (
    approve_execution_contract,
    build_contract_fingerprint,
    build_pending_approval,
    invalidate_execution_approval,
    is_approval_stale,
    reject_execution_contract,
)


class ExecutionApprovalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = {
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
            "rationale": "prepare review-only patch intent",
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
            ]
        )

    def test_fingerprint_is_stable_for_same_contract_and_draft(self) -> None:
        first = build_contract_fingerprint(self.contract, self.patch_draft)
        second = build_contract_fingerprint(dict(self.contract), self.patch_draft)
        self.assertEqual(first, second)

    def test_fingerprint_changes_when_contract_changes(self) -> None:
        base = build_contract_fingerprint(self.contract, self.patch_draft)
        changed = dict(self.contract)
        changed["risk"] = "different risk"
        updated = build_contract_fingerprint(changed, self.patch_draft)
        self.assertNotEqual(base, updated)

    def test_fingerprint_changes_when_patch_draft_changes(self) -> None:
        base = build_contract_fingerprint(self.contract, self.patch_draft)
        updated = build_contract_fingerprint(self.contract, self.patch_draft + "\n+# extra")
        self.assertNotEqual(base, updated)

    def test_build_pending_approval_sets_pending_state(self) -> None:
        approval = build_pending_approval(self.contract, self.patch_draft)
        self.assertEqual(approval["approval_status"], "pending")
        self.assertFalse(approval["stale"])
        self.assertEqual(approval["target_module"], "markdown_parser")
        self.assertEqual(approval["contract_version"], "v1")

    def test_matching_contract_can_be_approved(self) -> None:
        pending = build_pending_approval(self.contract, self.patch_draft)
        approved = approve_execution_contract(pending, self.contract, self.patch_draft, approved_by="user")
        self.assertEqual(approved["approval_status"], "approved")
        self.assertEqual(approved["review_decision"], "approved")
        self.assertEqual(approved["approved_by"], "user")
        self.assertTrue(approved["approved_at"])
        self.assertFalse(approved["stale"])

    def test_changed_contract_invalidates_approval(self) -> None:
        pending = build_pending_approval(self.contract, self.patch_draft)
        changed_contract = dict(self.contract)
        changed_contract["rationale"] = "changed"
        result = approve_execution_contract(pending, changed_contract, self.patch_draft)
        self.assertEqual(result["approval_status"], "invalidated")
        self.assertTrue(result["stale"])
        self.assertEqual(result["review_reason"], "contract changed before approval")

    def test_reject_records_reason(self) -> None:
        pending = build_pending_approval(self.contract, self.patch_draft)
        rejected = reject_execution_contract(pending, reason="need narrower scope")
        self.assertEqual(rejected["approval_status"], "rejected")
        self.assertEqual(rejected["review_reason"], "need narrower scope")
        self.assertEqual(rejected["review_decision"], "rejected")

    def test_invalidate_sets_stale_true(self) -> None:
        pending = build_pending_approval(self.contract, self.patch_draft)
        invalidated = invalidate_execution_approval(pending, reason="contract refreshed")
        self.assertEqual(invalidated["approval_status"], "invalidated")
        self.assertTrue(invalidated["stale"])
        self.assertEqual(invalidated["review_reason"], "contract refreshed")

    def test_is_approval_stale_detects_contract_or_draft_changes(self) -> None:
        pending = build_pending_approval(self.contract, self.patch_draft)
        self.assertFalse(is_approval_stale(pending, self.contract, self.patch_draft))

        changed_contract = dict(self.contract)
        changed_contract["risk"] = "new risk"
        self.assertTrue(is_approval_stale(pending, changed_contract, self.patch_draft))

        changed_draft = self.patch_draft + "\n+# changed"
        self.assertTrue(is_approval_stale(pending, self.contract, changed_draft))

    def test_helpers_do_not_record_execution_side_effects(self) -> None:
        pending = build_pending_approval(self.contract, self.patch_draft)
        approved = approve_execution_contract(pending, self.contract, self.patch_draft)
        rejected = reject_execution_contract(pending, "reject")
        invalidated = invalidate_execution_approval(pending, "invalidate")

        for obj in [pending, approved, rejected, invalidated]:
            self.assertNotIn("commands_executed", obj)
            self.assertNotIn("artifacts_generated", obj)
            self.assertNotIn("file_writes", obj)


if __name__ == "__main__":
    unittest.main()
