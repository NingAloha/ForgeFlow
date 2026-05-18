from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from forgeflow.runtime.execution_request import write_execution_request
from forgeflow.runtime.lineage import upsert_lineage_entry
from forgeflow.runtime.materialization_preview import materialize_sandbox_preview
from forgeflow.runtime.review_state import set_review_decision


class MaterializePreviewEntrypointTests(unittest.TestCase):
    def test_materialize_preview_writes_generated_readme_and_execution_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime_root = Path(tmp_dir) / ".forgeflow"
            state_dir = runtime_root / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            runs_root = runtime_root / "runs"
            runs_root.mkdir(parents=True, exist_ok=True)

            run_id = "20260102T000000Z-new00000"
            run_dir = runs_root / run_id
            run_dir.mkdir(parents=True, exist_ok=True)

            # Summary presence is not required by the materialization path, but many tools assume it exists.
            (run_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1",
                        "run_id": run_id,
                        "original_request": "x",
                        "generated_project_dir": str(runtime_root / "generated" / "x"),
                        "state_dir": str(state_dir),
                        "latest_summary": "ok",
                        "latest_final_stage": "SOLUTION",
                        "latest_decision_type": "FORWARD",
                        "steps": [{"timestamp": "2026-01-02T00:00:00Z"}],
                    }
                ),
                encoding="utf-8",
            )

            # Lineage + review approvals are required for eligibility.
            for artifact in ["spec", "solution", "system_design", "implementation_status", "test_report"]:
                upsert_lineage_entry(run_dir=run_dir, run_id=run_id, artifact=artifact, generated_by="x")  # type: ignore[arg-type]
                set_review_decision(
                    run_dir=run_dir,
                    run_id=run_id,
                    artifact=artifact,
                    review_status="approved",
                    reviewed_by="tester",
                    review_reason="ok",
                    reviewed_at="2026-01-02T00:00:00Z",
                )

            write_execution_request(runs_root=runs_root, run_id=run_id, requested_by="tester", notes="x")

            result = materialize_sandbox_preview(state_dir=state_dir, run_id=run_id)
            self.assertEqual(result.get("run_id"), run_id)
            self.assertEqual(result.get("status"), "completed")

            readme_path = runtime_root / "generated" / run_id / "README.md"
            self.assertTrue(readme_path.exists())
            self.assertIn("ForgeFlow Sandbox Preview", readme_path.read_text(encoding="utf-8"))

            preview_path = run_dir / "execution_preview.json"
            self.assertTrue(preview_path.exists())
            preview_payload = json.loads(preview_path.read_text(encoding="utf-8"))
            self.assertEqual(preview_payload.get("run_id"), run_id)
            self.assertEqual(preview_payload.get("status"), "completed")

    def test_materialize_preview_records_failed_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime_root = Path(tmp_dir) / ".forgeflow"
            state_dir = runtime_root / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            runs_root = runtime_root / "runs"
            runs_root.mkdir(parents=True, exist_ok=True)

            run_id = "20260102T000000Z-new00000"
            run_dir = runs_root / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1",
                        "run_id": run_id,
                        "original_request": "x",
                        "generated_project_dir": str(runtime_root / "generated" / "x"),
                        "state_dir": str(state_dir),
                        "latest_summary": "ok",
                        "latest_final_stage": "SOLUTION",
                        "latest_decision_type": "FORWARD",
                        "steps": [{"timestamp": "2026-01-02T00:00:00Z"}],
                    }
                ),
                encoding="utf-8",
            )

            for artifact in ["spec", "solution", "system_design", "implementation_status", "test_report"]:
                upsert_lineage_entry(run_dir=run_dir, run_id=run_id, artifact=artifact, generated_by="x")  # type: ignore[arg-type]
                set_review_decision(
                    run_dir=run_dir,
                    run_id=run_id,
                    artifact=artifact,
                    review_status="approved",
                    reviewed_by="tester",
                    review_reason="ok",
                    reviewed_at="2026-01-02T00:00:00Z",
                )

            write_execution_request(runs_root=runs_root, run_id=run_id, requested_by="tester", notes="x")

            real_write_text = Path.write_text

            def guarded_write_text(self: Path, data: str, *args, **kwargs):  # type: ignore[no-untyped-def]
                # Fail only when attempting to write the generated README preview.
                if str(self).endswith(f"/generated/{run_id}/README.md"):
                    raise OSError("simulated write failure")
                return real_write_text(self, data, *args, **kwargs)

            with patch("pathlib.Path.write_text", new=guarded_write_text):
                with self.assertRaises(OSError):
                    materialize_sandbox_preview(state_dir=state_dir, run_id=run_id)

            preview_path = run_dir / "execution_preview.json"
            self.assertTrue(preview_path.exists())
            preview_payload = json.loads(preview_path.read_text(encoding="utf-8"))
            self.assertEqual(preview_payload.get("status"), "failed")
            self.assertIn("simulated write failure", str(preview_payload.get("error", "")))

            events_path = run_dir / "events.jsonl"
            self.assertTrue(events_path.exists())
            events_text = events_path.read_text(encoding="utf-8")
            self.assertIn('"event_type": "materialization_preview_failed"', events_text)


if __name__ == "__main__":
    unittest.main()
