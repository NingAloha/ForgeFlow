from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agents.implementation_engineer.execution_approval import build_pending_approval
from agents.implementation_engineer.execution_approval_store import (
    build_approval_artifact_path,
    load_approval_artifact,
    save_approval_artifact_for_run,
    save_approval_artifact,
    validate_approval_artifact,
)


class ExecutionApprovalStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = {
            "execution_contract_version": "v1",
            "target_module": "markdown_parser",
            "create": [
                "src/markdown_parser/README.md",
                "tests/markdown_parser/README.md",
            ],
            "modify": [],
            "delete": [],
        }
        self.patch_draft = "diff --git a/src/markdown_parser/README.md b/src/markdown_parser/README.md\nnew file mode 100644"
        self.pending = build_pending_approval(self.contract, self.patch_draft)

    def test_artifact_path_is_under_run_dir_approvals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = Path(tmp_dir) / "run-1"
            path = build_approval_artifact_path(run_dir, self.pending["contract_hash"])
            self.assertEqual(path.parent, run_dir.resolve() / "approvals")
            self.assertEqual(path.name, f"{self.pending['contract_hash']}.json")

    def test_parent_dir_auto_created_on_save(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = Path(tmp_dir) / "run-1"
            path = build_approval_artifact_path(run_dir, self.pending["contract_hash"])
            save_approval_artifact(path, self.pending)
            self.assertTrue(path.parent.exists())
            self.assertTrue(path.exists())

    def test_save_for_run_writes_to_run_scoped_approvals_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = Path(tmp_dir) / "run-1"
            path = save_approval_artifact_for_run(
                run_dir,
                self.pending["contract_hash"],
                self.pending,
            )
            self.assertEqual(path.parent, run_dir.resolve() / "approvals")
            self.assertEqual(path.name, f"{self.pending['contract_hash']}.json")
            self.assertTrue(path.exists())

    def test_save_load_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = Path(tmp_dir) / "run-1"
            path = build_approval_artifact_path(run_dir, self.pending["contract_hash"])
            save_approval_artifact(path, self.pending)
            loaded = load_approval_artifact(path)
            self.assertEqual(loaded, self.pending)

    def test_missing_file_returns_empty_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing = Path(tmp_dir) / "missing.json"
            self.assertEqual(load_approval_artifact(missing), {})

    def test_validate_passes_for_matching_hash(self) -> None:
        issues = validate_approval_artifact(
            self.pending, self.contract, self.patch_draft
        )
        self.assertEqual(issues, [])

    def test_contract_change_returns_stale_issue(self) -> None:
        changed = dict(self.contract)
        changed["target_module"] = "summary_extractor"
        issues = validate_approval_artifact(self.pending, changed, self.patch_draft)
        self.assertIn("approval artifact is stale", issues)

    def test_invalid_status_returns_issue(self) -> None:
        invalid = dict(self.pending)
        invalid["approval_status"] = "unknown"
        issues = validate_approval_artifact(invalid, self.contract, self.patch_draft)
        self.assertIn("invalid approval_status: unknown", issues)

    def test_approved_and_stale_true_returns_issue(self) -> None:
        approved = dict(self.pending)
        approved["approval_status"] = "approved"
        approved["stale"] = True
        issues = validate_approval_artifact(approved, self.contract, self.patch_draft)
        self.assertIn("approved artifact must not be marked stale", issues)

    def test_path_builder_rejects_non_hash_filenames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = Path(tmp_dir) / "run-1"
            with self.assertRaises(ValueError):
                build_approval_artifact_path(run_dir, "../../bad")
            with self.assertRaises(ValueError):
                build_approval_artifact_path(run_dir, "not-a-sha")

    def test_save_for_run_rejects_non_sha256_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = Path(tmp_dir) / "run-1"
            with self.assertRaises(ValueError):
                save_approval_artifact_for_run(run_dir, "bad-hash", self.pending)

    def test_save_approval_artifact_rejects_arbitrary_filename_and_path_traversal(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            approvals_dir = base / "approvals"
            approvals_dir.mkdir(parents=True, exist_ok=True)

            with self.assertRaises(ValueError):
                save_approval_artifact(approvals_dir / "custom-name.json", self.pending)
            with self.assertRaises(ValueError):
                save_approval_artifact(
                    base / "not_approvals" / f"{self.pending['contract_hash']}.json",
                    self.pending,
                )

    def test_store_writes_only_under_tmp_run_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dir = Path(tmp_dir) / "runs" / "run-1"
            path = save_approval_artifact_for_run(
                run_dir,
                self.pending["contract_hash"],
                self.pending,
            )
            self.assertTrue(str(path.resolve()).startswith(str(run_dir.resolve())))


if __name__ == "__main__":
    unittest.main()
