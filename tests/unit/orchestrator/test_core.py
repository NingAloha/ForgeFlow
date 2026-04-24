from __future__ import annotations

import unittest

from agents.base import AgentResult
from agents.orchestrator import Orchestrator, Stage, TransitionDecision
from tests.unit.support.orchestrator_fixtures import (
    make_design_ready_states,
    make_done_states,
    make_empty_states,
    make_implementing_states,
    make_requirements_ready_states,
    make_solution_ready_states,
    make_testing_states,
)


class OrchestratorCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = Orchestrator()

    def test_evaluate_forward_transition_reports_expected_targets(self) -> None:
        target, evidence = self.orchestrator.evaluate_forward_transition(
            make_requirements_ready_states(),
            Stage.INIT,
        )
        self.assertEqual(target, Stage.REQUIREMENTS)
        self.assertTrue(evidence)

        target, evidence = self.orchestrator.evaluate_forward_transition(
            make_solution_ready_states(),
            Stage.REQUIREMENTS,
        )
        self.assertEqual(target, Stage.SOLUTION)
        self.assertTrue(evidence)

        target, _ = self.orchestrator.evaluate_forward_transition(
            make_design_ready_states(),
            Stage.SOLUTION,
        )
        self.assertEqual(target, Stage.DESIGN)

        target, _ = self.orchestrator.evaluate_forward_transition(
            make_implementing_states(),
            Stage.DESIGN,
        )
        self.assertEqual(target, Stage.IMPLEMENTATION)

        target, _ = self.orchestrator.evaluate_forward_transition(
            make_testing_states(),
            Stage.TESTING,
        )
        self.assertIsNone(target)

        target, _ = self.orchestrator.evaluate_forward_transition(
            make_done_states(),
            Stage.TESTING,
        )
        self.assertEqual(target, Stage.DONE)

    def test_determine_execution_stage_respects_wait_backflow_forward_and_bootstrap(
        self,
    ) -> None:
        self.assertIsNone(
            self.orchestrator.determine_execution_stage(
                TransitionDecision(
                    computed_stage=Stage.REQUIREMENTS,
                    final_stage=Stage.REQUIREMENTS,
                    wait_for_user_input=True,
                    should_stay=True,
                    reason="Waiting for user input.",
                )
            )
        )

        self.assertEqual(
            self.orchestrator.determine_execution_stage(
                TransitionDecision(
                    computed_stage=Stage.TESTING,
                    final_stage=Stage.DESIGN,
                    backflow_target=Stage.DESIGN,
                    should_stay=False,
                    reason="Backflow triggered.",
                )
            ),
            Stage.DESIGN,
        )

        self.assertEqual(
            self.orchestrator.determine_execution_stage(
                TransitionDecision(
                    computed_stage=Stage.REQUIREMENTS,
                    final_stage=Stage.SOLUTION,
                    forward_target=Stage.SOLUTION,
                    should_stay=False,
                    reason="Forward transition available.",
                )
            ),
            Stage.SOLUTION,
        )

        self.assertEqual(
            self.orchestrator.determine_execution_stage(
                TransitionDecision(
                    computed_stage=Stage.INIT,
                    final_stage=Stage.INIT,
                    should_stay=True,
                    reason="Stay on current stage.",
                )
            ),
            Stage.REQUIREMENTS,
        )

    def test_build_result_summary_handles_wait_execution_and_noop_paths(self) -> None:
        wait_summary = self.orchestrator.build_result_summary(
            decision=TransitionDecision(
                computed_stage=Stage.REQUIREMENTS,
                final_stage=Stage.REQUIREMENTS,
                wait_for_user_input=True,
                should_stay=True,
                reason="Waiting for user input.",
            )
        )
        self.assertIn("waiting for user input", wait_summary)

        execution_summary = self.orchestrator.build_result_summary(
            decision=TransitionDecision(
                computed_stage=Stage.REQUIREMENTS,
                final_stage=Stage.SOLUTION,
                forward_target=Stage.SOLUTION,
                should_stay=False,
                reason="Forward transition available.",
            ),
            executed_stage=Stage.SOLUTION,
            agent_result=AgentResult(
                agent_name="Solution Engineer",
                stage_name="SOLUTION",
                state_key="solution",
                updated_state=make_empty_states()["solution"],
                summary="Generated a solution.",
            ),
        )
        self.assertIn("executed SOLUTION via Solution Engineer", execution_summary)

        noop_summary = self.orchestrator.build_result_summary(
            decision=TransitionDecision(
                computed_stage=Stage.DONE,
                final_stage=Stage.DONE,
                should_stay=True,
                reason="Stay on current stage.",
            ),
            executed_stage=None,
        )
        self.assertIn("no agent execution was required", noop_summary)


if __name__ == "__main__":
    unittest.main()
