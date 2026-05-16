from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgeflow.runtime.status import build_status_snapshot


class StatusApprovalsTests(unittest.TestCase):
    def test_status_reads_approval_artifacts_from_latest_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime_root = Path(tmp_dir)
            state_dir = runtime_root / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            runs_root = runtime_root / "runs"
            runs_root.mkdir(parents=True, exist_ok=True)

            run_id = "20260101T000000Z-demo0000"
            run_dir = runs_root / run_id
            approvals_dir = run_dir / "approvals"
            approvals_dir.mkdir(parents=True, exist_ok=True)

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
                        "steps": [
                            {
                                "timestamp": "2026-01-01T00:00:00Z",
                                "input": "",
                                "decision_type": "FORWARD",
                                "computed_stage": "REQUIREMENTS",
                                "final_stage": "SOLUTION",
                                "executed_stage": "REQUIREMENTS",
                                "summary": "ok",
                                "llm_trace": {
                                    "status": "none",
                                    "failure_type": "none",
                                    "repair_attempts": 0,
                                    "validation_errors": [],
                                    "raw_excerpt": "",
                                    "model": "",
                                    "provider": "",
                                    "protocol": "openai",
                                    "latency_ms": 0,
                                    "error": None,
                                },
                                "execution_trace": {},
                                "state_changes": [],
                                "question_state": {"status": "idle"},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            (approvals_dir / "a.json").write_text(
                json.dumps(
                    {
                        "approval_status": "approved",
                        "contract_hash": "x" * 64,
                        "contract_version": "1",
                        "target_module": "core",
                        "review_decision": "approve",
                        "review_reason": "ok",
                        "approved_at": "2026-01-01T00:00:01Z",
                        "approved_by": "alice",
                        "stale": False,
                    }
                ),
                encoding="utf-8",
            )

            status = build_status_snapshot(str(state_dir))
            self.assertTrue(status.approval_artifacts)
            self.assertEqual(status.approval_artifacts[0]["approval_status"], "approved")


if __name__ == "__main__":
    unittest.main()

