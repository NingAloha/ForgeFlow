from __future__ import annotations

import unittest

from agents.orchestrator import Orchestrator, Stage
from tests.unit.support.orchestrator_fixtures import (
    make_design_ready_states,
    make_requirements_ready_states,
    make_solution_ready_states,
    make_testing_states,
)


class OrchestratorRegressionDecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = Orchestrator()

    def test_spec_missing_core_fields_results_in_wait_and_question(self) -> None:
        states = make_requirements_ready_states()
        states["spec"]["acceptance_criteria"] = []
        states["question_state"] = {
            "status": "awaiting_user",
            "stage_name": "REQUIREMENTS",
            "state_key": "spec",
            "blocking": True,
            "questions": [{"id": "acceptance_criteria"}],
            "created_by": "Requirements Engineer",
            "resolution_summary": "",
        }
        decision = self.orchestrator.resolve_transition(states)
        self.assertTrue(decision.wait_for_user_input)
        self.assertEqual(decision.final_stage, Stage.REQUIREMENTS)
        self.assertIn("awaiting user", " ".join(decision.evidence).lower())

    def test_question_state_answered_retries_requirements(self) -> None:
        states = make_requirements_ready_states()
        states["question_state"] = {
            "status": "answered",
            "stage_name": "REQUIREMENTS",
            "state_key": "spec",
            "blocking": True,
            "questions": [{"id": "scope"}],
            "created_by": "Requirements Engineer",
            "resolution_summary": "answered",
        }

        decision = self.orchestrator.resolve_transition(states)

        self.assertTrue(decision.should_stay)
        self.assertFalse(decision.wait_for_user_input)
        self.assertEqual(decision.final_stage, Stage.REQUIREMENTS)
        self.assertEqual(self.orchestrator.determine_execution_stage(decision), Stage.REQUIREMENTS)

    def test_solution_complete_forwards_to_design(self) -> None:
        states = make_solution_ready_states()
        decision = self.orchestrator.resolve_transition(states)

        self.assertEqual(decision.next_stage_to_execute, Stage.DESIGN)
        self.assertEqual(decision.final_stage, Stage.DESIGN)
        self.assertFalse(decision.should_stay)

    def test_design_contract_missing_stays_or_retries_design(self) -> None:
        states = make_design_ready_states()
        states["system_design"]["contracts"] = []

        decision = self.orchestrator.resolve_transition(states)

        self.assertIn(decision.final_stage, {Stage.SOLUTION, Stage.DESIGN})
        if decision.backflow_target is not None:
            self.assertEqual(decision.backflow_target, Stage.SOLUTION)

    def test_testing_contract_issue_rolls_back_to_design(self) -> None:
        states = make_testing_states()
        states["test_report"].update(
            {
                "result": "fail",
                "issues": [
                    {
                        "title": "Contract mismatch",
                        "severity": "critical",
                        "status": "confirmed",
                        "related_modules": ["orchestrator", "state_manager"],
                        "related_contracts": ["requirements_to_solution_state"],
                        "notes": "contract drift",
                    }
                ],
            }
        )

        decision = self.orchestrator.resolve_transition(states)
        self.assertEqual(decision.backflow_target, Stage.DESIGN)
        self.assertEqual(decision.final_stage, Stage.DESIGN)

    def test_testing_implementation_issue_rolls_back_to_implementation(self) -> None:
        states = make_testing_states()
        states["test_report"].update(
            {
                "result": "fail",
                "issues": [
                    {
                        "title": "Local logic broken",
                        "severity": "high",
                        "status": "open",
                        "related_modules": ["orchestrator"],
                        "related_contracts": [],
                        "notes": "module local defect",
                    }
                ],
            }
        )

        decision = self.orchestrator.resolve_transition(states)
        self.assertEqual(decision.backflow_target, Stage.IMPLEMENTATION)
        self.assertEqual(decision.final_stage, Stage.IMPLEMENTATION)

    def test_diagnostic_payload_contains_decision_and_question_summary_fields(self) -> None:
        states = make_solution_ready_states()
        decision = self.orchestrator.resolve_transition(states)
        payload = self.orchestrator.build_diagnostic_payload(
            decision=decision,
            states_before=states,
            states_after=states,
            executed_stage=Stage.DESIGN,
            summary="diagnostic",
        )
        self.assertIn(payload["decision_type"], {"FORWARD", "BACKFLOW", "WAIT", "STAY", "EXECUTE", "BOOTSTRAP"})
        self.assertIn("computed", payload["stages"])
        self.assertIn("final", payload["stages"])
        self.assertIn("executed", payload["stages"])
        self.assertIn("status", payload["question_state"])
