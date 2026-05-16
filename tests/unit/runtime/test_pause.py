from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agents.orchestrator import Orchestrator, Stage
from agents.state_manager import StateManager
from forgeflow.runtime.pause import load_runtime_pause_state


class RuntimePauseTests(unittest.TestCase):
    def test_load_pause_defaults_to_not_paused(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir) / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            pause = load_runtime_pause_state(state_dir)
            self.assertFalse(pause.paused)

    def test_orchestrator_respects_runtime_pause(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir) / "state"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "runtime_pause.json").write_text(
                json.dumps({"paused": True, "reason": "maintenance"}), encoding="utf-8"
            )
            manager = StateManager(state_dir=str(state_dir))
            orchestrator = Orchestrator(state_manager=manager)
            result = orchestrator.orchestrate("x", original_request="x")
            self.assertTrue(result.decision.wait_for_user_input)
            self.assertEqual(result.decision.reason, "Runtime is paused.")
            self.assertIsNone(result.executed_stage)
            self.assertNotEqual(result.decision.final_stage, Stage.DONE)


if __name__ == "__main__":
    unittest.main()

