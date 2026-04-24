from __future__ import annotations

import unittest

from agents.orchestrator import Stage
from agents.orchestrator.backflow_evaluator import BackflowEvaluator
from agents.orchestrator.stage_evaluator import StageEvaluator
from tests.unit.support.orchestrator_fixtures import (
    make_design_ready_states,
    make_empty_states,
    make_solution_ready_states,
    make_testing_states,
)


class BackflowEvaluatorTests(unittest.TestCase):
    def setUp(self) -> None:
        stage_evaluator = StageEvaluator()
        self.evaluator = BackflowEvaluator(
            is_requirements_ready=stage_evaluator.is_requirements_ready,
            is_solution_ready=stage_evaluator.is_solution_ready,
        )

    def test_testing_partial_without_issue_attribution_stays_put(self) -> None:
        states = make_testing_states()
        states["test_report"].update({"result": "partial", "issues": []})

        target, evidence = self.evaluator.evaluate(states, Stage.TESTING)

        self.assertIsNone(target)
        self.assertTrue(evidence)

    def test_testing_failure_routes_to_requirements_for_acceptance_instability(
        self,
    ) -> None:
        states = make_testing_states()
        states["test_report"].update(
            {
                "result": "fail",
                "issues": [
                    {
                        "title": "Acceptance criteria mismatch",
                        "severity": "critical",
                        "status": "open",
                        "related_modules": ["orchestrator"],
                        "related_contracts": [],
                        "notes": "Requirement scope is unclear.",
                    }
                ],
            }
        )

        target, _ = self.evaluator.evaluate(states, Stage.TESTING)

        self.assertEqual(target, Stage.REQUIREMENTS)

    def test_testing_failure_routes_to_design_for_contract_breakage(self) -> None:
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
                        "related_contracts": ["handoff"],
                        "notes": "Producer and consumer disagree on schema.",
                    }
                ],
            }
        )

        target, _ = self.evaluator.evaluate(states, Stage.TESTING)

        self.assertEqual(target, Stage.DESIGN)

    def test_testing_failure_routes_to_solution_for_multi_module_ownership_break(
        self,
    ) -> None:
        states = make_testing_states()
        states["test_report"].update(
            {
                "result": "fail",
                "issues": [
                    {
                        "title": "Module ownership is unclear",
                        "severity": "high",
                        "status": "open",
                        "related_modules": ["orchestrator", "state_manager"],
                        "related_contracts": [],
                        "notes": "Architecture ownership remains ambiguous.",
                    }
                ],
            }
        )

        target, _ = self.evaluator.evaluate(states, Stage.TESTING)

        self.assertEqual(target, Stage.SOLUTION)

    def test_testing_failure_routes_to_implementation_for_module_local_defects(
        self,
    ) -> None:
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
                        "notes": "",
                    }
                ],
            }
        )

        target, _ = self.evaluator.evaluate(states, Stage.TESTING)

        self.assertEqual(target, Stage.IMPLEMENTATION)

    def test_implementation_blocked_without_blockers_does_not_backflow(self) -> None:
        states = make_design_ready_states()
        states["implementation_status"].update(
            {
                "module_name": "orchestrator",
                "implementation_status": "blocked",
                "blockers": [],
            }
        )

        target, evidence = self.evaluator.evaluate(states, Stage.IMPLEMENTATION)

        self.assertIsNone(target)
        self.assertEqual(evidence, [])

    def test_implementation_execution_blocker_stays_on_implementation(self) -> None:
        states = make_design_ready_states()
        states["implementation_status"].update(
            {
                "module_name": "orchestrator",
                "implementation_status": "blocked",
                "blockers": ["Local dependency install fails in sandbox."],
            }
        )

        target, evidence = self.evaluator.evaluate(states, Stage.IMPLEMENTATION)

        self.assertIsNone(target)
        self.assertTrue(evidence)

    def test_implementation_requirements_blocker_backflows_to_requirements(self) -> None:
        states = make_design_ready_states()
        states["implementation_status"].update(
            {
                "module_name": "orchestrator",
                "implementation_status": "blocked",
                "blockers": ["Acceptance criteria are unclear for this flow."],
            }
        )
        states["spec"]["acceptance_criteria"] = []

        target, _ = self.evaluator.evaluate(states, Stage.IMPLEMENTATION)

        self.assertEqual(target, Stage.REQUIREMENTS)

    def test_implementation_solution_blocker_backflows_to_solution(self) -> None:
        states = make_design_ready_states()
        states["implementation_status"].update(
            {
                "module_name": "orchestrator",
                "implementation_status": "blocked",
                "blockers": ["Module responsibility and ownership are unclear."],
            }
        )

        target, _ = self.evaluator.evaluate(states, Stage.IMPLEMENTATION)

        self.assertEqual(target, Stage.SOLUTION)

    def test_implementation_design_blocker_backflows_to_design(self) -> None:
        states = make_design_ready_states()
        states["implementation_status"].update(
            {
                "module_name": "orchestrator",
                "implementation_status": "blocked",
                "blockers": ["Schema boundary is inconsistent."],
                "contract_compliance": False,
            }
        )

        target, _ = self.evaluator.evaluate(states, Stage.IMPLEMENTATION)

        self.assertEqual(target, Stage.DESIGN)

    def test_design_stage_backflows_to_solution_or_requirements_when_support_breaks(
        self,
    ) -> None:
        states = make_design_ready_states()
        states["solution"]["module_mapping"] = []
        target, _ = self.evaluator.evaluate(states, Stage.DESIGN)
        self.assertEqual(target, Stage.SOLUTION)

        states = make_empty_states()
        states["system_design"]["contracts"] = [{"name": "handoff"}]
        target, _ = self.evaluator.evaluate(states, Stage.DESIGN)
        self.assertEqual(target, Stage.REQUIREMENTS)

    def test_solution_stage_backflows_to_requirements_when_requirements_break(
        self,
    ) -> None:
        states = make_solution_ready_states()
        states["spec"]["functional_requirements"] = []

        target, _ = self.evaluator.evaluate(states, Stage.SOLUTION)

        self.assertEqual(target, Stage.REQUIREMENTS)


if __name__ == "__main__":
    unittest.main()
