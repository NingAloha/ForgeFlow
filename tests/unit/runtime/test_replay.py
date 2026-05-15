from __future__ import annotations

import builtins
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from forgeflow.runtime.replay import ReplayLoadError, load_replay_snapshot


class RuntimeReplayInvariantTests(unittest.TestCase):
    def test_replay_never_mutates_filesystem(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir) / "state"
            run_id = "20260101T000000Z-demo"
            run_dir = Path(temp_dir) / "runs" / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "summary.json").write_text(
                '{"schema_version":"1","run_id":"20260101T000000Z-demo","steps":[]}\n',
                encoding="utf-8",
            )

            real_open = builtins.open

            def guarded_open(file, mode="r", *args, **kwargs):  # type: ignore[no-untyped-def]
                text_mode = str(mode)
                if any(flag in text_mode for flag in ("w", "a", "x", "+")):
                    raise AssertionError(f"Replay attempted to open for write: mode={mode}")
                return real_open(file, mode, *args, **kwargs)

            with patch("pathlib.Path.write_text", side_effect=AssertionError("write_text not allowed")), patch(
                "pathlib.Path.mkdir", side_effect=AssertionError("mkdir not allowed")
            ), patch("builtins.open", side_effect=guarded_open):
                snapshot = load_replay_snapshot(run_id, str(state_dir))
                self.assertEqual(snapshot.run_id, run_id)

    def test_replay_never_invokes_agents(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir) / "state"
            run_id = "20260101T000000Z-demo"
            run_dir = Path(temp_dir) / "runs" / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "summary.json").write_text(
                '{"schema_version":"1","run_id":"20260101T000000Z-demo","steps":[]}\n',
                encoding="utf-8",
            )

            with patch(
                "agents.orchestrator.core.Orchestrator.__init__",
                side_effect=AssertionError("Orchestrator must not be constructed in replay"),
            ), patch(
                "agents.requirements_engineer.agent.RequirementsEngineerAgent.__init__",
                side_effect=AssertionError("Agents must not be constructed in replay"),
            ):
                snapshot = load_replay_snapshot(run_id, str(state_dir))
                self.assertEqual(snapshot.run_id, run_id)

    def test_missing_run_returns_structured_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir) / "state"
            with self.assertRaises(ReplayLoadError) as ctx:
                load_replay_snapshot("missing-run", str(state_dir))
        self.assertEqual(ctx.exception.code, "run_not_found")

    def test_replay_uses_only_run_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir) / "state"
            run_id = "20260101T000000Z-demo"
            run_dir = Path(temp_dir) / "runs" / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "summary.json").write_text(
                '{"schema_version":"1","run_id":"20260101T000000Z-demo","steps":[]}\n',
                encoding="utf-8",
            )

            live_state_dir = Path(temp_dir) / ".forgeflow" / "state"
            live_state_dir.mkdir(parents=True, exist_ok=True)
            (live_state_dir / "spec.json").write_text(
                '{"poison":"if replay reads this, it is consulting live state"}\n',
                encoding="utf-8",
            )

            real_read_text = Path.read_text

            def guarded_read_text(self: Path, *args, **kwargs):  # type: ignore[no-untyped-def]
                resolved = str(self.resolve())
                if "/.forgeflow/state/" in resolved or resolved.endswith("/.forgeflow/state"):
                    raise AssertionError(f"Replay attempted to read live state: {resolved}")
                return real_read_text(self, *args, **kwargs)

            with patch("pathlib.Path.read_text", new=guarded_read_text):
                snapshot = load_replay_snapshot(run_id, str(state_dir))
                self.assertEqual(snapshot.run_id, run_id)


if __name__ == "__main__":
    unittest.main()

