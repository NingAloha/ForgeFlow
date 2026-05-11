from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import BaseModel

from agents.orchestrator import Orchestrator, Stage
from tests.unit.support.fake_pipeline_agents import (
    FakeDesignAgent,
    FakeImplementationAgent,
    FakeRequirementsAgent,
    FakeSolutionAgent,
    FakeTestingAgent,
)


class StageTraceStepModel(BaseModel):
    computed_stage: str
    final_stage: str
    decision_type: str | None = None
    executed_stage: str | None = None
    reason: str | None = None


class StageTraceModel(BaseModel):
    trace: list[StageTraceStepModel]


class ExpectedMinimalStateModel(BaseModel):
    required: dict[str, list[str]]
    expected_values: dict[str, str]


class ExampleGoldenRegressionTests(unittest.TestCase):
    SCENARIOS = [
        "todo_cli",
        "simple_blog_generator",
        "markdown_summarizer",
        "json_validator",
        "tiny_rest_api_plan",
    ]

    def _scenario_dir(self, scenario: str) -> Path:
        return Path("examples") / scenario

    def _load_json(self, path: Path) -> dict:
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertIsInstance(payload, dict)
        return payload

    def _build_fake_orchestrator(self, state_dir: str) -> Orchestrator:
        orchestrator = Orchestrator()
        orchestrator.state_manager.state_dir = Path(state_dir)
        orchestrator.agents = {
            Stage.REQUIREMENTS: FakeRequirementsAgent(),
            Stage.SOLUTION: FakeSolutionAgent(),
            Stage.DESIGN: FakeDesignAgent(),
            Stage.IMPLEMENTATION: FakeImplementationAgent(),
            Stage.TESTING: FakeTestingAgent(),
        }
        return orchestrator

    def _collect_trace(self, orchestrator: Orchestrator, user_input: str) -> list[dict[str, str]]:
        trace: list[dict[str, str]] = []
        for step in range(1, 12):
            step_input = user_input if step == 1 else ""
            result = orchestrator.orchestrate(step_input, original_request=user_input)
            diag = result.diagnostic
            stages = diag.get("stages", {})
            transition = diag.get("transition", {})
            trace.append(
                {
                    "decision_type": str(diag.get("decision_type", "")),
                    "computed_stage": str(stages.get("computed", "")),
                    "final_stage": str(stages.get("final", "")),
                    "executed_stage": str(stages.get("executed", "")),
                    "reason": str(transition.get("reason", "")),
                }
            )
            if result.decision.wait_for_user_input or result.decision.final_stage == Stage.DONE:
                break
        return trace

    def _lookup(self, payload: dict, dotted_key: str):
        current = payload
        for segment in dotted_key.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(segment)
        return current

    def test_example_directories_have_required_assets(self) -> None:
        for scenario in self.SCENARIOS:
            with self.subTest(scenario=scenario):
                root = self._scenario_dir(scenario)
                self.assertTrue((root / "input.md").exists())
                self.assertTrue((root / "expected_stage_trace.json").exists())
                self.assertTrue((root / "expected_state_minimal.json").exists())
                self.assertTrue((root / "notes.md").exists())

    def test_offline_goldens_do_not_invoke_real_llm_and_match_key_trace(self) -> None:
        for scenario in self.SCENARIOS:
            with self.subTest(scenario=scenario):
                root = self._scenario_dir(scenario)
                expected_trace = StageTraceModel.model_validate(
                    self._load_json(root / "expected_stage_trace.json")
                )
                expected_state = ExpectedMinimalStateModel.model_validate(
                    self._load_json(root / "expected_state_minimal.json")
                )
                user_input = (root / "input.md").read_text(encoding="utf-8").strip()

                with tempfile.TemporaryDirectory() as tmp_dir:
                    orchestrator = self._build_fake_orchestrator(tmp_dir)
                    with patch(
                        "agents.common.llm_gateway.LLMGateway.generate",
                        side_effect=AssertionError("real LLM gateway call is forbidden in offline golden regression"),
                    ) as llm_generate, patch(
                        "agents.common.llm_adapter.LLMAdapter.generate_text",
                        side_effect=AssertionError("real LLM adapter call is forbidden in offline golden regression"),
                    ) as llm_adapter_generate:
                        trace = self._collect_trace(orchestrator, user_input)
                        self.assertEqual(llm_generate.call_count, 0)
                        self.assertEqual(llm_adapter_generate.call_count, 0)

                    # Validate the core stage progression, not full diagnostics byte-equality.
                    expected_pairs = [
                        (item.computed_stage, item.final_stage) for item in expected_trace.trace
                    ]
                    observed_pairs = [
                        (item["computed_stage"], item["final_stage"]) for item in trace
                    ]
                    self.assertEqual(observed_pairs, expected_pairs)
                    for step in trace:
                        self.assertTrue(step.get("reason"))
                        self.assertTrue(step.get("decision_type"))

                    final_states = orchestrator.state_manager.load_all_states()
                    required_map = expected_state.required
                    for state_key, required_fields in required_map.items():
                        self.assertIn(state_key, final_states)
                        state_payload = final_states[state_key]
                        self.assertIsInstance(state_payload, dict)
                        for field in required_fields:
                            self.assertIn(field, state_payload)

                    for key, value in expected_state.expected_values.items():
                        self.assertEqual(self._lookup(final_states, key), value)
