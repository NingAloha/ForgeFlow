from __future__ import annotations

import json

from pydantic import ValidationError

from ..base import AgentContext, AgentResult, BaseAgent
from ..common.llm_adapter import LLMAdapter
from ..common.llm_policy import (
    build_llm_failure_question_state,
    should_block_on_llm_failure,
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

    def get_llm_adapter(self) -> LLMAdapter:
        return LLMAdapter()

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
        llm_stage_enabled = should_use_llm(llm_config, self.stage_name)
        if llm_config.enabled and llm_stage_enabled and user_input:
            llm_result = self.get_llm_adapter().generate_json(
                system_prompt=(
                    "Return strict JSON only with keys: project_structure, contracts, "
                    "data_flow, mvp_plan. Keep schema-compatible shapes."
                ),
                user_prompt=(
                    f"User request: {user_input}\\n"
                    "Build system design from solution and spec JSON:\\n"
                    f"solution={json.dumps(solution, ensure_ascii=False)}\\n"
                    f"spec={json.dumps(spec, ensure_ascii=False)}"
                ),
                config=llm_config,
            )
            llm_trace["used"] = True
            llm_trace["latency_ms"] = llm_result.latency_ms
            llm_trace["error"] = llm_result.error
            if llm_result.ok and isinstance(llm_result.content, dict):
                llm_trace["source"] = "llm"
                payload = llm_result.content
                candidate_state = {
                    "project_structure": payload.get("project_structure", project_structure),
                    "contracts": payload.get("contracts", contracts),
                    "data_flow": payload.get("data_flow", data_flow),
                    "mvp_plan": payload.get("mvp_plan", mvp_plan),
                }
                try:
                    normalized = SystemDesignState.model_validate(candidate_state).model_dump(mode="python")
                    project_structure = normalized["project_structure"]
                    contracts = normalized["contracts"]
                    data_flow = normalized["data_flow"]
                    mvp_plan = normalized["mvp_plan"]
                except ValidationError:
                    llm_trace["fallback_used"] = True
                    llm_trace["error"] = "LLM payload failed SystemDesignState validation."
            elif llm_config.fallback_on_error:
                llm_trace["fallback_used"] = True
            else:
                llm_trace["fallback_used"] = True
        if should_block_on_llm_failure(
            llm_config,
            self.stage_name,
            llm_trace["used"],
            llm_trace["fallback_used"],
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
                    llm_trace.get("error", ""),
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
