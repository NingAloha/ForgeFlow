from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agents.base import AgentContext
from agents.common.llm_gateway import LLMStructuredResult
from agents.common.runtime_config import LLMRuntimeConfig
from agents.implementation_engineer import ImplementationEngineerAgent
from agents.requirements_engineer import RequirementsEngineerAgent
from agents.solution_engineer import SolutionEngineerAgent
from agents.system_designer import SystemDesignerAgent
from agents.test_validation_engineer import TestValidationEngineerAgent
from tests.unit.support.orchestrator_fixtures import (
    make_design_ready_states,
    make_empty_states,
    make_requirements_ready_states,
    make_solution_ready_states,
    make_testing_states,
)


def _result(status: str) -> LLMStructuredResult:
    return LLMStructuredResult(
        status=status,
        parsed_output={
            "project_goal": "x",
            "functional_requirements": ["a"],
            "acceptance_criteria": ["b"],
        }
        if status == "success"
        else None,
        validation_errors=[],
        raw_output="{}",
        repair_attempts=0,
        confidence=None,
        failure_type="none" if status == "success" else "network_error",
        model="m",
        provider="p",
        protocol="openai",
        latency_ms=1,
        error="boom" if status != "success" else "",
    )


class _GatewayStub:
    def __init__(self, status: str) -> None:
        self.status = status

    def generate(self, contract, user_prompt, config):  # noqa: ANN001
        return _result(self.status)


class _ReqAgent(RequirementsEngineerAgent):
    def __init__(self, status: str, mode: str) -> None:
        super().__init__()
        self._status = status
        self._mode = mode

    def get_llm_runtime_config(self) -> LLMRuntimeConfig:
        return LLMRuntimeConfig(enabled=True, execution_mode=self._mode)

    def get_llm_gateway(self):  # type: ignore[override]
        return _GatewayStub(self._status)


class _SolAgent(SolutionEngineerAgent):
    def __init__(self, status: str, mode: str) -> None:
        super().__init__()
        self._status = status
        self._mode = mode

    def get_llm_runtime_config(self) -> LLMRuntimeConfig:
        return LLMRuntimeConfig(enabled=True, execution_mode=self._mode)

    def get_llm_gateway(self):  # type: ignore[override]
        return _GatewayStub(self._status)


class _DesignAgent(SystemDesignerAgent):
    def __init__(self, status: str, mode: str) -> None:
        super().__init__()
        self._status = status
        self._mode = mode

    def get_llm_runtime_config(self) -> LLMRuntimeConfig:
        return LLMRuntimeConfig(enabled=True, execution_mode=self._mode)

    def get_llm_gateway(self):  # type: ignore[override]
        return _GatewayStub(self._status)


class _ImplAgent(ImplementationEngineerAgent):
    def __init__(self, status: str, mode: str) -> None:
        super().__init__()
        self._status = status
        self._mode = mode

    def get_llm_runtime_config(self) -> LLMRuntimeConfig:
        return LLMRuntimeConfig(enabled=True, execution_mode=self._mode)

    def get_llm_gateway(self):  # type: ignore[override]
        return _GatewayStub(self._status)


class _TestAgent(TestValidationEngineerAgent):
    def __init__(self, status: str, mode: str) -> None:
        super().__init__()
        self._status = status
        self._mode = mode

    def get_llm_runtime_config(self) -> LLMRuntimeConfig:
        return LLMRuntimeConfig(enabled=True, execution_mode=self._mode)

    def get_llm_gateway(self):  # type: ignore[override]
        return _GatewayStub(self._status)


class AgentGatewayStatusTests(unittest.TestCase):
    def test_retryable_error_exhausted_strict_llm_waits_all_stages(self) -> None:
        req = _ReqAgent("retryable_error", "strict_llm").run(
            AgentContext(user_input="x", states=make_empty_states())
        )
        self.assertTrue(req.handoff_ready)
        self.assertFalse(req.requires_user_input)

        sol = _SolAgent("retryable_error", "strict_llm").run(
            AgentContext(user_input="x", states=make_requirements_ready_states())
        )
        self.assertTrue(sol.requires_user_input)

        design = _DesignAgent("retryable_error", "strict_llm").run(
            AgentContext(user_input="x", states=make_solution_ready_states())
        )
        self.assertTrue(design.requires_user_input)

        impl = _ImplAgent("retryable_error", "strict_llm").run(
            AgentContext(user_input="x", states=make_design_ready_states())
        )
        self.assertTrue(impl.requires_user_input)

        with tempfile.TemporaryDirectory() as temp_dir:
            tests_dir = Path(temp_dir) / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            (tests_dir / "test_smoke.py").write_text(
                "import unittest\n", encoding="utf-8"
            )
            states = make_testing_states()
            states["implementation_status"]["workspace_path"] = str(temp_dir)
            test_agent = _TestAgent("retryable_error", "strict_llm").run(
                AgentContext(user_input="x", states=states)
            )
            self.assertTrue(test_agent.requires_user_input)

    def test_fatal_error_waits_all_stages(self) -> None:
        req = _ReqAgent("fatal_error", "strict_llm").run(
            AgentContext(user_input="x", states=make_empty_states())
        )
        self.assertTrue(req.requires_user_input)

        sol = _SolAgent("fatal_error", "strict_llm").run(
            AgentContext(user_input="x", states=make_requirements_ready_states())
        )
        self.assertTrue(sol.requires_user_input)

        design = _DesignAgent("fatal_error", "strict_llm").run(
            AgentContext(user_input="x", states=make_solution_ready_states())
        )
        self.assertTrue(design.requires_user_input)

        impl = _ImplAgent("fatal_error", "strict_llm").run(
            AgentContext(user_input="x", states=make_design_ready_states())
        )
        self.assertTrue(impl.requires_user_input)

        with tempfile.TemporaryDirectory() as temp_dir:
            tests_dir = Path(temp_dir) / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            (tests_dir / "test_smoke.py").write_text(
                "import unittest\n", encoding="utf-8"
            )
            states = make_testing_states()
            states["implementation_status"]["workspace_path"] = str(temp_dir)
            test_agent = _TestAgent("fatal_error", "strict_llm").run(
                AgentContext(user_input="x", states=states)
            )
            self.assertTrue(test_agent.requires_user_input)

    def test_compat_fallback_still_works_all_stages(self) -> None:
        req = _ReqAgent("retryable_error", "compat").run(
            AgentContext(user_input="x", states=make_empty_states())
        )
        self.assertTrue(req.handoff_ready)

        sol = _SolAgent("retryable_error", "compat").run(
            AgentContext(user_input="x", states=make_requirements_ready_states())
        )
        self.assertTrue(sol.handoff_ready)

        design = _DesignAgent("retryable_error", "compat").run(
            AgentContext(user_input="x", states=make_solution_ready_states())
        )
        self.assertTrue(design.handoff_ready)

        impl = _ImplAgent("retryable_error", "compat").run(
            AgentContext(user_input="x", states=make_design_ready_states())
        )
        self.assertTrue(bool(impl.updated_state.get("artifacts_generated")))

        with tempfile.TemporaryDirectory() as temp_dir:
            tests_dir = Path(temp_dir) / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            (tests_dir / "test_main.py").write_text(
                "import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            states = make_testing_states()
            states["implementation_status"]["workspace_path"] = str(temp_dir)
            test_agent = _TestAgent("retryable_error", "compat").run(
                AgentContext(user_input="x", states=states)
            )
            self.assertIn(
                test_agent.updated_state["result"], {"pass", "partial", "fail"}
            )


if __name__ == "__main__":
    unittest.main()
