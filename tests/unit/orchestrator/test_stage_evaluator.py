from __future__ import annotations

import unittest

from agents.orchestrator import Stage, StageFlags
from agents.orchestrator.stage_evaluator import StageEvaluator
from tests.unit.support.orchestrator_fixtures import (
    make_design_ready_states,
    make_done_states,
    make_empty_states,
    make_requirements_ready_states,
    make_solution_ready_states,
    make_testing_states,
)


class StageEvaluatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.evaluator = StageEvaluator()

    def test_is_requirements_ready_requires_all_core_spec_fields(self) -> None:
        states = make_requirements_ready_states()
        self.assertTrue(self.evaluator.is_requirements_ready(states))

        states["spec"]["acceptance_criteria"] = []
        self.assertFalse(self.evaluator.is_requirements_ready(states))

    def test_is_solution_ready_requires_backend_stable_modules_and_requirement_coverage(
        self,
    ) -> None:
        states = make_solution_ready_states()
        self.assertTrue(self.evaluator.is_solution_ready(states))

        states["solution"]["selected_stack"]["backend"] = ""
        self.assertFalse(self.evaluator.is_solution_ready(states))

        states = make_solution_ready_states()
        states["solution"]["module_mapping"][0]["covers_requirements"] = []
        self.assertFalse(self.evaluator.is_solution_ready(states))

    def test_is_design_ready_rejects_data_flow_without_valid_contract(self) -> None:
        states = make_design_ready_states()
        self.assertTrue(self.evaluator.is_design_ready(states))

        states["system_design"]["data_flow"][0]["contract_name"] = "missing"
        self.assertFalse(self.evaluator.is_design_ready(states))

    def test_has_active_implementation_allows_active_statuses_only_after_design_ready(
        self,
    ) -> None:
        states = make_design_ready_states()
        states["implementation_status"].update(
            {"module_name": "orchestrator", "implementation_status": "blocked"}
        )
        self.assertTrue(self.evaluator.has_active_implementation(states))

        states = make_empty_states()
        states["implementation_status"].update(
            {"module_name": "orchestrator", "implementation_status": "in_progress"}
        )
        self.assertFalse(self.evaluator.has_active_implementation(states))

    def test_has_validation_context_requires_done_status_no_blockers_and_scope(
        self,
    ) -> None:
        states = make_testing_states()
        self.assertTrue(self.evaluator.has_validation_context(states))

        states["implementation_status"]["blockers"] = ["Need API clarification"]
        self.assertFalse(self.evaluator.has_validation_context(states))

    def test_is_done_rejects_high_severity_open_issues_even_when_result_passes(
        self,
    ) -> None:
        states = make_done_states()
        self.assertTrue(self.evaluator.is_done(states))

        states["test_report"]["issues"].append(
            {
                "title": "Critical regression",
                "severity": "critical",
                "status": "confirmed",
                "related_modules": ["orchestrator"],
                "related_contracts": [],
                "notes": "",
            }
        )
        self.assertFalse(self.evaluator.is_done(states))

    def test_evaluate_stage_flags_short_circuits_downstream_flags_when_upstream_breaks(
        self,
    ) -> None:
        states = make_solution_ready_states()
        states["spec"]["functional_requirements"] = []

        flags = self.evaluator.evaluate_stage_flags(states)

        self.assertEqual(
            flags,
            StageFlags(
                requirements_ready=False,
                solution_ready=False,
                design_ready=False,
                implementing_active=False,
                testing_active=False,
                done_ready=False,
            ),
        )

    def test_stage_from_flags_prefers_farthest_reached_stage(self) -> None:
        flags = StageFlags(
            requirements_ready=True,
            solution_ready=True,
            design_ready=True,
            implementing_active=True,
            testing_active=True,
            done_ready=False,
        )
        self.assertEqual(self.evaluator.stage_from_flags(flags), Stage.TESTING)

    def test_infer_source_stage_uses_residual_artifacts_when_truth_stage_regresses(
        self,
    ) -> None:
        states = make_empty_states()
        states["solution"]["selected_stack"]["backend"] = "Python"
        self.assertEqual(self.evaluator.infer_source_stage(states), Stage.SOLUTION)

        states = make_empty_states()
        states["system_design"]["contracts"] = [
            {
                "name": "handoff",
                "producer": "Requirements Engineer",
                "consumers": ["Solution Engineer"],
                "input": ["spec"],
                "output": ["solution"],
            }
        ]
        self.assertEqual(self.evaluator.infer_source_stage(states), Stage.DESIGN)

    def test_apply_backflow_to_flags_clears_only_downstream_flags(self) -> None:
        flags = StageFlags(
            requirements_ready=True,
            solution_ready=True,
            design_ready=True,
            implementing_active=True,
            testing_active=True,
            done_ready=True,
        )

        self.assertEqual(
            self.evaluator.apply_backflow_to_flags(flags, Stage.SOLUTION),
            StageFlags(
                requirements_ready=True,
                solution_ready=True,
                design_ready=False,
                implementing_active=False,
                testing_active=False,
                done_ready=False,
            ),
        )
        self.assertEqual(
            self.evaluator.apply_backflow_to_flags(flags, Stage.IMPLEMENTATION),
            StageFlags(
                requirements_ready=True,
                solution_ready=True,
                design_ready=True,
                implementing_active=True,
                testing_active=False,
                done_ready=False,
            ),
        )


if __name__ == "__main__":
    unittest.main()
