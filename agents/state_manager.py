from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StateManager:
    STATE_FILES = {
        "spec": "spec.json",
        "solution": "solution.json",
        "system_design": "system_design.json",
        "implementation_status": "implementation_status.json",
        "test_report": "test_report.json",
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

    def load_state(self, state_key: str) -> dict[str, Any]:
        path = self.get_state_path(state_key)
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def save_state(self, state_key: str, payload: dict[str, Any]) -> None:
        path = self.get_state_path(state_key)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    def load_all_states(self) -> dict[str, dict[str, Any]]:
        return {
            state_key: self.load_state(state_key)
            for state_key in self.STATE_FILES
        }
