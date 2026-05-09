from __future__ import annotations

import unittest

from pydantic import ValidationError

from schemas.design import SystemDesignState
from schemas.implementation import ImplementationStatusState
from schemas.question_state import QuestionStateModel
from schemas.solution import SolutionState
from schemas.spec import SpecState
from schemas.testing import TestReportState


class StateModelsTests(unittest.TestCase):
    def test_models_support_default_construction(self) -> None:
        self.assertEqual(SpecState().project_goal, "")
        self.assertEqual(SolutionState().selected_stack.backend, "")
        self.assertEqual(SystemDesignState().project_structure.modules, [])
        self.assertEqual(ImplementationStatusState().implementation_status, "not_started")
        self.assertEqual(TestReportState().result, "not_run")
        self.assertEqual(QuestionStateModel().status, "idle")

    def test_models_accept_valid_payloads(self) -> None:
        spec = SpecState.model_validate(
            {"project_goal": "Build", "functional_requirements": ["Do X"]}
        )
        self.assertEqual(spec.project_goal, "Build")
        self.assertEqual(spec.functional_requirements, ["Do X"])

        question_state = QuestionStateModel.model_validate(
            {
                "status": "awaiting_user",
                "questions": [{"id": "q1", "title": "t", "description": "d"}],
            }
        )
        self.assertEqual(question_state.questions[0].id, "q1")

    def test_models_reject_invalid_types(self) -> None:
        with self.assertRaises(ValidationError):
            SpecState.model_validate({"project_goal": 123})
        with self.assertRaises(ValidationError):
            TestReportState.model_validate({"issues": "broken"})
        with self.assertRaises(ValidationError):
            QuestionStateModel.model_validate({"questions": "not-a-list"})


if __name__ == "__main__":
    unittest.main()
