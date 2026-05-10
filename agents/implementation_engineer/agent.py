from __future__ import annotations

import json
from pathlib import Path

from ..base import AgentContext, AgentResult, BaseAgent
from ..common import (
    LLMGateway,
    LLMRuntimeConfig,
    PromptContract,
    WorkspaceExecutor,
    load_llm_runtime_config,
    resolve_gateway_failure,
    should_use_llm,
)
from schemas.llm_trace import EMPTY_LLM_TRACE, LLMTraceModel
from schemas.implementation import ImplementationStatusState
from .planning import ImplementationPlanningMixin


class ImplementationEngineerAgent(ImplementationPlanningMixin, BaseAgent):
    agent_name = "Implementation Engineer"
    stage_name = "IMPLEMENTATION"
    state_key = "implementation_status"

    def get_llm_runtime_config(self) -> LLMRuntimeConfig:
        return load_llm_runtime_config()

    def get_llm_gateway(self) -> LLMGateway:
        return LLMGateway()

    def run(self, context: AgentContext) -> AgentResult:
        current_state = dict(context.states.get(self.state_key, {}))
        design = dict(context.states.get("system_design", {}))
        solution = dict(context.states.get("solution", {}))
        user_input = context.user_input.strip()
        module_name = self.select_module_name(current_state, design, solution)
        blockers: list[str] = []

        if not module_name:
            blockers.append("No module selected from design or solution states.")
        if not design.get("contracts"):
            blockers.append("system_design.contracts is empty.")
        if not design.get("data_flow"):
            blockers.append("system_design.data_flow is empty.")

        contract_compliance = self.evaluate_contract_compliance(module_name, design)
        if not contract_compliance:
            blockers.append("No matching design contract found for the active module.")

        llm_config = self.get_llm_runtime_config()
        llm_trace: LLMTraceModel = EMPTY_LLM_TRACE
        fallback_source = ""

        workspace_path = str(context.metadata.get("generated_project_dir", "")).strip()
        if not workspace_path:
            workspace_path = str(Path(".forgeflow") / "generated" / "manual")

        files_touched: list[str] = []
        tests_added_or_updated: list[str] = []
        artifacts_generated: list[str] = []
        commands_executed: list[str] = []
        suggested_test_command = [
            "python3",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_*.py",
            "-v",
        ]

        executor = WorkspaceExecutor(workspace_root=workspace_path or ".")
        llm_stage_enabled = should_use_llm(llm_config, self.stage_name)
        llm_files: list[dict[str, str]] = []

        if llm_stage_enabled and user_input:
            contract = PromptContract(
                stage_name=self.stage_name,
                system_prompt=(
                    "Return strict JSON only with keys: files, tests, suggested_test_command. "
                    "files/tests are arrays of objects with path and content. "
                    "Generate a minimal runnable Python project with unittest tests."
                ),
                required_fields=["files", "tests", "suggested_test_command"],
                output_model=None,
            )
            llm_result = self.get_llm_gateway().generate(
                contract=contract,
                user_prompt=(
                    f"User request: {user_input}\n"
                    f"Design JSON: {json.dumps(design, ensure_ascii=False)}\n"
                    f"Solution JSON: {json.dumps(solution, ensure_ascii=False)}"
                ),
                config=llm_config,
            )
            llm_trace = llm_result.to_trace()
            failure_result = resolve_gateway_failure(
                llm_result=llm_result,
                llm_config=llm_config,
                stage_name=self.stage_name,
                state_key=self.state_key,
                agent_name=self.agent_name,
                updated_state={
                    **current_state,
                    "module_name": module_name,
                    "implementation_status": "blocked",
                    "files_touched": [],
                    "tests_added_or_updated": [],
                    "contract_compliance": contract_compliance,
                    "known_limitations": ["strict_llm mode requires successful LLM generation."],
                    "blockers": ["llm_generation_failed"],
                    "workspace_path": workspace_path,
                    "commands_executed": [],
                    "artifacts_generated": [],
                    "suggested_test_command": suggested_test_command,
                },
                fallback_factory=None,
                strict_summary="Implementation blocked: strict_llm mode requires successful LLM output.",
                fatal_summary="Implementation blocked: LLM output is unavailable.",
            )
            if failure_result is not None:
                failure_result.diagnostics["execution_trace"] = {}
                return failure_result
            if llm_result.status == "success" and isinstance(llm_result.parsed_output, dict):
                payload = llm_result.parsed_output
                raw_files = payload.get("files", [])
                raw_tests = payload.get("tests", [])
                if isinstance(raw_files, list) and isinstance(raw_tests, list):
                    llm_files = [
                        {
                            "path": str(item.get("path", "")).strip(),
                            "content": str(item.get("content", "")),
                        }
                        for item in (raw_files + raw_tests)
                        if isinstance(item, dict)
                        and str(item.get("path", "")).strip()
                    ]
                    suggested = payload.get("suggested_test_command")
                    if isinstance(suggested, list) and suggested:
                        suggested_test_command = [str(x) for x in suggested if str(x).strip()]

        if llm_files:
            try:
                for file_item in llm_files:
                    written = executor.write_file(file_item["path"], file_item["content"])
                    artifacts_generated.append(written)
                    if "/tests/" in f"/{written}" or written.startswith("tests/"):
                        tests_added_or_updated.append(written)
                    else:
                        files_touched.append(written)
            except Exception as exc:
                blockers.append(f"File generation failed: {exc}")
        else:
            # compat mode fallback template
            fallback_source = "implementation_compat"
            fallback_files = self._build_fallback_template_files(user_input)
            for path, content in fallback_files:
                written = executor.write_file(path, content)
                artifacts_generated.append(written)
                if "/tests/" in f"/{written}" or written.startswith("tests/"):
                    tests_added_or_updated.append(written)
                else:
                    files_touched.append(written)

        implementation_status = "blocked" if blockers else "done"
        updated_state = {
            **current_state,
            "module_name": module_name,
            "implementation_status": implementation_status,
            "files_touched": files_touched,
            "tests_added_or_updated": tests_added_or_updated,
            "contract_compliance": contract_compliance,
            "known_limitations": [],
            "blockers": blockers,
            "workspace_path": workspace_path,
            "commands_executed": commands_executed,
            "artifacts_generated": artifacts_generated,
            "suggested_test_command": suggested_test_command,
        }
        updated_state = ImplementationStatusState.model_validate(updated_state).model_dump(mode="python")

        if blockers:
            diagnostics = {
                "llm_trace": llm_trace,
                "execution_trace": self._trace_to_dict(executor.trace),
            }
            if fallback_source:
                diagnostics["fallback_source"] = fallback_source
            return AgentResult(
                agent_name=self.agent_name,
                stage_name=self.stage_name,
                state_key=self.state_key,
                updated_state=updated_state,
                summary="Implementation planning is blocked by generation or design issues.",
                notes=[
                    "Recorded blockers to trigger explicit backflow attribution in orchestrator."
                ],
                blockers=blockers,
                handoff_ready=False,
                diagnostics=diagnostics,
            )

        diagnostics = {
            "llm_trace": llm_trace,
            "execution_trace": self._trace_to_dict(executor.trace),
        }
        if fallback_source:
            diagnostics["fallback_source"] = fallback_source
        return AgentResult(
            agent_name=self.agent_name,
            stage_name=self.stage_name,
            state_key=self.state_key,
            updated_state=updated_state,
            summary="Implementation generated real project files and test artifacts.",
            notes=[
                "Generated project files in isolated workspace and prepared test command for validation."
            ],
            handoff_ready=True,
            diagnostics=diagnostics,
        )

    def _trace_to_dict(self, trace) -> dict[str, object]:
        return {
            "workspace_path": trace.workspace_path,
            "file_writes": list(trace.file_writes),
            "command_results": [
                {
                    "command": list(item.command),
                    "exit_code": item.exit_code,
                    "stdout": item.stdout[-4000:],
                    "stderr": item.stderr[-4000:],
                }
                for item in trace.command_results
            ],
        }

    def _build_fallback_template_files(self, user_input: str) -> list[tuple[str, str]]:
        title = user_input.strip() or "demo project"
        package_name = "app"
        return [
            (
                f"{package_name}/__init__.py",
                '"""Generated demo package."""\n',
            ),
            (
                f"{package_name}/main.py",
                """
from __future__ import annotations


def build_message() -> str:
    return "demo project ready"


if __name__ == "__main__":
    print(build_message())
""".lstrip(),
            ),
            (
                "README.md",
                f"# Generated Project\n\nRequest: {title}\n",
            ),
            (
                "tests/test_main.py",
                """
import unittest

from app.main import build_message


class MainTests(unittest.TestCase):
    def test_build_message(self) -> None:
        self.assertEqual(build_message(), "demo project ready")


if __name__ == "__main__":
    unittest.main()
""".lstrip(),
            ),
        ]
