from __future__ import annotations

import unittest

from pydantic import ValidationError

from schemas.llm_trace import LLMTraceModel
from schemas.run_summary import RunSummaryModel


class RunSummaryModelsTests(unittest.TestCase):
    def test_model_accepts_minimal_valid_payload(self) -> None:
        payload = {
            "schema_version": "1",
            "run_id": "run-1",
            "original_request": "build todo",
            "generated_project_dir": "/tmp/generated/run-1",
            "state_dir": "/tmp/state",
            "latest_summary": "ok",
            "latest_final_stage": "REQUIREMENTS",
            "latest_decision_type": "STAY",
            "steps": [
                {
                    "timestamp": "2026-05-10T00:00:00Z",
                    "input": "build todo",
                    "decision_type": "STAY",
                    "computed_stage": "REQUIREMENTS",
                    "final_stage": "REQUIREMENTS",
                    "executed_stage": "REQUIREMENTS",
                    "summary": "ok",
                    "llm_trace": {
                        "status": "none",
                        "failure_type": "none",
                        "repair_attempts": 0,
                        "validation_errors": [],
                        "raw_excerpt": "",
                        "model": "",
                        "provider": "",
                        "protocol": "",
                        "latency_ms": 0,
                        "error": None,
                    },
                    "execution_trace": {},
                    "state_changes": [],
                    "question_state": {"status": "idle"},
                }
            ],
        }
        model = RunSummaryModel.model_validate(payload)
        self.assertEqual(model.schema_version, "1")
        self.assertEqual(len(model.steps), 1)
        self.assertIsInstance(model.steps[0].llm_trace, LLMTraceModel)

    def test_model_rejects_wrong_schema_version(self) -> None:
        with self.assertRaises(ValidationError):
            RunSummaryModel.model_validate({
                "schema_version": "2",
                "run_id": "run-1",
                "original_request": "",
                "generated_project_dir": "",
                "state_dir": "",
                "latest_summary": "",
                "latest_final_stage": "",
                "latest_decision_type": "",
                "steps": [],
            })

    def test_model_rejects_unknown_field(self) -> None:
        with self.assertRaises(ValidationError):
            RunSummaryModel.model_validate({
                "schema_version": "1",
                "run_id": "run-1",
                "original_request": "",
                "generated_project_dir": "",
                "state_dir": "",
                "latest_summary": "",
                "latest_final_stage": "",
                "latest_decision_type": "",
                "steps": [],
                "extra_field": True,
            })

    def test_model_rejects_invalid_field_type(self) -> None:
        with self.assertRaises(ValidationError):
            RunSummaryModel.model_validate({
                "schema_version": "1",
                "run_id": "run-1",
                "original_request": "",
                "generated_project_dir": "",
                "state_dir": "",
                "latest_summary": "",
                "latest_final_stage": "",
                "latest_decision_type": "",
                "steps": "not-a-list",
            })

    def test_model_rejects_empty_dict_llm_trace(self) -> None:
        with self.assertRaises(ValidationError):
            RunSummaryModel.model_validate({
                "schema_version": "1",
                "run_id": "run-1",
                "original_request": "build todo",
                "generated_project_dir": "/tmp/generated/run-1",
                "state_dir": "/tmp/state",
                "latest_summary": "ok",
                "latest_final_stage": "REQUIREMENTS",
                "latest_decision_type": "STAY",
                "steps": [
                    {
                        "timestamp": "2026-05-10T00:00:00Z",
                        "input": "build todo",
                        "decision_type": "STAY",
                        "computed_stage": "REQUIREMENTS",
                        "final_stage": "REQUIREMENTS",
                        "executed_stage": "REQUIREMENTS",
                        "summary": "ok",
                        "llm_trace": {},
                        "execution_trace": {},
                        "state_changes": [],
                        "question_state": {"status": "idle"},
                    }
                ],
            })


if __name__ == "__main__":
    unittest.main()
