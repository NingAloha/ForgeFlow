from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from forgeflow.runtime.events import append_runtime_event, load_runtime_events


class RuntimeEventsTests(unittest.TestCase):
    def test_append_creates_events_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "runs" / "run-1"
            run_dir.mkdir(parents=True, exist_ok=True)
            append_runtime_event(run_dir, event_type="run_started", run_id="run-1")
            self.assertTrue((run_dir / "events.jsonl").exists())

    def test_sequence_monotonic_and_preserves_existing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "runs" / "run-1"
            run_dir.mkdir(parents=True, exist_ok=True)
            append_runtime_event(run_dir, event_type="run_started", run_id="run-1")
            append_runtime_event(run_dir, event_type="decision_computed", run_id="run-1")
            lines = (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
            first = json.loads(lines[0])
            second = json.loads(lines[1])
            self.assertEqual(first["sequence"], 1)
            self.assertEqual(second["sequence"], 2)

    def test_sequence_uses_max_valid_event_when_bad_lines_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "runs" / "run-1"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "events.jsonl").write_text(
                (
                    '{"timestamp":"t","event_type":"run_started","run_id":"run-1","sequence":1,"payload":{}}\n'
                    '{bad json\n'
                ),
                encoding="utf-8",
            )
            event = append_runtime_event(run_dir, event_type="decision_computed", run_id="run-1")
            self.assertEqual(event.sequence, 2)

    def test_load_runtime_events_reads_in_order_and_records_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "runs" / "run-1"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "events.jsonl").write_text(
                (
                    '{"timestamp":"t1","event_type":"run_started","run_id":"run-1","sequence":1,"payload":{}}\n'
                    '{bad json\n'
                    '{"timestamp":"t2","event_type":"run_finished","run_id":"run-1","sequence":2,"payload":{}}\n'
                ),
                encoding="utf-8",
            )
            log = load_runtime_events(run_dir)
            self.assertEqual([e.sequence for e in log.events], [1, 2])
            self.assertTrue(log.errors)

    def test_step_finished_is_accepted_by_event_loader(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "runs" / "run-1"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "events.jsonl").write_text(
                (
                    '{"timestamp":"t1","event_type":"run_started","run_id":"run-1","sequence":1,"payload":{}}\n'
                    '{"timestamp":"t2","event_type":"step_finished","run_id":"run-1","sequence":2,"payload":{}}\n'
                ),
                encoding="utf-8",
            )
            log = load_runtime_events(run_dir)
            self.assertEqual([e.event_type for e in log.events], ["run_started", "step_finished"])

    def test_materialization_preview_failed_is_accepted_by_event_loader(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir) / "runs" / "run-1"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "events.jsonl").write_text(
                (
                    '{"timestamp":"t1","event_type":"run_started","run_id":"run-1","sequence":1,"payload":{}}\n'
                    '{"timestamp":"t2","event_type":"materialization_preview_failed","run_id":"run-1","sequence":2,"payload":{"error":"x"}}\n'
                ),
                encoding="utf-8",
            )
            log = load_runtime_events(run_dir)
            self.assertEqual(
                [e.event_type for e in log.events],
                ["run_started", "materialization_preview_failed"],
            )


if __name__ == "__main__":
    unittest.main()
