from __future__ import annotations

from ..base import AgentContext, AgentResult, BaseAgent


class ImplementationEngineerAgent(BaseAgent):
    agent_name = "Implementation Engineer"
    stage_name = "IMPLEMENTATION"
    state_key = "implementation_status"

    def run(self, context: AgentContext) -> AgentResult:
        current_state = dict(context.states.get(self.state_key, {}))
        notes = [
            "Placeholder only: no code generation or blocker analysis yet.",
            "Expected output target is state/implementation_status.json.",
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
