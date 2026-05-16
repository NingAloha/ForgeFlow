from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgeflow.runtime.run_index import load_run_index
from forgeflow.runtime.run_index_repair import repair_run_index


class RuntimeRunIndexRepairTests(unittest.TestCase):
    def test_repair_overwrites_corrupted_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime_root = Path(tmp_dir)
            runs_root = runtime_root / "runs"
            runs_root.mkdir(parents=True, exist_ok=True)

            run_id = "20260101T000000Z-demo0000"
            run_dir = runs_root / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1",
                        "run_id": run_id,
                        "original_request": "x",
                        "generated_project_dir": str(runtime_root / "generated" / "x"),
                        "state_dir": str(runtime_root / "state"),
                        "latest_summary": "ok",
                        "latest_final_stage": "SOLUTION",
                        "latest_decision_type": "FORWARD",
                        "steps": [{"timestamp": "2026-01-01T00:00:00Z"}],
                    }
                ),
                encoding="utf-8",
            )

            (runs_root / "index.json").write_text("{bad json", encoding="utf-8")
            result = repair_run_index(runs_root)
            self.assertEqual(result.runs_written, 1)

            index = load_run_index(runs_root)
            self.assertIsNotNone(index)
            assert index is not None
            self.assertEqual(len(index.runs), 1)
            self.assertEqual(index.runs[0].run_id, run_id)


if __name__ == "__main__":
    unittest.main()

