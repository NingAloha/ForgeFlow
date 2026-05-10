from __future__ import annotations

import unittest

from pydantic import BaseModel

from agents.common.llm_adapter import LLMCallResult
from agents.common.llm_gateway import LLMGateway, PromptContract
from agents.common.runtime_config import LLMRuntimeConfig


class _FakeAdapter:
    def __init__(self, responses: list[LLMCallResult]) -> None:
        self.responses = responses
        self.calls = 0

    def generate_text(self, system_prompt: str, user_prompt: str, config: LLMRuntimeConfig) -> LLMCallResult:
        self.calls += 1
        if self.responses:
            return self.responses.pop(0)
        return LLMCallResult(ok=False, content={}, error="timeout")


class _SimpleModel(BaseModel):
    project_goal: str


class LLMGatewayTests(unittest.TestCase):
    def test_valid_json_success(self) -> None:
        gateway = LLMGateway(
            adapter=_FakeAdapter(
                [LLMCallResult(ok=True, content={}, raw_output='{"project_goal":"x"}')]
            )
        )
        result = gateway.generate(
            PromptContract(
                stage_name="REQUIREMENTS",
                system_prompt="x",
                required_fields=["project_goal"],
                output_model=_SimpleModel,
            ),
            "build",
            LLMRuntimeConfig(enabled=True),
        )
        self.assertEqual(result.status, "success")
        self.assertEqual(result.parsed_output, {"project_goal": "x"})

    def test_fenced_json_extraction(self) -> None:
        gateway = LLMGateway(
            adapter=_FakeAdapter(
                [LLMCallResult(ok=True, content={}, raw_output='```json\n{"project_goal":"x"}\n```')]
            )
        )
        result = gateway.generate(
            PromptContract(stage_name="REQUIREMENTS", system_prompt="x", required_fields=["project_goal"]),
            "build",
            LLMRuntimeConfig(enabled=True, retry_policy_by_stage={"REQUIREMENTS": 0}),
        )
        self.assertEqual(result.status, "success")

    def test_invalid_json_classification(self) -> None:
        gateway = LLMGateway(
            adapter=_FakeAdapter([LLMCallResult(ok=True, content={}, raw_output='{"project_goal": }')])
        )
        result = gateway.generate(
            PromptContract(stage_name="REQUIREMENTS", system_prompt="x", required_fields=["project_goal"]),
            "build",
            LLMRuntimeConfig(
                enabled=True,
                max_repair_attempts=0,
                retry_policy_by_stage={"REQUIREMENTS": 0},
            ),
        )
        self.assertEqual(result.status, "retryable_error")
        self.assertEqual(result.failure_type, "invalid_json")

    def test_schema_error_classification(self) -> None:
        gateway = LLMGateway(
            adapter=_FakeAdapter([LLMCallResult(ok=True, content={}, raw_output='{"x":"y"}')])
        )
        result = gateway.generate(
            PromptContract(stage_name="REQUIREMENTS", system_prompt="x", required_fields=["project_goal"]),
            "build",
            LLMRuntimeConfig(enabled=True, retry_policy_by_stage={"REQUIREMENTS": 0}),
        )
        self.assertEqual(result.status, "retryable_error")
        self.assertEqual(result.failure_type, "schema_error")

    def test_unknown_field_rejection_with_allowed_fields(self) -> None:
        gateway = LLMGateway(
            adapter=_FakeAdapter([LLMCallResult(ok=True, content={}, raw_output='{"project_goal":"x","extra":"z"}')])
        )
        result = gateway.generate(
            PromptContract(
                stage_name="REQUIREMENTS",
                system_prompt="x",
                required_fields=["project_goal"],
                output_model=None,
                allowed_fields=["project_goal"],
            ),
            "build",
            LLMRuntimeConfig(
                enabled=True,
                strict_unknown_fields=True,
                retry_policy_by_stage={"REQUIREMENTS": 0},
            ),
        )
        self.assertEqual(result.status, "retryable_error")
        self.assertEqual(result.failure_type, "schema_error")

    def test_output_model_none_allows_unknown_fields_when_no_allowed_fields(self) -> None:
        gateway = LLMGateway(
            adapter=_FakeAdapter([LLMCallResult(ok=True, content={}, raw_output='{"project_goal":"x","extra":"z"}')])
        )
        result = gateway.generate(
            PromptContract(stage_name="REQUIREMENTS", system_prompt="x", required_fields=["project_goal"], output_model=None),
            "build",
            LLMRuntimeConfig(enabled=True, strict_unknown_fields=True),
        )
        self.assertEqual(result.status, "success")

    def test_retry_only_on_retryable_error(self) -> None:
        adapter = _FakeAdapter(
            [
                LLMCallResult(ok=False, content={}, error="timeout"),
                LLMCallResult(ok=True, content={}, raw_output='{"project_goal":"x"}'),
            ]
        )
        gateway = LLMGateway(adapter=adapter)
        result = gateway.generate(
            PromptContract(stage_name="REQUIREMENTS", system_prompt="x", required_fields=["project_goal"]),
            "build",
            LLMRuntimeConfig(enabled=True, retry_policy_by_stage={"REQUIREMENTS": 1}),
        )
        self.assertEqual(result.status, "success")
        self.assertEqual(adapter.calls, 2)

    def test_schema_error_then_success_retries_and_recovers(self) -> None:
        adapter = _FakeAdapter(
            [
                LLMCallResult(ok=True, content={}, raw_output='{"unexpected":"x"}'),
                LLMCallResult(ok=True, content={}, raw_output='{"project_goal":"x"}'),
            ]
        )
        gateway = LLMGateway(adapter=adapter)
        result = gateway.generate(
            PromptContract(stage_name="REQUIREMENTS", system_prompt="x", required_fields=["project_goal"]),
            "build",
            LLMRuntimeConfig(enabled=True, retry_policy_by_stage={"REQUIREMENTS": 1}),
        )
        self.assertEqual(result.status, "success")
        self.assertEqual(adapter.calls, 2)

    def test_fatal_error_no_retry(self) -> None:
        adapter = _FakeAdapter(
            [
                LLMCallResult(ok=False, content={}, error="401 unauthorized"),
                LLMCallResult(ok=True, content={}, raw_output='{"project_goal":"x"}'),
            ]
        )
        gateway = LLMGateway(adapter=adapter)
        result = gateway.generate(
            PromptContract(stage_name="REQUIREMENTS", system_prompt="x", required_fields=["project_goal"]),
            "build",
            LLMRuntimeConfig(enabled=True, retry_policy_by_stage={"REQUIREMENTS": 2}),
        )
        self.assertEqual(result.status, "fatal_error")
        self.assertEqual(adapter.calls, 1)


if __name__ == "__main__":
    unittest.main()
