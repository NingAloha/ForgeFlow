from __future__ import annotations

from ..base import AgentContext, AgentResult, BaseAgent
from .planning import TestValidationPlanningMixin


class TestValidationEngineerAgent(TestValidationPlanningMixin, BaseAgent):
    agent_name = "Test & Validation Engineer"
    stage_name = "TESTING"
    state_key = "test_report"

    def run(self, context: AgentContext) -> AgentResult:
        current_state = dict(context.states.get(self.state_key, {}))
        spec = dict(context.states.get("spec", {}))
        implementation_status = dict(context.states.get("implementation_status", {}))
        design = dict(context.states.get("system_design", {}))
        issues = self.build_issues(spec, implementation_status, design)
        updated_state = {
            **current_state,
            "test_scope": current_state.get("test_scope") or "workflow_integration",
            "result": self.pick_result(issues, implementation_status),
            "issues": issues,
        }
        blockers = [
            str(issue.get("title", ""))
            for issue in issues
            if issue.get("severity") in {"critical", "high"}
            and issue.get("status") in {"open", "confirmed"}
        ]
        return AgentResult(
            agent_name=self.agent_name,
            stage_name=self.stage_name,
            state_key=self.state_key,
            updated_state=updated_state,
            summary="Validation report was generated with issue attribution for backflow decisions.",
            notes=[
                "Produced executable test_report.result and structured issues for root-cause routing."
            ],
            blockers=blockers,
            handoff_ready=updated_state["result"] == "pass",
        )
