from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from forgeflow.runtime.render import render_status
from forgeflow.runtime.status import build_status_snapshot
from forgeflow.runtime.run_index import build_index_entry, update_run_index
from main import main


class RuntimeStatusOverviewTests(unittest.TestCase):
    def test_artifact_availability_reflects_file_existence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_dir = Path(tmp_dir)
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "spec.json").write_text("{}", encoding="utf-8")

            status = build_status_snapshot(str(state_dir))

            self.assertTrue(status.artifacts["spec"])
            self.assertFalse(status.artifacts["solution"])
            self.assertFalse(status.artifacts["system_design"])
            self.assertFalse(status.artifacts["implementation_status"])
            self.assertFalse(status.artifacts["test_report"])

    def test_build_status_snapshot_has_no_orchestrator_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_dir = Path(tmp_dir) / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            runtime_root = state_dir.parent
            runs_root = runtime_root / "runs"
            generated_root = runtime_root / "generated"
            self.assertFalse(runs_root.exists())
            self.assertFalse(generated_root.exists())

            _ = build_status_snapshot(str(state_dir))

            self.assertFalse(runs_root.exists())
            self.assertFalse(generated_root.exists())

    def test_executed_stage_and_last_decision_come_from_latest_run_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime_root = Path(tmp_dir)
            state_dir = runtime_root / "state"
            state_dir.mkdir(parents=True, exist_ok=True)

            runs_root = runtime_root / "runs"
            run_dir = runs_root / "20260101T000000Z-aaaa1111"
            run_dir.mkdir(parents=True, exist_ok=True)
            summary_path = run_dir / "summary.json"
            payload = {
                "schema_version": "1",
                "run_id": "20260101T000000Z-aaaa1111",
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
            summary_path.write_text(json.dumps(payload), encoding="utf-8")

            status = build_status_snapshot(str(state_dir))

            self.assertEqual(status.executed_stage, "REQUIREMENTS")
            self.assertIsNotNone(status.last_decision)
            self.assertEqual(status.last_decision["action"], "FORWARD")
            self.assertEqual(status.last_decision["final_stage"], "SOLUTION")

    def test_runs_root_derives_from_state_dir_not_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime_root = Path(tmp_dir)
            state_dir = runtime_root / "state"
            state_dir.mkdir(parents=True, exist_ok=True)

            runs_root = runtime_root / "runs"
            run_dir = runs_root / "20260101T000000Z-bbbb2222"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "summary.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1",
                        "run_id": "20260101T000000Z-bbbb2222",
                        "original_request": "x",
                        "generated_project_dir": str(runtime_root / "generated" / "x"),
                        "state_dir": str(state_dir),
                        "latest_summary": "ok",
                        "latest_final_stage": "DESIGN",
                        "latest_decision_type": "STAY",
                        "steps": [
                            {
                                "timestamp": "2026-01-01T00:00:00Z",
                                "input": "",
                                "decision_type": "STAY",
                                "computed_stage": "DESIGN",
                                "final_stage": "DESIGN",
                                "executed_stage": "SOLUTION",
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

            # Call build_status_snapshot(None) but force StateManager to use our
            # temp state_dir as its resolved default; this simulates invoking
            # status from an unrelated CWD without passing --state-dir.
            from forgeflow.runtime import status as status_module

            original_init = status_module.StateManager.__init__

            def _init(self, *args, **kwargs):  # noqa: ANN001
                original_init(self, state_dir=str(state_dir))

            with patch.object(status_module.StateManager, "__init__", new=_init):
                status = build_status_snapshot(None)

            self.assertEqual(status.executed_stage, "SOLUTION")
            self.assertEqual(status.last_decision["final_stage"], "DESIGN")

    def test_latest_run_summary_prefers_run_id_over_mtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime_root = Path(tmp_dir)
            state_dir = runtime_root / "state"
            state_dir.mkdir(parents=True, exist_ok=True)

            runs_root = runtime_root / "runs"
            old_run = runs_root / "20260101T000000Z-aaaa0000"
            new_run = runs_root / "20260102T000000Z-bbbb0000"
            old_run.mkdir(parents=True, exist_ok=True)
            new_run.mkdir(parents=True, exist_ok=True)

            (old_run / "summary.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1",
                        "run_id": "20260101T000000Z-aaaa0000",
                        "original_request": "x",
                        "generated_project_dir": str(runtime_root / "generated" / "old"),
                        "state_dir": str(state_dir),
                        "latest_summary": "old",
                        "latest_final_stage": "REQUIREMENTS",
                        "latest_decision_type": "STAY",
                        "steps": [
                            {
                                "timestamp": "2026-01-01T00:00:00Z",
                                "input": "",
                                "decision_type": "STAY",
                                "computed_stage": "REQUIREMENTS",
                                "final_stage": "REQUIREMENTS",
                                "executed_stage": "REQUIREMENTS",
                                "summary": "old",
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

            (new_run / "summary.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1",
                        "run_id": "20260102T000000Z-bbbb0000",
                        "original_request": "x",
                        "generated_project_dir": str(runtime_root / "generated" / "new"),
                        "state_dir": str(state_dir),
                        "latest_summary": "new",
                        "latest_final_stage": "DESIGN",
                        "latest_decision_type": "FORWARD",
                        "steps": [
                            {
                                "timestamp": "2026-01-02T00:00:00Z",
                                "input": "",
                                "decision_type": "FORWARD",
                                "computed_stage": "SOLUTION",
                                "final_stage": "DESIGN",
                                "executed_stage": "SOLUTION",
                                "summary": "new",
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

            # Touch old summary after the new one exists: mtime would wrongly pick old.
            (old_run / "summary.json").write_text(
                (old_run / "summary.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            status = build_status_snapshot(str(state_dir))
            self.assertEqual(status.executed_stage, "SOLUTION")
            self.assertEqual(status.last_decision["summary"], "new")

    def test_latest_run_summary_ignores_nonstandard_run_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime_root = Path(tmp_dir)
            state_dir = runtime_root / "state"
            state_dir.mkdir(parents=True, exist_ok=True)

            runs_root = runtime_root / "runs"
            valid_run = runs_root / "20260103T000000Z-cccc0000"
            weird_run = runs_root / "zzzz-not-a-run-id"
            valid_run.mkdir(parents=True, exist_ok=True)
            weird_run.mkdir(parents=True, exist_ok=True)

            (valid_run / "summary.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1",
                        "run_id": "20260103T000000Z-cccc0000",
                        "original_request": "x",
                        "generated_project_dir": str(runtime_root / "generated" / "valid"),
                        "state_dir": str(state_dir),
                        "latest_summary": "valid",
                        "latest_final_stage": "SOLUTION",
                        "latest_decision_type": "STAY",
                        "steps": [
                            {
                                "timestamp": "2026-01-03T00:00:00Z",
                                "input": "",
                                "decision_type": "STAY",
                                "computed_stage": "SOLUTION",
                                "final_stage": "SOLUTION",
                                "executed_stage": "SOLUTION",
                                "summary": "valid",
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

            # If timestamp parsing is broken and we fall back to ordering by raw
            # directory name, "zzzz-..." would incorrectly win.
            (weird_run / "summary.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1",
                        "run_id": "zzzz-not-a-run-id",
                        "original_request": "x",
                        "generated_project_dir": "",
                        "state_dir": str(state_dir),
                        "latest_summary": "weird",
                        "latest_final_stage": "INIT",
                        "latest_decision_type": "STAY",
                        "steps": [],
                    }
                ),
                encoding="utf-8",
            )

            status = build_status_snapshot(str(state_dir))
            self.assertEqual(status.last_decision["summary"], "valid")

    def test_latest_run_summary_breaks_same_second_ties_by_payload_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime_root = Path(tmp_dir)
            state_dir = runtime_root / "state"
            state_dir.mkdir(parents=True, exist_ok=True)

            runs_root = runtime_root / "runs"
            # Same second prefix; lexicographic suffix order should not decide recency.
            older_run = runs_root / "20260104T000000Z-ffff0000"
            newer_run = runs_root / "20260104T000000Z-00000000"
            older_run.mkdir(parents=True, exist_ok=True)
            newer_run.mkdir(parents=True, exist_ok=True)

            older_payload = {
                "schema_version": "1",
                "run_id": "20260104T000000Z-ffff0000",
                "original_request": "x",
                "generated_project_dir": str(runtime_root / "generated" / "older"),
                "state_dir": str(state_dir),
                "latest_summary": "older",
                "latest_final_stage": "REQUIREMENTS",
                "latest_decision_type": "STAY",
                "steps": [
                    {
                        "timestamp": "2026-01-04T00:00:00.100000+00:00",
                        "input": "",
                        "decision_type": "STAY",
                        "computed_stage": "REQUIREMENTS",
                        "final_stage": "REQUIREMENTS",
                        "executed_stage": "REQUIREMENTS",
                        "summary": "older",
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
            newer_payload = {
                "schema_version": "1",
                "run_id": "20260104T000000Z-00000000",
                "original_request": "x",
                "generated_project_dir": str(runtime_root / "generated" / "newer"),
                "state_dir": str(state_dir),
                "latest_summary": "newer",
                "latest_final_stage": "SOLUTION",
                "latest_decision_type": "FORWARD",
                "steps": [
                    {
                        "timestamp": "2026-01-04T00:00:00.900000+00:00",
                        "input": "",
                        "decision_type": "FORWARD",
                        "computed_stage": "REQUIREMENTS",
                        "final_stage": "SOLUTION",
                        "executed_stage": "REQUIREMENTS",
                        "summary": "newer",
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

            (older_run / "summary.json").write_text(
                json.dumps(older_payload), encoding="utf-8"
            )
            (newer_run / "summary.json").write_text(
                json.dumps(newer_payload), encoding="utf-8"
            )

            status = build_status_snapshot(str(state_dir))
            self.assertEqual(status.last_decision["summary"], "newer")

    def test_cli_status_prints_overview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_dir = Path(tmp_dir) / "state"
            state_dir.mkdir(parents=True, exist_ok=True)

            with patch(
                "sys.argv",
                ["main.py", "--status", "--state-dir", str(state_dir)],
            ):
                with patch("builtins.print") as print_mock:
                    exit_code = main()

            self.assertEqual(exit_code, 0)
            printed = "\n".join(
                str(call.args[0]) for call in print_mock.call_args_list if call.args
            )
            self.assertIn("ForgeFlow Status", printed)
            self.assertIn("Artifacts", printed)

    def test_status_does_not_crash_when_question_state_is_answered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_dir = Path(tmp_dir) / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "question_state.json").write_text(
                json.dumps(
                    {
                        "status": "answered",
                        "stage_name": "SOLUTION",
                        "state_key": "solution",
                        "blocking": True,
                        "questions": [{"id": "q1"}],
                        "created_by": "Solution Engineer",
                        "resolution_summary": "ok",
                    }
                ),
                encoding="utf-8",
            )

            status = build_status_snapshot(str(state_dir))

            self.assertEqual(status.current_stage, "SOLUTION")

    def test_render_status_is_pure_string_formatting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_dir = Path(tmp_dir) / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            status = build_status_snapshot(str(state_dir))
            rendered = render_status(status)
            self.assertIsInstance(rendered, str)
            self.assertIn("ForgeFlow Status", rendered)

    def test_status_prefers_valid_created_at_over_invalid_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime_root = Path(tmp_dir)
            state_dir = runtime_root / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            runs_root = runtime_root / "runs"
            runs_root.mkdir(parents=True, exist_ok=True)

            valid_run = "20260101T000000Z-aaaa0000"
            invalid_run = "zzzz-invalid-run-id"

            (runs_root / valid_run).mkdir(parents=True, exist_ok=True)
            (runs_root / invalid_run).mkdir(parents=True, exist_ok=True)

            payload = {
                "schema_version": "1",
                "run_id": valid_run,
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
            (runs_root / valid_run / "summary.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            # Provide a summary for the invalid run too; it must still be de-prioritized.
            bad_payload = dict(payload)
            bad_payload["run_id"] = invalid_run
            (runs_root / invalid_run / "summary.json").write_text(
                json.dumps(bad_payload), encoding="utf-8"
            )

            update_run_index(
                runs_root,
                build_index_entry(run_id=invalid_run, status="finished", final_stage="DONE"),
            )
            update_run_index(
                runs_root,
                build_index_entry(run_id=valid_run, status="finished", final_stage="SOLUTION"),
            )

            status = build_status_snapshot(str(state_dir))
            self.assertEqual(status.executed_stage, "REQUIREMENTS")
            self.assertEqual(status.last_decision["final_stage"], "SOLUTION")

    def test_status_falls_back_when_index_points_to_missing_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime_root = Path(tmp_dir)
            state_dir = runtime_root / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            runs_root = runtime_root / "runs"
            runs_root.mkdir(parents=True, exist_ok=True)

            missing_run = "20260103T000000Z-missing0"
            scan_run = "20260101T000000Z-scan0000"
            (runs_root / scan_run).mkdir(parents=True, exist_ok=True)
            (runs_root / scan_run / "summary.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1",
                        "run_id": scan_run,
                        "original_request": "x",
                        "generated_project_dir": str(runtime_root / "generated" / "s"),
                        "state_dir": str(state_dir),
                        "latest_summary": "ok",
                        "latest_final_stage": "DESIGN",
                        "latest_decision_type": "FORWARD",
                        "steps": [
                            {
                                "timestamp": "2026-01-01T00:00:00Z",
                                "input": "",
                                "decision_type": "FORWARD",
                                "computed_stage": "SOLUTION",
                                "final_stage": "DESIGN",
                                "executed_stage": "SOLUTION",
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

            update_run_index(
                runs_root,
                build_index_entry(run_id=missing_run, status="finished", final_stage="DONE"),
            )
            status = build_status_snapshot(str(state_dir))
            self.assertEqual(status.executed_stage, "SOLUTION")
            self.assertEqual(status.last_decision["final_stage"], "DESIGN")

    def test_status_falls_back_when_index_is_corrupted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            runtime_root = Path(tmp_dir)
            state_dir = runtime_root / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            runs_root = runtime_root / "runs"
            runs_root.mkdir(parents=True, exist_ok=True)

            run_id = "20260101T000000Z-aaaa0000"
            (runs_root / run_id).mkdir(parents=True, exist_ok=True)
            (runs_root / run_id / "summary.json").write_text(
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
            (runs_root / "index.json").write_text("{bad json", encoding="utf-8")
            status = build_status_snapshot(str(state_dir))
            self.assertEqual(status.executed_stage, "REQUIREMENTS")
            self.assertEqual(status.last_decision["final_stage"], "SOLUTION")


if __name__ == "__main__":
    unittest.main()
