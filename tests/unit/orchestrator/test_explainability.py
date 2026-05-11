from __future__ import annotations

import unittest

from agents.orchestrator import Orchestrator, Stage
from tests.unit.support.orchestrator_fixtures import make_testing_states


class OrchestratorExplainabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = Orchestrator()

    def test_forward_evidence_explains_downstream_consumability(self) -> None:
        states = make_testing_states()
        target, evidence = self.orchestrator.evaluate_forward_transition(
            states, Stage.IMPLEMENTATION
        )
        self.assertEqual(target, Stage.TESTING)
        self.assertTrue(
            any("consumable by TESTING" in item for item in evidence),
            evidence,
        )

    def test_implementation_non_ready_evidence_contains_missing_invariant_hint(
        self,
    ) -> None:
        states = make_testing_states()
        states["implementation_status"]["implementation_status"] = "blocked"
        states["implementation_status"]["contract_compliance"] = False
        states["implementation_status"]["blockers"] = ["missing design contract"]
        target, evidence = self.orchestrator.evaluate_forward_transition(
            states, Stage.IMPLEMENTATION
        )
        self.assertIsNone(target)
        self.assertTrue(
            any("blockers remain" in item for item in evidence),
            evidence,
        )

    def test_wait_evidence_mentions_progress_pause(self) -> None:
        states = make_testing_states()
        states["question_state"] = {
            "status": "awaiting_user",
            "stage_name": "IMPLEMENTATION",
            "state_key": "implementation_status",
            "blocking": True,
            "questions": [{"id": "q1"}],
            "created_by": "Implementation Engineer",
            "resolution_summary": "",
        }
        decision = self.orchestrator.resolve_transition(states)
        self.assertTrue(decision.wait_for_user_input)
        self.assertTrue(
            any("Progress is paused" in item for item in decision.evidence),
            decision.evidence,
        )


if __name__ == "__main__":
    unittest.main()
