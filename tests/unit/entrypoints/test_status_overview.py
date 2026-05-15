from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from forgeflow.runtime.render import render_status
from forgeflow.runtime.status import build_status_snapshot
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


if __name__ == "__main__":
    unittest.main()
