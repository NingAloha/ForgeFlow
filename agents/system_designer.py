from __future__ import annotations

from .base import AgentContext, AgentResult, BaseAgent


class SystemDesignerAgent(BaseAgent):
    agent_name = "System Designer"
    stage_name = "DESIGN"
    state_key = "system_design"

    def run(self, context: AgentContext) -> AgentResult:
        current_state = dict(context.states.get(self.state_key, {}))
        notes = [
            "Placeholder only: no structure, contract, or flow generation yet.",
            "Expected output target is state/system_design.json.",
        ]
        return AgentResult(
            agent_name=self.agent_name,
            stage_name=self.stage_name,
            state_key=self.state_key,
            updated_state=current_state,
            summary=self.build_placeholder_summary(),
            notes=notes,
            handoff_ready=False,
        )
