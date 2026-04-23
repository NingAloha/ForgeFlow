from __future__ import annotations

from .base import AgentContext, AgentResult, BaseAgent


class SolutionEngineerAgent(BaseAgent):
    agent_name = "Solution Engineer"
    stage_name = "SOLUTION"
    state_key = "solution"

    def run(self, context: AgentContext) -> AgentResult:
        current_state = dict(context.states.get(self.state_key, {}))
        notes = [
            "Placeholder only: no stack selection or module mapping logic yet.",
            "Expected output target is state/solution.json.",
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
