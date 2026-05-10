from __future__ import annotations

import json

from ..base import AgentContext, AgentResult, BaseAgent
from ..common import LLMGateway, PromptContract
from ..common.llm_policy import (
    build_llm_failure_question_state,
    should_use_llm,
)
from ..common.runtime_config import LLMRuntimeConfig, load_llm_runtime_config
from schemas.design import SystemDesignState
from .planning import SystemDesignPlanningMixin


class SystemDesignerAgent(SystemDesignPlanningMixin, BaseAgent):
    agent_name = "System Designer"
    stage_name = "DESIGN"
    state_key = "system_design"

    def get_llm_runtime_config(self) -> LLMRuntimeConfig:
        return load_llm_runtime_config()

    def get_llm_gateway(self) -> LLMGateway:
        return LLMGateway()

    def run(self, context: AgentContext) -> AgentResult:
        current_state = dict(context.states.get(self.state_key, {}))
        solution = dict(context.states.get("solution", {}))
        spec = dict(context.states.get("spec", {}))
        user_input = context.user_input.strip()
        module_mapping = list(solution.get("module_mapping", []))

        if not module_mapping:
            return AgentResult(
                agent_name=self.agent_name,
                stage_name=self.stage_name,
                state_key=self.state_key,
                updated_state=current_state,
                summary="Design is blocked until solution module mapping is available.",
                notes=[
                    "No system design was produced because solution.module_mapping is empty."
                ],
                blockers=["solution_module_mapping_missing"],
                handoff_ready=False,
            )

        project_structure = self.build_project_structure(module_mapping)
        contracts = self.build_contracts(module_mapping)
        data_flow = self.build_data_flow(contracts)
        mvp_plan = self.build_mvp_plan(spec, module_mapping)
        llm_config = self.get_llm_runtime_config()
        llm_trace: dict[str, object] = {}
        llm_success = False
        llm_stage_enabled = should_use_llm(llm_config, self.stage_name)
        if llm_stage_enabled and user_input:
            contract = PromptContract(
                stage_name=self.stage_name,
                system_prompt=(
                    "Return strict JSON only with keys: project_structure, contracts, "
                    "data_flow, mvp_plan. Keep schema-compatible shapes."
                ),
                required_fields=["project_structure", "contracts", "data_flow", "mvp_plan"],
                output_model=SystemDesignState,
            )
            llm_result = self.get_llm_gateway().generate(
                contract=contract,
                user_prompt=(
                    f"User request: {user_input}\n"
                    "Build system design from solution and spec JSON:\n"
                    f"solution={json.dumps(solution, ensure_ascii=False)}\n"
                    f"spec={json.dumps(spec, ensure_ascii=False)}"
                ),
                config=llm_config,
            )
            llm_trace = llm_result.to_trace()
            if llm_result.status == "success" and isinstance(llm_result.parsed_output, dict):
                llm_success = True
                payload = llm_result.parsed_output
                candidate_state = {
                    "project_structure": payload.get("project_structure", project_structure),
                    "contracts": payload.get("contracts", contracts),
                    "data_flow": payload.get("data_flow", data_flow),
                    "mvp_plan": payload.get("mvp_plan", mvp_plan),
                }
                normalized = SystemDesignState.model_validate(candidate_state).model_dump(mode="python")
                project_structure = normalized["project_structure"]
                contracts = normalized["contracts"]
                data_flow = normalized["data_flow"]
                mvp_plan = normalized["mvp_plan"]
            elif llm_result.status in {"fatal_error", "needs_user_input"}:
                return AgentResult(
                    agent_name=self.agent_name,
                    stage_name=self.stage_name,
                    state_key=self.state_key,
                    updated_state=current_state,
                    summary="Design blocked: LLM output is unavailable.",
                    notes=["LLM output was invalid or unavailable; waiting for user action."],
                    blockers=["llm_generation_failed"],
                    handoff_ready=False,
                    requires_user_input=True,
                    question_state_update=build_llm_failure_question_state(
                        self.stage_name,
                        self.state_key,
                        llm_result.error,
                    ),
                    diagnostics={"llm_trace": llm_result.to_trace()},
                )
            elif llm_result.status == "retryable_error" and llm_config.execution_mode == "strict_llm":
                return AgentResult(
                    agent_name=self.agent_name,
                    stage_name=self.stage_name,
                    state_key=self.state_key,
                    updated_state=current_state,
                    summary="Design blocked: strict_llm mode requires successful LLM output.",
                    notes=["LLM retry budget exhausted; waiting for user action."],
                    blockers=["llm_generation_failed"],
                    handoff_ready=False,
                    requires_user_input=True,
                    question_state_update=build_llm_failure_question_state(
                        self.stage_name,
                        self.state_key,
                        llm_result.error,
                    ),
                    diagnostics={"llm_trace": llm_result.to_trace()},
                )

        if (
            llm_config.execution_mode == "strict_llm"
            and llm_stage_enabled
            and user_input
            and not llm_success
        ):
            return AgentResult(
                agent_name=self.agent_name,
                stage_name=self.stage_name,
                state_key=self.state_key,
                updated_state=current_state,
                summary="Design blocked: strict_llm mode requires successful LLM output.",
                notes=["LLM output was invalid or unavailable; waiting for user action."],
                blockers=["llm_generation_failed"],
                handoff_ready=False,
                requires_user_input=True,
                question_state_update=build_llm_failure_question_state(
                    self.stage_name,
                    self.state_key,
                    str(llm_trace.get("error", "")),
                ),
                diagnostics={"llm_trace": llm_trace},
            )
        updated_state = {
            **current_state,
            "project_structure": project_structure,
            "contracts": contracts,
            "data_flow": data_flow,
            "mvp_plan": mvp_plan,
        }

        return AgentResult(
            agent_name=self.agent_name,
            stage_name=self.stage_name,
            state_key=self.state_key,
            updated_state=updated_state,
            summary="System design artifacts were generated from the current solution state.",
            notes=[
                "Built project structure, contracts, data flow, and MVP milestones for implementation handoff."
            ],
            handoff_ready=True,
            diagnostics={"llm_trace": llm_trace},
        )
