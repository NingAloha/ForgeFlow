from __future__ import annotations

import json
import re
from pathlib import Path

from ..base import AgentContext, AgentResult, BaseAgent
from ..common import (
    LLMAdapter,
    LLMRuntimeConfig,
    WorkspaceExecutor,
    build_llm_failure_question_state,
    load_llm_runtime_config,
    should_block_on_llm_failure,
    should_use_llm,
)
from .planning import TestValidationPlanningMixin


class TestValidationEngineerAgent(TestValidationPlanningMixin, BaseAgent):
    agent_name = "Test & Validation Engineer"
    stage_name = "TESTING"
    state_key = "test_report"

    def get_llm_runtime_config(self) -> LLMRuntimeConfig:
        return load_llm_runtime_config()

    def get_llm_adapter(self) -> LLMAdapter:
        return LLMAdapter()

    def run(self, context: AgentContext) -> AgentResult:
        current_state = dict(context.states.get(self.state_key, {}))
        spec = dict(context.states.get("spec", {}))
        implementation_status = dict(context.states.get("implementation_status", {}))
        design = dict(context.states.get("system_design", {}))
        user_input = context.user_input.strip()

        issues = self.build_issues(spec, implementation_status, design)
        llm_config = self.get_llm_runtime_config()
        llm_trace = {
            "enabled": llm_config.enabled,
            "provider": llm_config.provider,
            "model": llm_config.model,
            "protocol": llm_config.protocol,
            "used": False,
            "fallback_used": False,
            "error": "",
            "latency_ms": 0,
            "source": "fallback",
        }

        test_scope = current_state.get("test_scope") or "integration"
        result = self.pick_result(issues, implementation_status)

        workspace_path = str(implementation_status.get("workspace_path", "")).strip()
        command = list(implementation_status.get("suggested_test_command", [])) or [
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

        if not workspace_path or not Path(workspace_path).exists():
            updated_state = {
                **current_state,
                "test_scope": test_scope,
                "result": self.pick_result(issues, implementation_status),
                "issues": issues,
                "command": command,
                "exit_code": 0 if self.pick_result(issues, implementation_status) == "pass" else 1,
                "tests_run": 0,
                "failed_tests": ["workspace_missing"] if self.pick_result(issues, implementation_status) != "pass" else [],
                "log_excerpt": "workspace is missing; synthetic validation used in compatibility path.",
            }
            return AgentResult(
                agent_name=self.agent_name,
                stage_name=self.stage_name,
                state_key=self.state_key,
                updated_state=updated_state,
                summary="Validation used synthetic path because workspace is unavailable.",
                notes=["Real test execution skipped due missing workspace path."],
                blockers=["workspace_missing"] if updated_state["result"] != "pass" else [],
                handoff_ready=updated_state["result"] == "pass",
                diagnostics={"llm_trace": llm_trace, "execution_trace": {}},
            )

        llm_stage_enabled = should_use_llm(llm_config, self.stage_name)
        if llm_stage_enabled and user_input:
            llm_result = self.get_llm_adapter().generate_json(
                system_prompt=(
                    "Return strict JSON only with keys: test_scope, command, issues_hint. "
                    "command must be an array of command tokens suitable for unittest/pytest."
                ),
                user_prompt=(
                    f"User request: {user_input}\n"
                    f"implementation_status={json.dumps(implementation_status, ensure_ascii=False)}"
                ),
                config=llm_config,
            )
            llm_trace["used"] = True
            llm_trace["latency_ms"] = llm_result.latency_ms
            llm_trace["error"] = llm_result.error
            if llm_result.ok and isinstance(llm_result.content, dict):
                payload = llm_result.content
                test_scope = str(payload.get("test_scope", test_scope))
                candidate_command = payload.get("command")
                if isinstance(candidate_command, list) and candidate_command:
                    command = [str(x) for x in candidate_command if str(x).strip()]
                llm_trace["source"] = "llm"
            else:
                llm_trace["fallback_used"] = True

        if should_block_on_llm_failure(
            llm_config,
            self.stage_name,
            llm_trace["used"],
            llm_trace["fallback_used"],
        ):
            updated_state = {
                **current_state,
                "test_scope": test_scope,
                "result": "fail",
                "issues": issues,
                "command": command,
                "exit_code": 1,
                "failed_tests": ["llm_generation_failed"],
                "log_excerpt": llm_trace.get("error", "strict_llm blocked."),
            }
            return AgentResult(
                agent_name=self.agent_name,
                stage_name=self.stage_name,
                state_key=self.state_key,
                updated_state=updated_state,
                summary="Testing blocked: strict_llm mode requires successful LLM output.",
                notes=["LLM output invalid for testing command synthesis."],
                blockers=["llm_generation_failed"],
                handoff_ready=False,
                requires_user_input=True,
                question_state_update=build_llm_failure_question_state(
                    self.stage_name,
                    self.state_key,
                    llm_trace.get("error", ""),
                ),
                diagnostics={"llm_trace": llm_trace, "execution_trace": {}},
            )

        executor = WorkspaceExecutor(workspace_root=Path(workspace_path))
        cmd_result = executor.run_command(command)
        tests_run = self._extract_tests_run(cmd_result.stdout + "\n" + cmd_result.stderr)
        failed_tests = self._extract_failed_tests(cmd_result.stdout + "\n" + cmd_result.stderr)
        log_excerpt = self._tail_excerpt(cmd_result.stdout, cmd_result.stderr)

        if cmd_result.exit_code == 0 and tests_run > 0:
            result = "pass"
            issues = []
        elif cmd_result.exit_code == 0 and tests_run == 0:
            result = "fail"
            failed_tests = failed_tests or ["No tests were discovered."]
        elif failed_tests:
            result = "fail"
        else:
            result = "partial"

        if cmd_result.exit_code != 0 and not issues:
            issues = [
                {
                    "title": "Automated tests failed",
                    "severity": "high",
                    "status": "open",
                    "related_modules": [implementation_status.get("module_name", "")],
                    "related_contracts": [],
                    "notes": "See log_excerpt and failed_tests for details.",
                }
            ]

        updated_state = {
            **current_state,
            "test_scope": test_scope,
            "result": result,
            "issues": issues,
            "command": command,
            "exit_code": int(cmd_result.exit_code),
            "tests_run": tests_run,
            "failed_tests": failed_tests,
            "log_excerpt": log_excerpt,
        }

        blockers = [
            str(issue.get("title", ""))
            for issue in issues
            if issue.get("severity") in {"critical", "high"}
            and issue.get("status") in {"open", "confirmed"}
        ]
        return AgentResult(
            agent_name=self.agent_name,
            stage_name=self.stage_name,
            state_key=self.state_key,
            updated_state=updated_state,
            summary="Validation executed real test command and produced structured report.",
            notes=[
                "Produced test_report from real command execution with exit code and failed tests."
            ],
            blockers=blockers,
            handoff_ready=updated_state["result"] == "pass" and cmd_result.exit_code == 0,
            diagnostics={
                "llm_trace": llm_trace,
                "execution_trace": {
                    "workspace_path": executor.trace.workspace_path,
                    "file_writes": executor.trace.file_writes,
                    "command_results": [
                        {
                            "command": cmd_result.command,
                            "exit_code": cmd_result.exit_code,
                            "stdout": cmd_result.stdout[-4000:],
                            "stderr": cmd_result.stderr[-4000:],
                        }
                    ],
                },
            },
        )

    def _extract_failed_tests(self, text: str) -> list[str]:
        failed = set()
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("FAIL:") or line.startswith("ERROR:"):
                failed.add(line)
            elif re.search(r"FAILED \(failures=|FAILED \(errors=", line):
                failed.add(line)
        return sorted(failed)

    def _extract_tests_run(self, text: str) -> int:
        match = re.search(r"Ran\s+(\d+)\s+tests?", text)
        if not match:
            return 0
        return int(match.group(1))

    def _tail_excerpt(self, stdout: str, stderr: str, max_lines: int = 40) -> str:
        merged = (stdout + "\n" + stderr).strip().splitlines()
        if not merged:
            return ""
        return "\n".join(merged[-max_lines:])
