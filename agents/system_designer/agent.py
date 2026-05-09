from __future__ import annotations

from ..base import AgentContext, AgentResult, BaseAgent
from .planning import SystemDesignPlanningMixin


class SystemDesignerAgent(SystemDesignPlanningMixin, BaseAgent):
    agent_name = "System Designer"
    stage_name = "DESIGN"
    state_key = "system_design"

    def run(self, context: AgentContext) -> AgentResult:
        current_state = dict(context.states.get(self.state_key, {}))
        solution = dict(context.states.get("solution", {}))
        spec = dict(context.states.get("spec", {}))
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
        )
