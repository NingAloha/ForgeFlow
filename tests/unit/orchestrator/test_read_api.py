from __future__ import annotations

import tempfile
import unittest

from agents.orchestrator import Orchestrator
from agents.state_manager import StateManager


class OrchestratorReadApiTests(unittest.TestCase):
    def test_read_api_returns_state_without_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            orchestrator = Orchestrator(state_manager=StateManager(state_dir=tmp_dir))
            calls: list[str] = []

            original_agents = dict(orchestrator.agents)
            for stage, agent in original_agents.items():
                original_run = agent.run

                def _wrapped_run(context, _orig=original_run):  # noqa: ANN001
                    calls.append(str(stage))
                    return _orig(context)

                agent.run = _wrapped_run  # type: ignore[assignment]

            snapshot_before = orchestrator.get_status_snapshot()
            spec = orchestrator.get_artifact_for_display("spec")
            unknown = orchestrator.get_artifact_for_display("unknown")
            names = orchestrator.get_artifact_names()
            snapshot_after = orchestrator.get_status_snapshot()

            self.assertIsInstance(snapshot_before, dict)
            self.assertIsInstance(spec, dict)
            self.assertEqual(unknown, {})
            self.assertIn("spec", names)
            self.assertIn("system_design", names)
            self.assertEqual(snapshot_before, snapshot_after)
            self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
