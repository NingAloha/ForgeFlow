from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgeflow.runtime.execution_gate import build_execution_gate_snapshot
from forgeflow.runtime.review_state import upsert_pending_review
from forgeflow.runtime.run_index import update_run_index, build_index_entry


class ExecutionGateTests(unittest.TestCase):
    def test_gate_reports_blocked_when_pending_reviews_and_no_approvals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime_root = Path(tmp_dir)
            state_dir = runtime_root / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            runs_root = runtime_root / "runs"
            runs_root.mkdir(parents=True, exist_ok=True)

            run_id = "20260101T000000Z-demo0000"
            run_dir = runs_root / run_id
            run_dir.mkdir(parents=True, exist_ok=True)

            upsert_pending_review(run_dir=run_dir, run_id=run_id, artifact="spec")
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
                        "steps": [{"timestamp": "2026-01-01T00:00:00Z"}],
                    }
                ),
                encoding="utf-8",
            )

            snapshot = build_execution_gate_snapshot(state_dir=state_dir)
            self.assertEqual(snapshot.gate_status, "blocked")
            self.assertIn("pending_reviews", snapshot.reasons)
            self.assertIn("no_approvals", snapshot.reasons)

    def test_gate_prefers_filesystem_latest_when_index_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime_root = Path(tmp_dir)
            state_dir = runtime_root / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            runs_root = runtime_root / "runs"
            runs_root.mkdir(parents=True, exist_ok=True)

            old_run = "20260101T000000Z-old00000"
            new_run = "20260102T000000Z-new00000"

            old_dir = runs_root / old_run
            old_dir.mkdir(parents=True, exist_ok=True)
            (old_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1",
                        "run_id": old_run,
                        "original_request": "x",
                        "generated_project_dir": str(runtime_root / "generated" / "x"),
                        "state_dir": str(state_dir),
                        "latest_summary": "ok",
                        "latest_final_stage": "SOLUTION",
                        "latest_decision_type": "FORWARD",
                        "steps": [{"timestamp": "2026-01-01T00:00:00Z"}],
                    }
                ),
                encoding="utf-8",
            )

            new_dir = runs_root / new_run
            approvals_dir = new_dir / "approvals"
            approvals_dir.mkdir(parents=True, exist_ok=True)
            (new_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1",
                        "run_id": new_run,
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
            (approvals_dir / "a.json").write_text(
                json.dumps({"approval_status": "approved", "contract_hash": "x" * 64}),
                encoding="utf-8",
            )

            # Stale index only includes the old run (cache lag).
            update_run_index(
                runs_root,
                build_index_entry(run_id=old_run, status="finished", final_stage="SOLUTION"),
            )

            snapshot = build_execution_gate_snapshot(state_dir=state_dir)
            self.assertEqual(snapshot.latest_run_id, new_run)
            self.assertNotIn("no_approvals", snapshot.reasons)


if __name__ == "__main__":
    unittest.main()
