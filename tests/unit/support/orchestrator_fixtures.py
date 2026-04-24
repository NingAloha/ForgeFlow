from __future__ import annotations


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
