from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from agents.base import AgentContext
from agents.common.llm_gateway import LLMStructuredResult
from agents.common.runtime_config import LLMRuntimeConfig
from agents.orchestrator import Orchestrator, Stage
from agents.requirements_engineer import RequirementsEngineerAgent
from agents.test_validation_engineer import TestValidationEngineerAgent
from schemas.llm_trace import LLMTraceModel
from tests.unit.support.orchestrator_fixtures import make_empty_states, make_testing_states
from tests.unit.support.orchestrator_stubs import InMemoryStateManager


class LLMTraceContractTests(unittest.TestCase):
    def test_to_trace_contains_expected_field_contract(self) -> None:
        result = LLMStructuredResult(
            status="success",
            parsed_output={"ok": True},
            validation_errors=[],
            raw_output='{"ok": true}',
            repair_attempts=1,
            confidence=None,
            failure_type="none",
            model="m",
            provider="p",
            protocol="openai",
            latency_ms=7,
            error="",
        )
        trace = result.to_trace()
        self.assertIsInstance(trace, LLMTraceModel)
        trace_dict = trace.model_dump(mode="python")
        expected_keys = {
            "status",
            "failure_type",
            "repair_attempts",
            "validation_errors",
            "raw_excerpt",
            "model",
            "provider",
            "protocol",
            "latency_ms",
            "error",
        }
        self.assertTrue(expected_keys.issubset(set(trace_dict.keys())))

    def test_to_trace_raw_excerpt_is_truncated(self) -> None:
        raw = "x" * 2000
        result = LLMStructuredResult(
            status="retryable_error",
            parsed_output=None,
            validation_errors=["bad"],
            raw_output=raw,
            repair_attempts=0,
            confidence=None,
            failure_type="invalid_json",
            model="m",
            provider="p",
            protocol="openai",
            latency_ms=9,
            error="invalid",
        )
        trace = result.to_trace()
        self.assertEqual(len(trace.raw_excerpt), 800)
        self.assertEqual(trace.raw_excerpt, "x" * 800)

    def test_stage_agents_do_not_reintroduce_legacy_llm_trace_flags(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        stage_agent_paths = [
            repo_root / "agents" / "requirements_engineer" / "agent.py",
            repo_root / "agents" / "solution_engineer" / "agent.py",
            repo_root / "agents" / "system_designer" / "agent.py",
            repo_root / "agents" / "implementation_engineer" / "agent.py",
            repo_root / "agents" / "test_validation_engineer" / "agent.py",
        ]

        forbidden_legacy_flag = "fallback_used"
        # Only flag enabled/used when they are attached to llm_trace semantics.
        llm_trace_legacy_patterns = [
            re.compile(r"llm_trace[^\n]{0,160}\bused\b"),
            re.compile(r"llm_trace[^\n]{0,160}\benabled\b"),
            re.compile(r"llm_trace[^\n]{0,160}\bfallback_used\b"),
        ]

        for path in stage_agent_paths:
            content = path.read_text(encoding="utf-8")
            self.assertNotIn(
                forbidden_legacy_flag,
                content,
                f"{path} contains forbidden token: {forbidden_legacy_flag}",
            )
            for pattern in llm_trace_legacy_patterns:
                self.assertIsNone(
                    pattern.search(content),
                    f"{path} matches forbidden llm_trace legacy pattern: {pattern.pattern}",
                )

    def test_orchestrator_diagnostic_uses_gateway_trace_for_requirements_agent(self) -> None:
        llm_result = LLMStructuredResult(
            status="success",
            parsed_output={
                "project_goal": "Build todo app",
                "functional_requirements": ["Create tasks"],
                "acceptance_criteria": ["User can create tasks"],
            },
            validation_errors=[],
            raw_output='{"project_goal":"Build todo app"}',
            repair_attempts=0,
            confidence=None,
            failure_type="none",
            model="test-model",
            provider="test-provider",
            protocol="test-protocol",
            latency_ms=1,
            error=None,
        )
        sentinel_trace = llm_result.to_trace()

        class GatewayStub:
            def generate(self, contract, user_prompt, config):  # noqa: ANN001
                return llm_result

        class TestableRequirementsEngineerAgent(RequirementsEngineerAgent):
            def get_llm_runtime_config(self) -> LLMRuntimeConfig:
                return LLMRuntimeConfig(enabled=True, execution_mode="compat")

            def get_llm_gateway(self):  # type: ignore[override]
                return GatewayStub()

        state_manager = InMemoryStateManager(make_empty_states())
        orchestrator = Orchestrator(state_manager=state_manager)
        orchestrator.agents[Stage.REQUIREMENTS] = TestableRequirementsEngineerAgent()

        result = orchestrator.orchestrate("build a simple todo app")
        self.assertEqual(
            result.diagnostic["llm_trace"],
            sentinel_trace.model_dump(mode="python"),
        )

    def test_orchestrator_diagnostic_uses_gateway_trace_for_testing_agent(self) -> None:
        llm_result = LLMStructuredResult(
            status="success",
            parsed_output={
                "test_scope": "integration",
                "command": ["python3", "-m", "unittest"],
            },
            validation_errors=[],
            raw_output='{"test_scope":"integration"}',
            repair_attempts=0,
            confidence=None,
            failure_type="none",
            model="test-model",
            provider="test-provider",
            protocol="test-protocol",
            latency_ms=1,
            error=None,
        )
        sentinel_trace = llm_result.to_trace()

        class GatewayStub:
            def generate(self, contract, user_prompt, config):  # noqa: ANN001
                return llm_result

        class TestableValidationAgent(TestValidationEngineerAgent):
            def get_llm_runtime_config(self) -> LLMRuntimeConfig:
                return LLMRuntimeConfig(enabled=True, execution_mode="compat")

            def get_llm_gateway(self):  # type: ignore[override]
                return GatewayStub()

        with tempfile.TemporaryDirectory() as temp_dir:
            tests_dir = Path(temp_dir) / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            (tests_dir / "test_ok.py").write_text(
                "import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            states = make_testing_states()
            states["implementation_status"]["workspace_path"] = str(temp_dir)
            state_manager = InMemoryStateManager(states)
            orchestrator = Orchestrator(state_manager=state_manager)
            orchestrator.agents[Stage.TESTING] = TestableValidationAgent()

            result = orchestrator.orchestrate("run tests")
            self.assertEqual(
                result.diagnostic["llm_trace"],
                sentinel_trace.model_dump(mode="python"),
            )


if __name__ == "__main__":
    unittest.main()
