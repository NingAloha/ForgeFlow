from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgeflow.runtime.execution_gate import build_execution_gate_snapshot
from forgeflow.runtime.review_state import upsert_pending_review
from forgeflow.runtime.run_index import update_run_index, build_index_entry
from forgeflow.runtime.lineage import upsert_lineage_entry
from forgeflow.runtime.review_state import set_review_decision
from forgeflow.runtime.execution_request import write_execution_request


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
            self.assertIn("pending_reviews", snapshot.materialization_reasons)
            self.assertIn("execution_request_missing", snapshot.materialization_reasons)
            self.assertFalse(snapshot.eligible_for_materialization)
            self.assertFalse(snapshot.eligible_for_mutation)
            self.assertIn("no_approvals", snapshot.mutation_reasons)

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
            self.assertNotIn("no_approvals", snapshot.mutation_reasons)

    def test_gate_reports_invalidations_from_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime_root = Path(tmp_dir)
            state_dir = runtime_root / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
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
                        "state_dir": str(state_dir),
                        "latest_summary": "ok",
                        "latest_final_stage": "SOLUTION",
                        "latest_decision_type": "FORWARD",
                        "steps": [{"timestamp": "2026-01-01T00:00:00Z"}],
                    }
                ),
                encoding="utf-8",
            )

            # Populate downstream so invalidation has an effect.
            upsert_lineage_entry(run_dir=run_dir, run_id=run_id, artifact="solution", generated_by="S")
            upsert_lineage_entry(run_dir=run_dir, run_id=run_id, artifact="system_design", generated_by="D")
            upsert_lineage_entry(run_dir=run_dir, run_id=run_id, artifact="spec", generated_by="R2")

            snapshot = build_execution_gate_snapshot(state_dir=state_dir)
            self.assertIn("artifacts_invalidated", snapshot.materialization_reasons)

    def test_gate_is_target_run_only_and_can_be_materialization_eligible(self) -> None:
        """
        Migration intent:
        - gate_status/reasons now represent the materialization gate.
        - mutation eligibility remains blocked in v0.2.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime_root = Path(tmp_dir)
            state_dir = runtime_root / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            runs_root = runtime_root / "runs"
            runs_root.mkdir(parents=True, exist_ok=True)

            run_a = "20260101T000000Z-old00000"
            run_b = "20260102T000000Z-new00000"

            run_a_dir = runs_root / run_a
            run_a_dir.mkdir(parents=True, exist_ok=True)
            upsert_pending_review(run_dir=run_a_dir, run_id=run_a, artifact="spec")
            # Ensure run_a exists as a candidate directory but should not pollute target-run diagnostics.
            (run_a_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1",
                        "run_id": run_a,
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

            run_b_dir = runs_root / run_b
            run_b_dir.mkdir(parents=True, exist_ok=True)
            (run_b_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1",
                        "run_id": run_b,
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

            # Lineage complete for run_b.
            for artifact in ["spec", "solution", "system_design", "implementation_status", "test_report"]:
                upsert_lineage_entry(run_dir=run_b_dir, run_id=run_b, artifact=artifact, generated_by="x")  # type: ignore[arg-type]
                set_review_decision(
                    run_dir=run_b_dir,
                    run_id=run_b,
                    artifact=artifact,
                    review_status="approved",
                    reviewed_by="tester",
                    review_reason="ok",
                    reviewed_at="2026-01-02T00:00:00Z",
                )

            # Execution request exists for run_b.
            write_execution_request(runs_root=runs_root, run_id=run_b, requested_by="tester", notes="x")

            snapshot = build_execution_gate_snapshot(state_dir=state_dir, run_id=run_b)
            self.assertTrue(snapshot.eligible_for_materialization)
            self.assertEqual(snapshot.gate_status, "ready")
            self.assertEqual(snapshot.materialization_reasons, [])
            self.assertNotIn("pending_reviews", snapshot.materialization_reasons)
            self.assertFalse(snapshot.eligible_for_mutation)

    def test_gate_blocks_materialization_when_execution_request_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime_root = Path(tmp_dir)
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

            snapshot = build_execution_gate_snapshot(state_dir=state_dir, run_id=run_id)
            self.assertFalse(snapshot.eligible_for_materialization)
            self.assertIn("execution_request_missing", snapshot.materialization_reasons)


if __name__ == "__main__":
    unittest.main()
