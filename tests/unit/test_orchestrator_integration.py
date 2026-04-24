from __future__ import annotations

import unittest
from copy import deepcopy

from agents.base import QuestionAnswer, QuestionItem, QuestionOption, QuestionState
from agents.orchestrator import Orchestrator, Stage
from tests.unit.support.orchestrator_fixtures import (
    make_design_ready_states,
    make_done_states,
    make_empty_states,
    make_implementing_states,
    make_requirements_ready_states,
    make_solution_ready_states,
    make_testing_states,
)
from tests.unit.support.orchestrator_stubs import (
    AnswerConsumingAgent,
    InMemoryStateManager,
    QuestionAskingAgent,
    ReaskingAgent,
)


class OrchestratorStageComputationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orchestrator = Orchestrator()

    def test_empty_states_resolve_to_init(self) -> None:
        states = make_empty_states()
        self.assertEqual(self.orchestrator.compute_current_stage(states), Stage.INIT)

    def test_requirements_ready_states_resolve_to_requirements_ready(self) -> None:
        states = make_requirements_ready_states()
        self.assertTrue(self.orchestrator.is_requirements_ready(states))
        self.assertEqual(self.orchestrator.compute_current_stage(states), Stage.REQUIREMENTS)

    def test_solution_ready_states_resolve_to_solution_ready(self) -> None:
        states = make_solution_ready_states()
        self.assertTrue(self.orchestrator.is_solution_ready(states))
        self.assertEqual(self.orchestrator.compute_current_stage(states), Stage.SOLUTION)

    def test_design_ready_states_resolve_to_design_ready(self) -> None:
        states = make_design_ready_states()
        self.assertTrue(self.orchestrator.is_design_ready(states))
        self.assertEqual(self.orchestrator.compute_current_stage(states), Stage.DESIGN)

    def test_implementing_states_resolve_to_implementing(self) -> None:
        states = make_implementing_states()
        self.assertTrue(self.orchestrator.has_active_implementation(states))
        self.assertEqual(self.orchestrator.compute_current_stage(states), Stage.IMPLEMENTATION)

    def test_testing_states_resolve_to_testing(self) -> None:
        states = make_testing_states()
        self.assertTrue(self.orchestrator.has_validation_context(states))
        self.assertEqual(self.orchestrator.compute_current_stage(states), Stage.TESTING)

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
        self.assertEqual(self.orchestrator.compute_current_stage(states), Stage.TESTING)

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
        self.assertEqual(self.orchestrator.compute_current_stage(states), Stage.IMPLEMENTATION)

    def test_missing_valid_contract_reference_prevents_design_ready(self) -> None:
        states = make_design_ready_states()
        broken_states = deepcopy(states)
        broken_states["system_design"]["data_flow"][0]["contract_name"] = "missing"
        self.assertFalse(self.orchestrator.is_design_ready(broken_states))
        self.assertEqual(self.orchestrator.compute_current_stage(broken_states), Stage.SOLUTION)

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
                    "answer": {"selected_values": ["mvp"], "free_text": ""},
                }
            ],
            "created_by": "Requirements Engineer",
            "resolution_summary": "",
        }
        decision = self.orchestrator.resolve_transition(states)
        self.assertFalse(decision.wait_for_user_input)
        self.assertTrue(decision.should_stay)
        self.assertEqual(decision.final_stage, Stage.REQUIREMENTS)
        self.assertEqual(self.orchestrator.determine_execution_stage(decision), Stage.REQUIREMENTS)

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
        self.assertEqual(question_state.questions[0].answer.selected_values, ["python"])
        self.assertEqual(question_state.questions[0].answer.free_text, "Prefer standard library first.")

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
        self.assertEqual(payload["questions"][0]["answer"]["selected_values"], ["python"])
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
                    "answer": {"selected_values": ["indie_hacker"], "free_text": "Solo builder first."},
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
        self.assertEqual(state_manager.saved_states["question_state"], make_empty_states()["question_state"])

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
                    "answer": {"selected_values": ["python"], "free_text": ""},
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
                    "answer": {"selected_values": [], "free_text": "Need more constraints."},
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
        self.assertEqual(state_manager.saved_states["question_state"]["status"], "awaiting_user")

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

    def test_resolve_transition_keeps_partial_testing_without_issue_attribution(self) -> None:
        states = make_testing_states()
        states["test_report"].update({"result": "partial", "issues": []})
        decision = self.orchestrator.resolve_transition(states)
        self.assertEqual(decision.computed_stage, Stage.TESTING)
        self.assertEqual(decision.final_stage, Stage.TESTING)
        self.assertIsNone(decision.backflow_target)
        self.assertTrue(decision.should_stay)

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

    def test_resolve_transition_keeps_blocked_implementation_without_blocker_details(self) -> None:
        states = make_design_ready_states()
        states["implementation_status"].update(
            {
                "module_name": "orchestrator",
                "implementation_status": "blocked",
                "blockers": [],
            }
        )
        decision = self.orchestrator.resolve_transition(states)
        self.assertEqual(decision.computed_stage, Stage.IMPLEMENTATION)
        self.assertEqual(decision.final_stage, Stage.IMPLEMENTATION)
        self.assertIsNone(decision.backflow_target)
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

    def test_resolve_transition_backflows_testing_to_requirements_when_open_questions_exist(self) -> None:
        states = make_testing_states()
        states["spec"]["open_questions"] = ["Need clearer acceptance scope."]
        states["test_report"].update(
            {
                "result": "fail",
                "issues": [
                    {
                        "title": "Validation blocked",
                        "severity": "critical",
                        "status": "confirmed",
                        "related_modules": ["orchestrator"],
                        "related_contracts": [],
                        "notes": "Acceptance criteria remain unclear.",
                    }
                ],
            }
        )
        decision = self.orchestrator.resolve_transition(states)
        self.assertEqual(decision.computed_stage, Stage.TESTING)
        self.assertEqual(decision.final_stage, Stage.REQUIREMENTS)
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
                    "answer": {"selected_values": ["indie_hacker"], "free_text": "Solo builder first."},
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
        self.assertEqual(state_manager.states["question_state"], make_empty_states()["question_state"])


if __name__ == "__main__":
    unittest.main()
