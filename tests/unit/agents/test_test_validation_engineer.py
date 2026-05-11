from __future__ import annotations

import unittest

from agents.test_validation_engineer.planning import TestValidationPlanningMixin
from tests.unit.support.orchestrator_fixtures import make_testing_states


class _Harness(TestValidationPlanningMixin):
    pass


class TestValidationPlanningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = _Harness()

    def test_build_issues_marks_contract_output_gap_when_tests_missing(self) -> None:
        states = make_testing_states()
        states["implementation_status"]["tests_added_or_updated"] = []
        issues = self.planner.build_issues(
            spec=states["spec"],
            implementation_status=states["implementation_status"],
            design=states["system_design"],
        )
        target = next(
            issue
            for issue in issues
            if issue["title"] == "No tests recorded for contract validation"
        )
        self.assertTrue(target["related_contracts"])
        self.assertIn("attribution=contract", target["notes"])
        self.assertIn("error_category=output_errors", target["notes"])

    def test_build_issues_marks_structure_mismatch_with_processing_category(self) -> None:
        states = make_testing_states()
        states["implementation_status"]["module_name"] = "unknown_module"
        issues = self.planner.build_issues(
            spec=states["spec"],
            implementation_status=states["implementation_status"],
            design=states["system_design"],
        )
        target = next(
            issue
            for issue in issues
            if issue["title"] == "Implementation module is outside design structure"
        )
        self.assertIn("attribution=structure", target["notes"])
        self.assertIn("error_category=processing_errors", target["notes"])

    def test_build_issues_marks_input_error_for_open_questions(self) -> None:
        states = make_testing_states()
        states["spec"]["open_questions"] = ["Confirm accepted markdown dialect."]
        issues = self.planner.build_issues(
            spec=states["spec"],
            implementation_status=states["implementation_status"],
            design=states["system_design"],
        )
        target = next(
            issue for issue in issues if issue["title"] == "Requirements remain unresolved"
        )
        self.assertIn("attribution=contract", target["notes"])
        self.assertIn("error_category=input_errors", target["notes"])


if __name__ == "__main__":
    unittest.main()
