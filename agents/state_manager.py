from __future__ import annotations

import json
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any


class StateManager:
    STATE_FILES = {
        "spec": "spec.json",
        "solution": "solution.json",
        "system_design": "system_design.json",
        "implementation_status": "implementation_status.json",
        "test_report": "test_report.json",
        "question_state": "question_state.json",
    }
    DEFAULT_STATES = {
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

    def __init__(self, state_dir: str | Path | None = None) -> None:
        if state_dir is None:
            state_dir = Path(__file__).resolve().parent.parent / "state"
        self.state_dir = Path(state_dir)

    def get_state_path(self, state_key: str) -> Path:
        try:
            filename = self.STATE_FILES[state_key]
        except KeyError as exc:
            raise KeyError(f"Unknown state key: {state_key}") from exc
        return self.state_dir / filename

    def get_default_state(self, state_key: str) -> dict[str, Any]:
        try:
            return deepcopy(self.DEFAULT_STATES[state_key])
        except KeyError as exc:
            raise KeyError(f"Unknown state key: {state_key}") from exc

    def merge_with_defaults(
        self, default: dict[str, Any], payload: dict[str, Any]
    ) -> dict[str, Any]:
        merged = deepcopy(default)
        for key, value in payload.items():
            default_value = merged.get(key)
            if isinstance(default_value, dict) and isinstance(value, dict):
                merged[key] = self.merge_with_defaults(default_value, value)
            else:
                merged[key] = value
        return merged

    def load_state(self, state_key: str) -> dict[str, Any]:
        path = self.get_state_path(state_key)
        default_state = self.get_default_state(state_key)
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except FileNotFoundError:
            return default_state
        except json.JSONDecodeError:
            return default_state

        if not isinstance(payload, dict):
            return default_state
        return self.merge_with_defaults(default_state, payload)

    def save_state(self, state_key: str, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            raise TypeError("State payload must be a dictionary.")
        path = self.get_state_path(state_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f"{path.stem}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            temp_path = Path(handle.name)
        temp_path.replace(path)

    def load_all_states(self) -> dict[str, dict[str, Any]]:
        return {
            state_key: self.load_state(state_key)
            for state_key in self.STATE_FILES
        }
