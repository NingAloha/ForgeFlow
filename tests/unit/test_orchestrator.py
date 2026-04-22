from __future__ import annotations

import unittest
from copy import deepcopy

from agents.orchestrator import Orchestrator, Stage


def make_empty_states() -> dict[str, dict]:
    return {
        "spec": {
            "project_goal": "",
            "target_users": [],
            "functional_requirements": [],
            "non_functional_requirements": [],
            "constraints": [],
            "preferences": [],
            "acceptance_criteria": [],
            "open_questions": [],
        },
        "solution": {
            "selected_stack": {
                "frontend": "",
                "backend": "",
                "database": "",
                "agent_framework": "",
                "deployment": "",
            },
            "module_mapping": [],
            "risks": [],
            "alternatives": [],
        },
        "system_design": {
            "project_structure": {
                "directories": [],
                "modules": [],
            },
            "contracts": [],
            "data_flow": [],
            "mvp_plan": {
                "in_scope": [],
                "out_of_scope": [],
                "milestones": [],
                "first_deliverable": "",
            },
        },
        "implementation_status": {
            "module_name": "",
            "implementation_status": "not_started",
            "files_touched": [],
            "tests_added_or_updated": [],
            "contract_compliance": True,
            "known_limitations": [],
            "blockers": [],
        },
        "test_report": {
            "test_scope": "integration",
            "result": "not_run",
            "issues": [],
        },
    }


def make_requirements_ready_states() -> dict[str, dict]:
    states = make_empty_states()
    states["spec"].update(
        {
            "project_goal": "Build a chat-first engineering workflow.",
            "functional_requirements": [
                "Collect requirements",
                "Generate solution and design artifacts",
            ],
            "acceptance_criteria": [
                "The system can persist structured workflow states."
            ],
        }
    )
    return states


def make_solution_ready_states() -> dict[str, dict]:
    states = make_requirements_ready_states()
    states["solution"] = {
        "selected_stack": {
            "frontend": "Textual",
            "backend": "Python",
            "database": "JSON files",
            "agent_framework": "Custom orchestrator",
            "deployment": "Local CLI",
        },
        "module_mapping": [
            {
                "module": "orchestrator",
                "responsibilities": ["Stage evaluation", "Agent dispatch"],
                "covers_requirements": [
                    "Collect requirements",
                    "Generate solution and design artifacts",
                ],
                "depends_on": ["state_manager"],
                "tech_note": "",
            }
        ],
        "risks": [],
        "alternatives": [],
    }
    return states


def make_design_ready_states() -> dict[str, dict]:
    states = make_solution_ready_states()
    states["system_design"] = {
        "project_structure": {
            "directories": ["agents/", "state/", "docs/"],
            "modules": ["orchestrator", "state_manager"],
        },
        "contracts": [
            {
                "name": "requirements_to_solution_state",
                "contract_type": "state_handoff",
                "producer": "Requirements Engineer",
                "consumers": ["Solution Engineer"],
                "input": [
                    {
                        "name": "spec_state",
                        "description": "Structured requirements state",
                        "required": True,
                    }
                ],
                "output": [
                    {
                        "name": "solution_state",
                        "description": "Structured solution state",
                        "required": True,
                    }
                ],
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
                "trigger": "Requirements approved",
                "notes": "",
            }
        ],
        "mvp_plan": {
            "in_scope": ["Workflow state machine"],
            "out_of_scope": [],
            "milestones": [],
            "first_deliverable": "Current stage computation",
        },
    }
    return states


def make_implementing_states() -> dict[str, dict]:
    states = make_design_ready_states()
    states["implementation_status"].update(
        {
            "module_name": "orchestrator",
            "implementation_status": "in_progress",
        }
    )
    return states


def make_testing_states() -> dict[str, dict]:
    states = make_design_ready_states()
    states["implementation_status"].update(
        {
            "module_name": "orchestrator",
            "implementation_status": "done",
            "blockers": [],
        }
    )
    states["test_report"].update(
        {
            "test_scope": "integration",
            "result": "not_run",
            "issues": [],
        }
    )
    return states


def make_done_states() -> dict[str, dict]:
    states = make_testing_states()
    states["test_report"].update(
        {
            "result": "pass",
            "issues": [
                {
                    "title": "Minor copy issue",
                    "severity": "low",
                    "status": "open",
                    "related_modules": ["orchestrator"],
                    "related_contracts": [],
                    "notes": "",
                }
            ],
        }
    )
    return states


class OrchestratorStageComputationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = Orchestrator()

    def test_empty_states_resolve_to_init(self) -> None:
        states = make_empty_states()
        self.assertEqual(self.orchestrator.compute_current_stage(states), Stage.INIT)

    def test_requirements_ready_states_resolve_to_requirements_ready(self) -> None:
        states = make_requirements_ready_states()
        self.assertTrue(self.orchestrator.is_requirements_ready(states))
        self.assertEqual(
            self.orchestrator.compute_current_stage(states),
            Stage.REQUIREMENTS_READY,
        )

    def test_solution_ready_states_resolve_to_solution_ready(self) -> None:
        states = make_solution_ready_states()
        self.assertTrue(self.orchestrator.is_solution_ready(states))
        self.assertEqual(
            self.orchestrator.compute_current_stage(states),
            Stage.SOLUTION_READY,
        )

    def test_design_ready_states_resolve_to_design_ready(self) -> None:
        states = make_design_ready_states()
        self.assertTrue(self.orchestrator.is_design_ready(states))
        self.assertEqual(
            self.orchestrator.compute_current_stage(states),
            Stage.DESIGN_READY,
        )

    def test_implementing_states_resolve_to_implementing(self) -> None:
        states = make_implementing_states()
        self.assertTrue(self.orchestrator.is_implementing(states))
        self.assertEqual(
            self.orchestrator.compute_current_stage(states),
            Stage.IMPLEMENTING,
        )

    def test_testing_states_resolve_to_testing(self) -> None:
        states = make_testing_states()
        self.assertTrue(self.orchestrator.is_testing(states))
        self.assertEqual(
            self.orchestrator.compute_current_stage(states),
            Stage.TESTING,
        )

    def test_done_states_resolve_to_done(self) -> None:
        states = make_done_states()
        self.assertTrue(self.orchestrator.is_done(states))
        self.assertEqual(self.orchestrator.compute_current_stage(states), Stage.DONE)

    def test_high_severity_open_issue_blocks_done(self) -> None:
        states = make_done_states()
        states["test_report"]["issues"] = [
            {
                "title": "Main flow broken",
                "severity": "critical",
                "status": "open",
                "related_modules": ["orchestrator"],
                "related_contracts": [],
                "notes": "",
            }
        ]
        self.assertFalse(self.orchestrator.is_done(states))
        self.assertEqual(
            self.orchestrator.compute_current_stage(states),
            Stage.TESTING,
        )

    def test_blocked_implementation_does_not_enter_testing(self) -> None:
        states = make_design_ready_states()
        states["implementation_status"].update(
            {
                "module_name": "orchestrator",
                "implementation_status": "blocked",
                "blockers": ["Need API shape clarification"],
            }
        )
        self.assertTrue(self.orchestrator.is_implementing(states))
        self.assertFalse(self.orchestrator.is_testing(states))
        self.assertEqual(
            self.orchestrator.compute_current_stage(states),
            Stage.IMPLEMENTING,
        )

    def test_missing_valid_contract_reference_prevents_design_ready(self) -> None:
        states = make_design_ready_states()
        broken_states = deepcopy(states)
        broken_states["system_design"]["data_flow"][0]["contract_name"] = "missing"
        self.assertFalse(self.orchestrator.is_design_ready(broken_states))
        self.assertEqual(
            self.orchestrator.compute_current_stage(broken_states),
            Stage.SOLUTION_READY,
        )

    def test_resolve_transition_stays_on_init_for_empty_states(self) -> None:
        decision = self.orchestrator.resolve_transition(make_empty_states())
        self.assertEqual(decision.computed_stage, Stage.INIT)
        self.assertEqual(decision.final_stage, Stage.INIT)
        self.assertTrue(decision.should_stay)

    def test_resolve_transition_stays_on_solution_when_design_not_ready(self) -> None:
        decision = self.orchestrator.resolve_transition(make_solution_ready_states())
        self.assertEqual(decision.computed_stage, Stage.SOLUTION_READY)
        self.assertEqual(decision.final_stage, Stage.SOLUTION_READY)
        self.assertIsNone(decision.forward_target)
        self.assertTrue(decision.should_stay)

    def test_resolve_transition_backflows_testing_failure_to_implementing(self) -> None:
        states = make_testing_states()
        states["test_report"].update(
            {
                "result": "fail",
                "issues": [
                    {
                        "title": "Broken logic",
                        "severity": "critical",
                        "status": "open",
                        "related_modules": ["orchestrator"],
                        "related_contracts": [],
                        "notes": "",
                    }
                ],
            }
        )
        decision = self.orchestrator.resolve_transition(states)
        self.assertEqual(decision.computed_stage, Stage.TESTING)
        self.assertEqual(decision.final_stage, Stage.IMPLEMENTING)
        self.assertEqual(decision.backflow_target, Stage.IMPLEMENTING)
        self.assertFalse(decision.should_stay)

    def test_resolve_transition_backflows_contract_failure_to_design(self) -> None:
        states = make_testing_states()
        states["test_report"].update(
            {
                "result": "fail",
                "issues": [
                    {
                        "title": "Contract mismatch",
                        "severity": "critical",
                        "status": "confirmed",
                        "related_modules": ["orchestrator", "state_manager"],
                        "related_contracts": ["requirements_to_solution_state"],
                        "notes": "",
                    }
                ],
            }
        )
        decision = self.orchestrator.resolve_transition(states)
        self.assertEqual(decision.computed_stage, Stage.TESTING)
        self.assertEqual(decision.final_stage, Stage.DESIGN_READY)
        self.assertEqual(decision.backflow_target, Stage.DESIGN_READY)
        self.assertFalse(decision.should_stay)

    def test_resolve_transition_keeps_execution_blocker_in_implementing(self) -> None:
        states = make_design_ready_states()
        states["implementation_status"].update(
            {
                "module_name": "orchestrator",
                "implementation_status": "blocked",
                "blockers": ["Local dependency install is failing in the environment."],
            }
        )
        decision = self.orchestrator.resolve_transition(states)
        self.assertEqual(decision.computed_stage, Stage.IMPLEMENTING)
        self.assertEqual(decision.final_stage, Stage.IMPLEMENTING)
        self.assertTrue(decision.should_stay)

    def test_resolve_transition_backflows_implementing_to_solution(self) -> None:
        states = make_design_ready_states()
        states["implementation_status"].update(
            {
                "module_name": "orchestrator",
                "implementation_status": "blocked",
                "blockers": ["Module responsibility and architecture ownership are unclear."],
            }
        )
        decision = self.orchestrator.resolve_transition(states)
        self.assertEqual(decision.computed_stage, Stage.IMPLEMENTING)
        self.assertEqual(decision.final_stage, Stage.SOLUTION_READY)
        self.assertEqual(decision.backflow_target, Stage.SOLUTION_READY)

    def test_resolve_transition_backflows_implementing_to_requirements(self) -> None:
        states = make_design_ready_states()
        states["spec"]["acceptance_criteria"] = []
        states["solution"] = make_solution_ready_states()["solution"]
        states["system_design"] = make_design_ready_states()["system_design"]
        states["implementation_status"].update(
            {
                "module_name": "orchestrator",
                "implementation_status": "blocked",
                "blockers": ["Acceptance criteria are unclear for this feature."],
            }
        )
        decision = self.orchestrator.resolve_transition(states)
        self.assertEqual(decision.computed_stage, Stage.INIT)
        self.assertEqual(decision.final_stage, Stage.INIT)
        self.assertEqual(decision.backflow_target, Stage.REQUIREMENTS_READY)

    def test_design_backflows_to_solution_when_solution_is_not_ready(self) -> None:
        states = make_design_ready_states()
        states["solution"]["module_mapping"] = []
        decision = self.orchestrator.resolve_transition(states)
        self.assertEqual(decision.computed_stage, Stage.REQUIREMENTS_READY)
        self.assertEqual(decision.final_stage, Stage.REQUIREMENTS_READY)
        self.assertEqual(decision.backflow_target, Stage.SOLUTION_READY)

    def test_solution_backflows_to_requirements_when_requirements_break(self) -> None:
        states = make_solution_ready_states()
        states["spec"]["functional_requirements"] = []
        decision = self.orchestrator.resolve_transition(states)
        self.assertEqual(decision.computed_stage, Stage.INIT)
        self.assertEqual(decision.final_stage, Stage.INIT)
        self.assertEqual(decision.backflow_target, Stage.REQUIREMENTS_READY)

    def test_orchestrate_executes_requirements_stage_for_empty_states(self) -> None:
        class StubStateManager:
            def __init__(self) -> None:
                self.states = make_empty_states()

            def load_all_states(self) -> dict[str, dict]:
                return deepcopy(self.states)

            def save_state(self, state_key: str, payload: dict) -> None:
                self.states[state_key] = deepcopy(payload)

        orchestrator = Orchestrator(state_manager=StubStateManager())
        result = orchestrator.orchestrate("build me a workflow")
        self.assertEqual(result.decision.final_stage, Stage.INIT)
        self.assertEqual(result.executed_stage, Stage.REQUIREMENTS_READY)
        self.assertIsNotNone(result.agent_result)

    def test_orchestrate_does_not_execute_agent_when_done(self) -> None:
        class StubStateManager:
            def __init__(self) -> None:
                self.states = make_done_states()

            def load_all_states(self) -> dict[str, dict]:
                return deepcopy(self.states)

            def save_state(self, state_key: str, payload: dict) -> None:
                self.states[state_key] = deepcopy(payload)

        orchestrator = Orchestrator(state_manager=StubStateManager())
        result = orchestrator.orchestrate()
        self.assertEqual(result.decision.final_stage, Stage.DONE)
        self.assertIsNone(result.executed_stage)
        self.assertIsNone(result.agent_result)


if __name__ == "__main__":
    unittest.main()
