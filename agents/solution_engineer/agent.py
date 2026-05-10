from __future__ import annotations

import json

from ..base import AgentContext, AgentResult, BaseAgent
from ..common import LLMGateway, PromptContract
from ..common.llm_policy import (
    build_llm_failure_question_state,
    should_use_llm,
)
from ..common.runtime_config import LLMRuntimeConfig, load_llm_runtime_config
from schemas.solution import SolutionState
from .planning import SolutionPlanningMixin
from .questions import SolutionQuestionMixin


class SolutionEngineerAgent(SolutionPlanningMixin, SolutionQuestionMixin, BaseAgent):
    agent_name = "Solution Engineer"
    stage_name = "SOLUTION"
    state_key = "solution"

    def get_llm_runtime_config(self) -> LLMRuntimeConfig:
        return load_llm_runtime_config()

    def get_llm_gateway(self) -> LLMGateway:
        return LLMGateway()

    def run(self, context: AgentContext) -> AgentResult:
        current_state = dict(context.states.get(self.state_key, {}))
        spec = dict(context.states.get("spec", {}))
        user_input = context.user_input.strip()
        answers = self.extract_answers(context)

        if not (
            spec.get("project_goal")
            and spec.get("functional_requirements")
            and spec.get("acceptance_criteria")
        ):
            return AgentResult(
                agent_name=self.agent_name,
                stage_name=self.stage_name,
                state_key=self.state_key,
                updated_state=current_state,
                summary="Solution work is blocked until requirements are stable.",
                notes=[
                    "Raised blocking solution questions because requirements are not ready for technical planning."
                ],
                blockers=["requirements_not_ready"],
                handoff_ready=False,
                question_state_update=self.build_clarifying_questions(),
                requires_user_input=True,
            )

        selected_stack = self.pick_stack(spec, answers, current_state)
        module_mapping = self.build_module_mapping(spec)
        llm_config = self.get_llm_runtime_config()
        llm_trace: dict[str, object] = {}
        llm_success = False
        llm_stage_enabled = should_use_llm(llm_config, self.stage_name)
        if llm_stage_enabled and user_input:
            contract = PromptContract(
                stage_name=self.stage_name,
                system_prompt=(
                    "Return strict JSON only with keys: selected_stack, module_mapping, "
                    "risks, alternatives. selected_stack must contain frontend, backend, "
                    "database, agent_framework, deployment."
                ),
                required_fields=[
                    "selected_stack",
                    "module_mapping",
                    "risks",
                    "alternatives",
                ],
                output_model=SolutionState,
            )
            llm_result = self.get_llm_gateway().generate(
                contract=contract,
                user_prompt=(
                    f"User request: {user_input}\n"
                    "Build solution state from spec JSON:\n"
                    f"{json.dumps(spec, ensure_ascii=False)}"
                ),
                config=llm_config,
            )
            llm_trace = llm_result.to_trace()
            if llm_result.status == "success" and isinstance(llm_result.parsed_output, dict):
                llm_success = True
                payload = llm_result.parsed_output
                if isinstance(payload, dict):
                    candidate_stack = payload.get("selected_stack")
                    candidate_mapping = payload.get("module_mapping")
                    candidate_risks = payload.get("risks")
                    candidate_alternatives = payload.get("alternatives")
                    if isinstance(candidate_stack, dict):
                        selected_stack = {
                            "frontend": str(candidate_stack.get("frontend", "")),
                            "backend": str(candidate_stack.get("backend", "")),
                            "database": str(candidate_stack.get("database", "")),
                            "agent_framework": str(
                                candidate_stack.get("agent_framework", "")
                            ),
                            "deployment": str(candidate_stack.get("deployment", "")),
                        }
                    if isinstance(candidate_mapping, list):
                        module_mapping = [
                            {
                                "module": str(item.get("module", "")),
                                "responsibilities": [
                                    str(x)
                                    for x in item.get("responsibilities", [])
                                    if str(x).strip()
                                ],
                                "covers_requirements": [
                                    str(x)
                                    for x in item.get("covers_requirements", [])
                                    if str(x).strip()
                                ],
                                "depends_on": [
                                    str(x)
                                    for x in item.get("depends_on", [])
                                    if str(x).strip()
                                ],
                                "tech_note": str(item.get("tech_note", "")),
                            }
                            for item in candidate_mapping
                            if isinstance(item, dict)
                        ]
                    risks = (
                        [str(x) for x in candidate_risks if str(x).strip()]
                        if isinstance(candidate_risks, list)
                        else self.build_risks(spec, selected_stack)
                    )
                    alternatives = (
                        [str(x) for x in candidate_alternatives if str(x).strip()]
                        if isinstance(candidate_alternatives, list)
                        else self.build_alternatives(selected_stack)
                    )
            elif llm_result.status in {"fatal_error", "needs_user_input"}:
                return AgentResult(
                    agent_name=self.agent_name,
                    stage_name=self.stage_name,
                    state_key=self.state_key,
                    updated_state=current_state,
                    summary="Solution blocked: LLM output is unavailable.",
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
                    summary="Solution blocked: strict_llm mode requires successful LLM output.",
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
            else:
                risks = self.build_risks(spec, selected_stack)
                alternatives = self.build_alternatives(selected_stack)
        else:
            risks = self.build_risks(spec, selected_stack)
            alternatives = self.build_alternatives(selected_stack)
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
                summary="Solution blocked: strict_llm mode requires successful LLM output.",
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
            "selected_stack": selected_stack,
            "module_mapping": module_mapping,
            "risks": risks,
            "alternatives": alternatives,
        }

        return AgentResult(
            agent_name=self.agent_name,
            stage_name=self.stage_name,
            state_key=self.state_key,
            updated_state=updated_state,
            summary="Solution outline was generated from the current requirements state.",
            notes=[
                "Filled a first-pass technical stack and module mapping for downstream design work."
            ],
            handoff_ready=True,
            diagnostics={"llm_trace": llm_trace},
        )
