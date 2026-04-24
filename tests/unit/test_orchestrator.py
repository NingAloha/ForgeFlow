from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from agents.base import (
    AgentContext,
    AgentResult,
    BaseAgent,
    QuestionAnswer,
    QuestionItem,
    QuestionOption,
    QuestionState,
)
from agents.requirements_engineer import RequirementsEngineerAgent
from agents.orchestrator import Orchestrator, Stage
from agents.state_manager import StateManager


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
        "question_state": {
            "status": "idle",
            "stage_name": "",
            "state_key": "",
            "blocking": False,
            "questions": [],
            "created_by": "",
            "resolution_summary": "",
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
            Stage.REQUIREMENTS,
        )

    def test_solution_ready_states_resolve_to_solution_ready(self) -> None:
        states = make_solution_ready_states()
        self.assertTrue(self.orchestrator.is_solution_ready(states))
        self.assertEqual(
            self.orchestrator.compute_current_stage(states),
            Stage.SOLUTION,
        )

    def test_design_ready_states_resolve_to_design_ready(self) -> None:
        states = make_design_ready_states()
        self.assertTrue(self.orchestrator.is_design_ready(states))
        self.assertEqual(
            self.orchestrator.compute_current_stage(states),
            Stage.DESIGN,
        )

    def test_implementing_states_resolve_to_implementing(self) -> None:
        states = make_implementing_states()
        self.assertTrue(self.orchestrator.has_active_implementation(states))
        self.assertEqual(
            self.orchestrator.compute_current_stage(states),
            Stage.IMPLEMENTATION,
        )

    def test_testing_states_resolve_to_testing(self) -> None:
        states = make_testing_states()
        self.assertTrue(self.orchestrator.has_validation_context(states))
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
        self.assertTrue(self.orchestrator.has_active_implementation(states))
        self.assertFalse(self.orchestrator.has_validation_context(states))
        self.assertEqual(
            self.orchestrator.compute_current_stage(states),
            Stage.IMPLEMENTATION,
        )

    def test_missing_valid_contract_reference_prevents_design_ready(self) -> None:
        states = make_design_ready_states()
        broken_states = deepcopy(states)
        broken_states["system_design"]["data_flow"][0]["contract_name"] = "missing"
        self.assertFalse(self.orchestrator.is_design_ready(broken_states))
        self.assertEqual(
            self.orchestrator.compute_current_stage(broken_states),
            Stage.SOLUTION,
        )

    def test_resolve_transition_stays_on_init_for_empty_states(self) -> None:
        decision = self.orchestrator.resolve_transition(make_empty_states())
        self.assertEqual(decision.computed_stage, Stage.INIT)
        self.assertEqual(decision.final_stage, Stage.INIT)
        self.assertTrue(decision.should_stay)

    def test_resolve_transition_stays_on_solution_when_design_not_ready(self) -> None:
        decision = self.orchestrator.resolve_transition(make_solution_ready_states())
        self.assertEqual(decision.computed_stage, Stage.SOLUTION)
        self.assertEqual(decision.final_stage, Stage.SOLUTION)
        self.assertIsNone(decision.forward_target)
        self.assertTrue(decision.should_stay)

    def test_resolve_transition_waits_on_blocking_question_state(self) -> None:
        states = make_requirements_ready_states()
        states["question_state"] = {
            "status": "awaiting_user",
            "stage_name": "REQUIREMENTS",
            "state_key": "spec",
            "blocking": True,
            "questions": [
                {
                    "id": "scope-choice",
                    "title": "Pick initial scope",
                    "description": "Need one direction before solution work.",
                    "response_type": "single_select",
                    "options": [],
                    "allow_free_text": False,
                    "answer": None,
                }
            ],
            "created_by": "Requirements Engineer",
            "resolution_summary": "",
        }
        decision = self.orchestrator.resolve_transition(states)
        self.assertTrue(decision.wait_for_user_input)
        self.assertTrue(decision.should_stay)
        self.assertEqual(decision.final_stage, Stage.REQUIREMENTS)
        self.assertIsNone(self.orchestrator.determine_execution_stage(decision))

    def test_resolve_transition_does_not_wait_on_answered_blocking_question_state(self) -> None:
        states = make_requirements_ready_states()
        states["question_state"] = {
            "status": "answered",
            "stage_name": "REQUIREMENTS",
            "state_key": "spec",
            "blocking": True,
            "questions": [
                {
                    "id": "scope-choice",
                    "title": "Pick initial scope",
                    "description": "Need one direction before solution work.",
                    "response_type": "single_select",
                    "options": [],
                    "allow_free_text": False,
                    "answer": {
                        "selected_values": ["mvp"],
                        "free_text": "",
                    },
                }
            ],
            "created_by": "Requirements Engineer",
            "resolution_summary": "",
        }
        decision = self.orchestrator.resolve_transition(states)
        self.assertFalse(decision.wait_for_user_input)
        self.assertTrue(decision.should_stay)
        self.assertEqual(decision.final_stage, Stage.REQUIREMENTS)
        self.assertEqual(
            self.orchestrator.determine_execution_stage(decision),
            Stage.REQUIREMENTS,
        )

    def test_resolve_transition_does_not_wait_when_question_state_is_non_blocking(self) -> None:
        states = make_requirements_ready_states()
        states["question_state"] = {
            "status": "awaiting_user",
            "stage_name": "REQUIREMENTS",
            "state_key": "spec",
            "blocking": False,
            "questions": [
                {
                    "id": "optional-note",
                    "title": "Optional preference",
                    "description": "Nice to know but not required.",
                    "response_type": "free_text",
                    "options": [],
                    "allow_free_text": True,
                    "answer": None,
                }
            ],
            "created_by": "Requirements Engineer",
            "resolution_summary": "",
        }
        decision = self.orchestrator.resolve_transition(states)
        self.assertFalse(decision.wait_for_user_input)
        self.assertEqual(decision.final_stage, Stage.REQUIREMENTS)

    def test_resolve_transition_does_not_wait_when_blocking_question_list_is_empty(self) -> None:
        states = make_requirements_ready_states()
        states["question_state"] = {
            "status": "awaiting_user",
            "stage_name": "REQUIREMENTS",
            "state_key": "spec",
            "blocking": True,
            "questions": [],
            "created_by": "Requirements Engineer",
            "resolution_summary": "",
        }
        decision = self.orchestrator.resolve_transition(states)
        self.assertFalse(decision.wait_for_user_input)
        self.assertEqual(decision.final_stage, Stage.REQUIREMENTS)

    def test_resolve_transition_falls_back_to_source_stage_for_invalid_question_stage(self) -> None:
        states = make_testing_states()
        states["question_state"] = {
            "status": "awaiting_user",
            "stage_name": "NOT_A_STAGE",
            "state_key": "spec",
            "blocking": True,
            "questions": [
                {
                    "id": "broken-stage",
                    "title": "Clarify expectation",
                    "description": "Malformed stage marker should not crash.",
                    "response_type": "free_text",
                    "options": [],
                    "allow_free_text": True,
                    "answer": None,
                }
            ],
            "created_by": "Requirements Engineer",
            "resolution_summary": "",
        }
        decision = self.orchestrator.resolve_transition(states)
        self.assertTrue(decision.wait_for_user_input)
        self.assertEqual(decision.source_stage, Stage.TESTING)
        self.assertEqual(decision.final_stage, Stage.TESTING)

    def test_parse_question_state_handles_nested_options_and_answers(self) -> None:
        payload = {
            "status": "answered",
            "stage_name": "SOLUTION",
            "state_key": "solution",
            "blocking": True,
            "questions": [
                {
                    "id": "stack-choice",
                    "title": "Pick backend",
                    "description": "Need a backend to proceed.",
                    "response_type": "mixed",
                    "options": [
                        {
                            "label": "Python",
                            "value": "python",
                            "hint": "Fastest path in this repo.",
                        }
                    ],
                    "allow_free_text": True,
                    "answer": {
                        "selected_values": ["python"],
                        "free_text": "Prefer standard library first.",
                    },
                }
            ],
            "created_by": "Solution Engineer",
            "resolution_summary": "User picked Python.",
        }

        question_state = self.orchestrator.parse_question_state(payload)

        self.assertEqual(question_state.status, "answered")
        self.assertEqual(question_state.stage_name, "SOLUTION")
        self.assertEqual(len(question_state.questions), 1)
        self.assertEqual(question_state.questions[0].options[0].value, "python")
        self.assertEqual(
            question_state.questions[0].answer.selected_values, ["python"]
        )
        self.assertEqual(
            question_state.questions[0].answer.free_text,
            "Prefer standard library first.",
        )

    def test_serialize_question_state_none_returns_idle_payload(self) -> None:
        payload = self.orchestrator.serialize_question_state(None)
        self.assertEqual(payload, make_empty_states()["question_state"])

    def test_serialize_question_state_preserves_nested_question_fields(self) -> None:
        question_state = QuestionState(
            status="answered",
            stage_name="SOLUTION",
            state_key="solution",
            blocking=True,
            questions=[
                QuestionItem(
                    id="stack-choice",
                    title="Pick backend",
                    description="Need a backend to proceed.",
                    response_type="mixed",
                    options=[
                        QuestionOption(
                            label="Python",
                            value="python",
                            hint="Fastest path in this repo.",
                        )
                    ],
                    allow_free_text=True,
                    answer=QuestionAnswer(
                        selected_values=["python"],
                        free_text="Prefer standard library first.",
                    ),
                )
            ],
            created_by="Solution Engineer",
            resolution_summary="User picked Python.",
        )

        payload = self.orchestrator.serialize_question_state(question_state)

        self.assertEqual(payload["questions"][0]["options"][0]["label"], "Python")
        self.assertEqual(
            payload["questions"][0]["answer"]["selected_values"], ["python"]
        )
        self.assertEqual(payload["resolution_summary"], "User picked Python.")

    def test_run_stage_saves_question_state_update(self) -> None:
        state_manager = InMemoryStateManager(make_empty_states())
        orchestrator = Orchestrator(state_manager=state_manager)
        orchestrator.agents[Stage.REQUIREMENTS] = QuestionAskingAgent()

        result = orchestrator.run_stage(Stage.REQUIREMENTS)

        self.assertTrue(result.requires_user_input)
        self.assertIn("question_state", state_manager.saved_states)
        saved_question_state = state_manager.saved_states["question_state"]
        self.assertEqual(saved_question_state["status"], "awaiting_user")
        self.assertEqual(saved_question_state["stage_name"], "REQUIREMENTS")
        self.assertEqual(saved_question_state["questions"][0]["id"], "target-user")

    def test_run_stage_without_question_update_does_not_write_question_state(self) -> None:
        state_manager = InMemoryStateManager(make_empty_states())
        orchestrator = Orchestrator(state_manager=state_manager)

        orchestrator.run_stage(
            Stage.REQUIREMENTS,
            user_input=(
                "Build a workflow assistant that collects requirements and "
                "generates implementation plans."
            ),
        )

        self.assertNotIn("question_state", state_manager.saved_states)
        self.assertIn("spec", state_manager.saved_states)

    def test_run_stage_clears_answered_question_state_after_same_stage_consumes_it(self) -> None:
        states = make_empty_states()
        states["question_state"] = {
            "status": "answered",
            "stage_name": "REQUIREMENTS",
            "state_key": "spec",
            "blocking": True,
            "questions": [
                {
                    "id": "target-user",
                    "title": "Who is the first target user?",
                    "description": "Need one concrete initial user persona.",
                    "response_type": "single_select",
                    "options": [],
                    "allow_free_text": True,
                    "answer": {
                        "selected_values": ["indie_hacker"],
                        "free_text": "Solo builder first.",
                    },
                }
            ],
            "created_by": "Requirements Engineer",
            "resolution_summary": "",
        }
        state_manager = InMemoryStateManager(states)
        orchestrator = Orchestrator(state_manager=state_manager)
        orchestrator.agents[Stage.REQUIREMENTS] = AnswerConsumingAgent()

        orchestrator.run_stage(Stage.REQUIREMENTS)

        self.assertIn("question_state", state_manager.saved_states)
        self.assertEqual(
            state_manager.saved_states["question_state"],
            make_empty_states()["question_state"],
        )

    def test_run_stage_does_not_clear_answered_question_state_for_other_stage(self) -> None:
        states = make_empty_states()
        states["question_state"] = {
            "status": "answered",
            "stage_name": "SOLUTION",
            "state_key": "solution",
            "blocking": True,
            "questions": [
                {
                    "id": "stack-choice",
                    "title": "Pick backend",
                    "description": "Need a backend to proceed.",
                    "response_type": "single_select",
                    "options": [],
                    "allow_free_text": False,
                    "answer": {
                        "selected_values": ["python"],
                        "free_text": "",
                    },
                }
            ],
            "created_by": "Solution Engineer",
            "resolution_summary": "",
        }
        state_manager = InMemoryStateManager(states)
        orchestrator = Orchestrator(state_manager=state_manager)
        orchestrator.agents[Stage.REQUIREMENTS] = AnswerConsumingAgent()

        orchestrator.run_stage(Stage.REQUIREMENTS)

        self.assertNotIn("question_state", state_manager.saved_states)

    def test_run_stage_does_not_clear_answered_question_state_when_agent_reasks(self) -> None:
        states = make_empty_states()
        states["question_state"] = {
            "status": "answered",
            "stage_name": "REQUIREMENTS",
            "state_key": "spec",
            "blocking": True,
            "questions": [
                {
                    "id": "target-user",
                    "title": "Who is the first target user?",
                    "description": "Need one concrete initial user persona.",
                    "response_type": "single_select",
                    "options": [],
                    "allow_free_text": True,
                    "answer": {
                        "selected_values": [],
                        "free_text": "Need more constraints.",
                    },
                }
            ],
            "created_by": "Requirements Engineer",
            "resolution_summary": "",
        }
        state_manager = InMemoryStateManager(states)
        orchestrator = Orchestrator(state_manager=state_manager)
        orchestrator.agents[Stage.REQUIREMENTS] = ReaskingAgent()

        orchestrator.run_stage(Stage.REQUIREMENTS)

        self.assertIn("question_state", state_manager.saved_states)
        self.assertEqual(
            state_manager.saved_states["question_state"]["status"],
            "awaiting_user",
        )

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
        self.assertEqual(decision.final_stage, Stage.IMPLEMENTATION)
        self.assertEqual(decision.backflow_target, Stage.IMPLEMENTATION)
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
        self.assertEqual(decision.final_stage, Stage.DESIGN)
        self.assertEqual(decision.backflow_target, Stage.DESIGN)
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
        self.assertEqual(decision.computed_stage, Stage.IMPLEMENTATION)
        self.assertEqual(decision.final_stage, Stage.IMPLEMENTATION)
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
        self.assertEqual(decision.computed_stage, Stage.IMPLEMENTATION)
        self.assertEqual(decision.final_stage, Stage.SOLUTION)
        self.assertEqual(decision.backflow_target, Stage.SOLUTION)

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
        self.assertEqual(decision.backflow_target, Stage.REQUIREMENTS)

    def test_design_backflows_to_solution_when_solution_is_not_ready(self) -> None:
        states = make_design_ready_states()
        states["solution"]["module_mapping"] = []
        decision = self.orchestrator.resolve_transition(states)
        self.assertEqual(decision.computed_stage, Stage.REQUIREMENTS)
        self.assertEqual(decision.final_stage, Stage.REQUIREMENTS)
        self.assertEqual(decision.backflow_target, Stage.SOLUTION)

    def test_solution_backflows_to_requirements_when_requirements_break(self) -> None:
        states = make_solution_ready_states()
        states["spec"]["functional_requirements"] = []
        decision = self.orchestrator.resolve_transition(states)
        self.assertEqual(decision.computed_stage, Stage.INIT)
        self.assertEqual(decision.final_stage, Stage.INIT)
        self.assertEqual(decision.backflow_target, Stage.REQUIREMENTS)

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
        self.assertEqual(result.executed_stage, Stage.REQUIREMENTS)
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

    def test_orchestrate_executes_answered_question_stage_for_consumption(self) -> None:
        states = make_empty_states()
        states["question_state"] = {
            "status": "answered",
            "stage_name": "REQUIREMENTS",
            "state_key": "spec",
            "blocking": True,
            "questions": [
                {
                    "id": "target-user",
                    "title": "Who is the first target user?",
                    "description": "Need one concrete initial user persona.",
                    "response_type": "single_select",
                    "options": [],
                    "allow_free_text": True,
                    "answer": {
                        "selected_values": ["indie_hacker"],
                        "free_text": "Solo builder first.",
                    },
                }
            ],
            "created_by": "Requirements Engineer",
            "resolution_summary": "",
        }

        state_manager = InMemoryStateManager(states)
        orchestrator = Orchestrator(state_manager=state_manager)
        orchestrator.agents[Stage.REQUIREMENTS] = AnswerConsumingAgent()

        result = orchestrator.orchestrate()

        self.assertEqual(result.decision.final_stage, Stage.INIT)
        self.assertEqual(result.executed_stage, Stage.REQUIREMENTS)
        self.assertIsNotNone(result.agent_result)
        self.assertEqual(
            state_manager.states["question_state"],
            make_empty_states()["question_state"],
        )


class InMemoryStateManager:
    def __init__(self, states: dict[str, dict]) -> None:
        self.states = deepcopy(states)
        self.saved_states: dict[str, dict] = {}

    def load_all_states(self) -> dict[str, dict]:
        return deepcopy(self.states)

    def save_state(self, state_key: str, payload: dict) -> None:
        self.saved_states[state_key] = deepcopy(payload)
        self.states[state_key] = deepcopy(payload)


class QuestionAskingAgent(BaseAgent):
    agent_name = "Requirements Engineer"
    stage_name = "REQUIREMENTS"
    state_key = "spec"

    def run(self, context):  # type: ignore[override]
        return AgentResult(
            agent_name=self.agent_name,
            stage_name=self.stage_name,
            state_key=self.state_key,
            updated_state=dict(context.states.get("spec", {})),
            summary="Need user clarification before proceeding.",
            question_state_update=QuestionState(
                status="awaiting_user",
                stage_name=self.stage_name,
                state_key=self.state_key,
                blocking=True,
                questions=[
                    QuestionItem(
                        id="target-user",
                        title="Who is the first target user?",
                        description="Need one concrete initial user persona.",
                    )
                ],
                created_by=self.agent_name,
            ),
            requires_user_input=True,
        )


class AnswerConsumingAgent(BaseAgent):
    agent_name = "Requirements Engineer"
    stage_name = "REQUIREMENTS"
    state_key = "spec"

    def run(self, context):  # type: ignore[override]
        updated_state = dict(context.states.get("spec", {}))
        updated_state["target_users"] = ["indie_hacker"]
        updated_state["open_questions"] = []
        return AgentResult(
            agent_name=self.agent_name,
            stage_name=self.stage_name,
            state_key=self.state_key,
            updated_state=updated_state,
            summary="Consumed answered question and updated spec.",
        )


class ReaskingAgent(BaseAgent):
    agent_name = "Requirements Engineer"
    stage_name = "REQUIREMENTS"
    state_key = "spec"

    def run(self, context):  # type: ignore[override]
        return AgentResult(
            agent_name=self.agent_name,
            stage_name=self.stage_name,
            state_key=self.state_key,
            updated_state=dict(context.states.get("spec", {})),
            summary="Need one more clarification round.",
            question_state_update=QuestionState(
                status="awaiting_user",
                stage_name=self.stage_name,
                state_key=self.state_key,
                blocking=True,
                questions=[
                    QuestionItem(
                        id="target-user-followup",
                        title="What is the user's biggest pain point?",
                        description="Need a sharper first-use-case boundary.",
                    )
                ],
                created_by=self.agent_name,
            ),
            requires_user_input=True,
        )


class StateManagerResilienceTests(unittest.TestCase):
    def test_load_state_returns_defaults_when_file_is_missing(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manager = StateManager(state_dir=temp_dir)
            self.assertEqual(
                manager.load_state("solution"),
                StateManager.DEFAULT_STATES["solution"],
            )

    def test_load_state_returns_defaults_when_json_is_invalid(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manager = StateManager(state_dir=temp_dir)
            path = manager.get_state_path("spec")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{broken json", encoding="utf-8")

            self.assertEqual(
                manager.load_state("spec"),
                StateManager.DEFAULT_STATES["spec"],
            )

    def test_load_state_merges_partial_payload_with_defaults(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manager = StateManager(state_dir=temp_dir)
            path = manager.get_state_path("solution")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                '{\n'
                '  "selected_stack": {\n'
                '    "backend": "Python"\n'
                "  }\n"
                "}\n",
                encoding="utf-8",
            )

            state = manager.load_state("solution")

            self.assertEqual(state["selected_stack"]["backend"], "Python")
            self.assertEqual(state["selected_stack"]["frontend"], "")
            self.assertEqual(state["module_mapping"], [])

    def test_load_state_returns_defaults_when_payload_is_not_an_object(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manager = StateManager(state_dir=temp_dir)
            path = manager.get_state_path("test_report")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('["not", "an", "object"]\n', encoding="utf-8")

            self.assertEqual(
                manager.load_state("test_report"),
                StateManager.DEFAULT_STATES["test_report"],
            )

    def test_load_all_states_tolerates_single_broken_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manager = StateManager(state_dir=temp_dir)
            spec_path = manager.get_state_path("spec")
            spec_path.parent.mkdir(parents=True, exist_ok=True)
            spec_path.write_text("{broken json", encoding="utf-8")

            solution_path = manager.get_state_path("solution")
            solution_path.write_text(
                '{\n'
                '  "selected_stack": {\n'
                '    "backend": "Python"\n'
                "  },\n"
                '  "module_mapping": []\n'
                "}\n",
                encoding="utf-8",
            )

            states = manager.load_all_states()

            self.assertEqual(states["spec"], StateManager.DEFAULT_STATES["spec"])
            self.assertEqual(states["solution"]["selected_stack"]["backend"], "Python")
            self.assertEqual(states["question_state"]["status"], "idle")

    def test_save_state_creates_parent_directory(self) -> None:
        with TemporaryDirectory() as temp_dir:
            state_dir = Path(temp_dir) / "nested" / "state"
            manager = StateManager(state_dir=state_dir)

            manager.save_state("spec", {"project_goal": "Ship"})

            self.assertTrue(manager.get_state_path("spec").exists())
            saved = json.loads(
                manager.get_state_path("spec").read_text(encoding="utf-8")
            )
            self.assertEqual(saved["project_goal"], "Ship")

    def test_save_state_rejects_non_dict_payload(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manager = StateManager(state_dir=temp_dir)

            with self.assertRaises(TypeError):
                manager.save_state("spec", ["not", "a", "dict"])  # type: ignore[arg-type]


class RequirementsEngineerAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = RequirementsEngineerAgent()

    def test_agent_extracts_core_spec_fields_from_user_input(self) -> None:
        context = AgentContext(
            user_input=(
                "Build a chat-first engineering workflow that collects requirements "
                "and generates solution artifacts."
            ),
            states=make_empty_states(),
        )

        result = self.agent.run(context)

        self.assertEqual(
            result.updated_state["project_goal"],
            "A chat-first engineering workflow that collects requirements and generates solution artifacts",
        )
        self.assertTrue(result.updated_state["functional_requirements"])
        self.assertTrue(result.updated_state["acceptance_criteria"])
        self.assertFalse(result.requires_user_input)
        self.assertTrue(result.handoff_ready)

    def test_agent_asks_blocking_questions_when_core_inputs_are_missing(self) -> None:
        context = AgentContext(user_input="", states=make_empty_states())

        result = self.agent.run(context)

        self.assertTrue(result.requires_user_input)
        self.assertIsNotNone(result.question_state_update)
        self.assertEqual(result.question_state_update.status, "awaiting_user")
        self.assertEqual(
            [question.id for question in result.question_state_update.questions],
            ["project_goal", "functional_requirements", "acceptance_criteria"],
        )
        self.assertEqual(
            result.updated_state["open_questions"],
            ["project_goal", "functional_requirements", "acceptance_criteria"],
        )

    def test_agent_consumes_answered_question_state(self) -> None:
        states = make_empty_states()
        context = AgentContext(
            user_input="",
            states=states,
            question_state=QuestionState(
                status="answered",
                stage_name="REQUIREMENTS",
                state_key="spec",
                blocking=True,
                questions=[
                    QuestionItem(
                        id="project_goal",
                        title="What are we building?",
                        description="Describe the primary goal.",
                        response_type="free_text",
                        allow_free_text=True,
                        answer=QuestionAnswer(
                            selected_values=[],
                            free_text="A workflow assistant for solo builders",
                        ),
                    ),
                    QuestionItem(
                        id="functional_requirements",
                        title="What must it do?",
                        description="List core capabilities.",
                        response_type="free_text",
                        allow_free_text=True,
                        answer=QuestionAnswer(
                            selected_values=[],
                            free_text=(
                                "Collect requirements; produce a solution outline; "
                                "track implementation progress"
                            ),
                        ),
                    ),
                    QuestionItem(
                        id="acceptance_criteria",
                        title="How will we know it works?",
                        description="Describe the acceptance signal.",
                        response_type="free_text",
                        allow_free_text=True,
                        answer=QuestionAnswer(
                            selected_values=[],
                            free_text=(
                                "The user can capture a request and receive a structured spec"
                            ),
                        ),
                    ),
                ],
                created_by="Requirements Engineer",
            ),
        )

        result = self.agent.run(context)

        self.assertEqual(
            result.updated_state["project_goal"],
            "A workflow assistant for solo builders",
        )
        self.assertIn(
            "Collect requirements",
            result.updated_state["functional_requirements"],
        )
        self.assertEqual(
            result.updated_state["acceptance_criteria"],
            ["The user can capture a request and receive a structured spec"],
        )
        self.assertFalse(result.requires_user_input)
        self.assertIsNone(result.question_state_update)


if __name__ == "__main__":
    unittest.main()
