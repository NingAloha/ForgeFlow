from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgeflow.runtime.run_index import build_index_entry, load_run_index, update_run_index


class RuntimeRunIndexTests(unittest.TestCase):
    def test_created_at_parsing_failure_sets_unknown(self) -> None:
        entry = build_index_entry(run_id="malformed-run-id", status="running", final_stage="")
        self.assertEqual(entry.created_at, "")
        self.assertEqual(entry.status, "unknown")

    def test_update_run_index_upserts_and_updates_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_root = Path(temp_dir) / "runs"
            runs_root.mkdir(parents=True, exist_ok=True)
            run_id = "20260101T000000Z-demo0000"
            update_run_index(runs_root, build_index_entry(run_id=run_id, status="running", final_stage=""))
            update_run_index(
                runs_root,
                build_index_entry(
                    run_id=run_id,
                    status="finished",
                    final_stage="DESIGN",
                    finished_at="2026-01-01T00:00:01Z",
                ),
            )
            index = load_run_index(runs_root)
            self.assertIsNotNone(index)
            self.assertEqual(len(index.runs), 1)
            self.assertEqual(index.runs[0].run_id, run_id)
            self.assertEqual(index.runs[0].status, "finished")
            self.assertEqual(index.runs[0].final_stage, "DESIGN")
            self.assertEqual(index.runs[0].finished_at, "2026-01-01T00:00:01Z")

    def test_load_run_index_returns_none_on_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_root = Path(temp_dir) / "runs"
            runs_root.mkdir(parents=True, exist_ok=True)
            (runs_root / "index.json").write_text("{bad json", encoding="utf-8")
            self.assertIsNone(load_run_index(runs_root))

    def test_update_run_index_is_atomic_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_root = Path(temp_dir) / "runs"
            runs_root.mkdir(parents=True, exist_ok=True)
            run_id = "20260101T000000Z-demo0000"
            update_run_index(runs_root, build_index_entry(run_id=run_id, status="running", final_stage=""))
            payload = json.loads((runs_root / "index.json").read_text(encoding="utf-8"))
            self.assertIn("runs", payload)

    def test_sort_breaks_same_second_ties_by_finished_at(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runs_root = Path(temp_dir) / "runs"
            runs_root.mkdir(parents=True, exist_ok=True)
            run_a = "20260101T000000Z-aaaa0000"
            run_b = "20260101T000000Z-bbbb0000"
            update_run_index(
                runs_root,
                build_index_entry(
                    run_id=run_a,
                    status="finished",
                    final_stage="SOLUTION",
                    finished_at="2026-01-01T00:00:02Z",
                ),
            )
            update_run_index(
                runs_root,
                build_index_entry(
                    run_id=run_b,
                    status="finished",
                    final_stage="DESIGN",
                    finished_at="2026-01-01T00:00:03Z",
                ),
            )
            index = load_run_index(runs_root)
            self.assertIsNotNone(index)
            self.assertEqual(index.runs[0].run_id, run_b)


if __name__ == "__main__":
    unittest.main()
