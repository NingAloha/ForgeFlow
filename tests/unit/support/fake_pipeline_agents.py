from __future__ import annotations

from agents.base import AgentContext, AgentResult, BaseAgent


class FakeRequirementsAgent(BaseAgent):
    agent_name = "Requirements Engineer"
    stage_name = "REQUIREMENTS"
    state_key = "spec"

    def run(self, context: AgentContext) -> AgentResult:
        prompt = context.user_input.strip() or "offline task"
        updated = {
            **context.states.get("spec", {}),
            "project_goal": f"Deliver: {prompt}",
            "functional_requirements": [
                "Collect user input",
                "Produce deterministic workflow artifacts",
            ],
            "acceptance_criteria": [
                "Pipeline reaches DONE without user blocking",
            ],
            "open_questions": [],
        }
        return AgentResult(
            agent_name=self.agent_name,
            stage_name=self.stage_name,
            state_key=self.state_key,
            updated_state=updated,
            summary="Fake requirements output generated.",
            handoff_ready=True,
        )


class FakeSolutionAgent(BaseAgent):
    agent_name = "Solution Engineer"
    stage_name = "SOLUTION"
    state_key = "solution"

    def run(self, context: AgentContext) -> AgentResult:
        requirements = list(context.states.get("spec", {}).get("functional_requirements", []))
        updated = {
            **context.states.get("solution", {}),
            "selected_stack": {
                "frontend": "CLI",
                "backend": "Python",
                "database": "JSON",
                "agent_framework": "ForgeFlow",
                "deployment": "local",
            },
            "module_mapping": [
                {
                    "module": "workflow_core",
                    "responsibilities": ["orchestrate stages", "persist state"],
                    "covers_requirements": requirements,
                    "depends_on": ["state_manager"],
                    "tech_note": "offline fixture",
                }
            ],
            "risks": [],
            "alternatives": [],
        }
        return AgentResult(
            agent_name=self.agent_name,
            stage_name=self.stage_name,
            state_key=self.state_key,
            updated_state=updated,
            summary="Fake solution output generated.",
            handoff_ready=True,
        )


class FakeDesignAgent(BaseAgent):
    agent_name = "System Designer"
    stage_name = "DESIGN"
    state_key = "system_design"

    def run(self, context: AgentContext) -> AgentResult:
        updated = {
            **context.states.get("system_design", {}),
            "project_structure": {
                "directories": ["app/", "tests/"],
                "modules": ["workflow_core", "state_manager"],
            },
            "contracts": [
                {
                    "name": "requirements_to_solution_state",
                    "contract_type": "state_handoff",
                    "producer": "Requirements Engineer",
                    "consumers": ["Solution Engineer"],
                    "input": [{"name": "spec_state", "description": "", "required": True}],
                    "output": [{"name": "solution_state", "description": "", "required": True}],
                    "constraints": [],
                    "acceptance_criteria": [],
                    "failure_handling": [],
                }
            ],
            "data_flow": [
                {
                    "step": 1,
                    "contract_name": "requirements_to_solution_state",
                    "from": "Requirements Engineer",
                    "to": ["Solution Engineer"],
                    "trigger": "requirements_ready",
                    "notes": "offline fixture",
                }
            ],
            "mvp_plan": {
                "in_scope": ["offline pipeline validation"],
                "out_of_scope": [],
                "milestones": ["reach done"],
                "first_deliverable": "state progression",
            },
        }
        return AgentResult(
            agent_name=self.agent_name,
            stage_name=self.stage_name,
            state_key=self.state_key,
            updated_state=updated,
            summary="Fake design output generated.",
            handoff_ready=True,
        )


class FakeImplementationAgent(BaseAgent):
    agent_name = "Implementation Engineer"
    stage_name = "IMPLEMENTATION"
    state_key = "implementation_status"

    def run(self, context: AgentContext) -> AgentResult:
        updated = {
            **context.states.get("implementation_status", {}),
            "module_name": "workflow_core",
            "implementation_status": "done",
            "files_touched": ["app/main.py"],
            "tests_added_or_updated": ["tests/test_smoke.py"],
            "contract_compliance": True,
            "known_limitations": [],
            "blockers": [],
            "workspace_path": "/tmp/forgeflow-offline-fixture",
            "commands_executed": [],
            "artifacts_generated": [],
            "suggested_test_command": [
                "python3",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                "test_*.py",
                "-v",
            ],
        }
        return AgentResult(
            agent_name=self.agent_name,
            stage_name=self.stage_name,
            state_key=self.state_key,
            updated_state=updated,
            summary="Fake implementation output generated.",
            handoff_ready=True,
        )


class FakeTestingAgent(BaseAgent):
    agent_name = "Test & Validation Engineer"
    stage_name = "TESTING"
    state_key = "test_report"

    def run(self, context: AgentContext) -> AgentResult:
        updated = {
            **context.states.get("test_report", {}),
            "test_scope": "integration",
            "result": "pass",
            "issues": [],
            "command": [
                "python3",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                "test_*.py",
                "-v",
            ],
            "exit_code": 0,
            "tests_run": 1,
            "failed_tests": [],
            "log_excerpt": "offline fixture passed",
        }
        return AgentResult(
            agent_name=self.agent_name,
            stage_name=self.stage_name,
            state_key=self.state_key,
            updated_state=updated,
            summary="Fake testing output generated.",
            handoff_ready=True,
        )
