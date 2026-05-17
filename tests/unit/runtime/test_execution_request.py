from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgeflow.runtime.execution_request import ensure_safe_run_id, write_execution_request


class ExecutionRequestTests(unittest.TestCase):
    def test_ensure_safe_run_id_rejects_traversal(self) -> None:
        with self.assertRaises(ValueError):
            ensure_safe_run_id("../bad")
        with self.assertRaises(ValueError):
            ensure_safe_run_id("a/b")

    def test_write_execution_request_requires_existing_run_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runs_root = Path(tmp_dir) / "runs"
            runs_root.mkdir(parents=True, exist_ok=True)
            with self.assertRaises(FileNotFoundError):
                _ = write_execution_request(
                    runs_root=runs_root,
                    run_id="20260101T000000Z-missing0",
                    requested_by="u",
                    notes="n",
                )

    def test_write_execution_request_writes_expected_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runs_root = Path(tmp_dir) / "runs"
            run_id = "20260101T000000Z-demo0000"
            run_dir = runs_root / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            path = write_execution_request(
                runs_root=runs_root,
                run_id=run_id,
                requested_by="alice",
                notes="hello",
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], "1")
            self.assertEqual(payload["run_id"], run_id)
            self.assertEqual(payload["requested_by"], "alice")
            self.assertEqual(payload["requested_capability"], "controlled_execution")
            self.assertEqual(payload["notes"], "hello")


if __name__ == "__main__":
    unittest.main()

