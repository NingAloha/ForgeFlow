from __future__ import annotations

import unittest

from pydantic import ValidationError

from schemas.llm_trace import EMPTY_LLM_TRACE, LLMTraceModel


class LLMTraceModelTests(unittest.TestCase):
    def test_model_accepts_valid_payload(self) -> None:
        payload = {
            "status": "success",
            "failure_type": "none",
            "repair_attempts": 0,
            "validation_errors": [],
            "raw_excerpt": '{"ok": true}',
            "model": "deepseek-v4-flash",
            "provider": "deepseek",
            "protocol": "openai",
            "latency_ms": 15,
            "error": None,
        }
        model = LLMTraceModel.model_validate(payload)
        self.assertEqual(model.status, "success")
        self.assertIsNone(model.error)

    def test_model_rejects_unknown_field(self) -> None:
        with self.assertRaises(ValidationError):
            LLMTraceModel.model_validate({
                "status": "success",
                "failure_type": "none",
                "repair_attempts": 0,
                "validation_errors": [],
                "raw_excerpt": "",
                "model": "",
                "provider": "",
                "protocol": "",
                "latency_ms": 0,
                "error": None,
                "extra": True,
            })

    def test_model_rejects_invalid_status(self) -> None:
        with self.assertRaises(ValidationError):
            LLMTraceModel.model_validate({
                "status": "invalid",
                "failure_type": "none",
                "repair_attempts": 0,
                "validation_errors": [],
                "raw_excerpt": "",
                "model": "",
                "provider": "",
                "protocol": "",
                "latency_ms": 0,
                "error": None,
            })

    def test_model_rejects_invalid_type(self) -> None:
        with self.assertRaises(ValidationError):
            LLMTraceModel.model_validate({
                "status": "success",
                "failure_type": "none",
                "repair_attempts": "0",
                "validation_errors": [],
                "raw_excerpt": "",
                "model": "",
                "provider": "",
                "protocol": "",
                "latency_ms": 0,
                "error": None,
            })

    def test_empty_trace_constant_is_stable_via_dump(self) -> None:
        self.assertEqual(
            EMPTY_LLM_TRACE.model_dump(mode="python"),
            {
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
        )


if __name__ == "__main__":
    unittest.main()
