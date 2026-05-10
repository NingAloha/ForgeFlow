from __future__ import annotations

import json

from ..base import AgentContext, AgentResult, BaseAgent
from ..common import LLMGateway, PromptContract
from ..common.llm_policy import (
    resolve_gateway_failure,
    should_use_llm,
)
from ..common.runtime_config import LLMRuntimeConfig, load_llm_runtime_config
from schemas.llm_trace import EMPTY_LLM_TRACE, LLMTraceModel
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
        llm_trace: LLMTraceModel = EMPTY_LLM_TRACE
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
            failure_result = resolve_gateway_failure(
                llm_result=llm_result,
                llm_config=llm_config,
                stage_name=self.stage_name,
                state_key=self.state_key,
                agent_name=self.agent_name,
                updated_state=current_state,
                fallback_factory=None,
                strict_summary="Design blocked: strict_llm mode requires successful LLM output.",
                fatal_summary="Design blocked: LLM output is unavailable.",
            )
            if failure_result is not None:
                return failure_result
            if llm_result.status == "success" and isinstance(llm_result.parsed_output, dict):
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
