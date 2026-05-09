from __future__ import annotations

from ..base import AgentContext, AgentResult, BaseAgent
from .planning import ImplementationPlanningMixin


class ImplementationEngineerAgent(ImplementationPlanningMixin, BaseAgent):
    agent_name = "Implementation Engineer"
    stage_name = "IMPLEMENTATION"
    state_key = "implementation_status"

    def run(self, context: AgentContext) -> AgentResult:
        current_state = dict(context.states.get(self.state_key, {}))
        design = dict(context.states.get("system_design", {}))
        solution = dict(context.states.get("solution", {}))
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

        implementation_status = "blocked" if blockers else "done"
        updated_state = {
            **current_state,
            "module_name": module_name,
            "implementation_status": implementation_status,
            "files_touched": self.build_files_touched(module_name),
            "tests_added_or_updated": self.build_tests_touched(module_name),
            "contract_compliance": contract_compliance,
            "known_limitations": [],
            "blockers": blockers,
        }

        if blockers:
            return AgentResult(
                agent_name=self.agent_name,
                stage_name=self.stage_name,
                state_key=self.state_key,
                updated_state=updated_state,
                summary="Implementation planning is blocked by missing upstream design details.",
                notes=[
                    "Recorded blockers to trigger explicit backflow attribution in orchestrator."
                ],
                blockers=blockers,
                handoff_ready=False,
            )

        return AgentResult(
            agent_name=self.agent_name,
            stage_name=self.stage_name,
            state_key=self.state_key,
            updated_state=updated_state,
            summary="Implementation status was advanced with executable module-level artifacts.",
            notes=[
                "Generated files/tests touchpoints and marked contract-compliant done status for validation."
            ],
            handoff_ready=True,
        )
