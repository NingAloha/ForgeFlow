from __future__ import annotations

from ..base import AgentContext, AgentResult, BaseAgent
from ..common import (
    LLMGateway,
    LLMRuntimeConfig,
    PromptContract,
    load_llm_runtime_config,
    resolve_gateway_failure,
    should_use_llm,
)
from schemas.llm_trace import EMPTY_LLM_TRACE
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
        user_input = context.user_input.strip()
        mode = self.resolve_implementation_mode(current_state, context.metadata)

        if mode == "execute":
            updated_state = self.build_execution_disabled_status(current_state, design)
            updated_state = ImplementationStatusState.model_validate(updated_state).model_dump(mode="python")
            patch_draft = self.build_single_module_patch_draft(updated_state["module_name"])
            contract_lines = self.build_execution_contract_lines(updated_state["module_name"])
            execute_notes = [
                "implementation_mode=execute; execution is disabled in current stable flow.",
                "contract_compliance is false because no execution handoff can be validated in execute mode.",
                "dry-run patch preview generated for module directories only; no file mutation and no command execution performed.",
                "BEGIN_EXECUTION_CONTRACT",
                *contract_lines,
                "END_EXECUTION_CONTRACT",
            ]
            if patch_draft:
                execute_notes.extend(
                    [
                        "BEGIN_PATCH_DRAFT",
                        patch_draft,
                        "END_PATCH_DRAFT",
                    ]
                )
            return AgentResult(
                agent_name=self.agent_name,
                stage_name=self.stage_name,
                state_key=self.state_key,
                updated_state=updated_state,
                summary=(
                    "Implementation execute mode is reserved for future integration and is currently disabled."
                ),
                notes=execute_notes,
                blockers=updated_state["blockers"],
                handoff_ready=False,
                diagnostics={
                    "llm_trace": EMPTY_LLM_TRACE,
                    "execution_trace": {
                        "workspace_path": updated_state["workspace_path"],
                        "file_writes": [],
                        "command_results": [],
                    },
                },
            )

        design_modules = self.get_design_modules(design)
        module_name = self.select_primary_module_name(current_state, design_modules)

        files_touched: list[str] = []
        tests_added_or_updated: list[str] = []
        known_limitations: list[str] = []
        blockers: list[str] = []
        notes: list[str] = []

        if not design_modules:
            blockers.append("missing design modules in system_design.project_structure.modules")

        has_any_contract = bool(design.get("contracts"))
        has_any_data_flow = bool(design.get("data_flow"))

        module_contract_alignment: dict[str, bool] = {}
        for module in design_modules:
            contract = self.match_module_contract(module, design)
            has_data_flow = self.has_module_data_flow(module, design)

            if not has_any_contract or contract is None:
                blockers.append(f"missing design contract for {module}")
                known_limitations.append(f"contract unresolved for {module}")

            if not has_any_data_flow or not has_data_flow:
                blockers.append(f"missing data flow step for {module}")
                known_limitations.append(f"data flow unresolved for {module}")

            planned_directory = self.find_module_directory(module, design)
            expected_artifact_types = self.build_expected_artifact_types()
            module_steps = self.build_module_steps(module, contract)
            done_criteria = self.build_module_done_criteria()
            suggested_tests = self.build_module_suggested_tests(module)

            files_touched.append(
                f"module={module}; planned_directory={planned_directory}; expected_artifact_types=[{' | '.join(expected_artifact_types)}]"
            )
            tests_added_or_updated.append(
                f"module={module}; suggested_tests=[{' | '.join(suggested_tests)}]"
            )
            notes.append(self.build_module_note(module, module_steps, done_criteria))

            module_contract_alignment[module] = contract is not None and has_data_flow

        contract_compliance = bool(design_modules) and all(module_contract_alignment.values())
        implementation_status = "blocked" if blockers else "done"

        updated_state = {
            **current_state,
            "module_name": module_name,
            "implementation_status": implementation_status,
            "files_touched": files_touched,
            "tests_added_or_updated": tests_added_or_updated,
            "contract_compliance": contract_compliance,
            "known_limitations": sorted(set(known_limitations)),
            "blockers": sorted(set(blockers)),
            "workspace_path": str(current_state.get("workspace_path", "")),
            "commands_executed": [],
            "artifacts_generated": ["handoff_package_generated"],
            "suggested_test_command": [],
        }
        updated_state = ImplementationStatusState.model_validate(updated_state).model_dump(mode="python")

        llm_trace = EMPTY_LLM_TRACE
        llm_config = self.get_llm_runtime_config()
        if should_use_llm(llm_config, self.stage_name) and user_input:
            llm_result = self.get_llm_gateway().generate(
                contract=PromptContract(
                    stage_name=self.stage_name,
                    system_prompt=(
                        "Return strict JSON only with key handoff_ready and boolean value."
                    ),
                    required_fields=["handoff_ready"],
                    allowed_fields=["handoff_ready"],
                    output_model=None,
                ),
                user_prompt=(
                    "Validate implementation handoff package alignment without generating code."
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
                updated_state=updated_state,
                fallback_factory=None,
                strict_summary=(
                    "Implementation handoff blocked: strict_llm mode requires successful LLM output."
                ),
                fatal_summary=(
                    "Implementation handoff blocked: LLM output is unavailable."
                ),
            )
            if failure_result is not None:
                failure_result.diagnostics["execution_trace"] = {
                    "workspace_path": updated_state["workspace_path"],
                    "file_writes": [],
                    "command_results": [],
                }
                return failure_result

        summary = (
            "Implementation produced module-level handoff checklist aligned to design contracts."
            if not blockers
            else "Implementation handoff is blocked by missing design contract or data flow inputs."
        )
        result_notes = [
            "implementation_mode=handoff",
            "contract_compliance means handoff package alignment with design contract, not code implementation completeness.",
            *notes,
        ]

        return AgentResult(
            agent_name=self.agent_name,
            stage_name=self.stage_name,
            state_key=self.state_key,
            updated_state=updated_state,
            summary=summary,
            notes=result_notes,
            blockers=updated_state["blockers"],
            handoff_ready=not blockers,
            diagnostics={
                "llm_trace": llm_trace,
                "execution_trace": {
                    "workspace_path": updated_state["workspace_path"],
                    "file_writes": [],
                    "command_results": [],
                },
            },
        )
