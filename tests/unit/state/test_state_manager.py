from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from agents.state_manager import StateManager


class StateManagerResilienceTests(unittest.TestCase):
    def test_default_state_dir_points_to_runtime_workspace(self) -> None:
        manager = StateManager()
        self.assertEqual(
            manager.state_dir,
            Path(__file__).resolve().parent.parent.parent.parent
            / ".forgeflow"
            / "state",
        )

    def test_load_state_returns_defaults_when_file_is_missing(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manager = StateManager(state_dir=temp_dir)
            self.assertEqual(
                manager.load_state("solution"), StateManager.DEFAULT_STATES["solution"]
            )

    def test_load_state_returns_defaults_when_json_is_invalid(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manager = StateManager(state_dir=temp_dir)
            path = manager.get_state_path("spec")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{broken json", encoding="utf-8")
            self.assertEqual(
                manager.load_state("spec"), StateManager.DEFAULT_STATES["spec"]
            )

    def test_load_state_merges_partial_payload_with_defaults(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manager = StateManager(state_dir=temp_dir)
            path = manager.get_state_path("solution")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                '{\n  "selected_stack": {\n    "backend": "Python"\n  }\n}\n',
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
                '{\n  "selected_stack": {\n    "backend": "Python"\n  },\n  "module_mapping": []\n}\n',
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

    def test_load_state_falls_back_to_defaults_when_schema_is_invalid(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manager = StateManager(state_dir=temp_dir)
            path = manager.get_state_path("spec")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"project_goal": 123}\n', encoding="utf-8")
            self.assertEqual(
                manager.load_state("spec"),
                StateManager.DEFAULT_STATES["spec"],
            )
            self.assertIn("spec", manager.validation_errors)

    def test_load_state_normalizes_missing_fields_via_schema_defaults(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manager = StateManager(state_dir=temp_dir)
            path = manager.get_state_path("question_state")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"status": "awaiting_user"}\n', encoding="utf-8")
            loaded = manager.load_state("question_state")
            self.assertEqual(loaded["status"], "awaiting_user")
            self.assertEqual(loaded["questions"], [])
            self.assertEqual(loaded["stage_name"], "")

    def test_save_state_rejects_schema_invalid_payload(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manager = StateManager(state_dir=temp_dir)
            with self.assertRaises(ValueError):
                manager.save_state("spec", {"project_goal": 123})  # type: ignore[arg-type]

    def test_load_all_states_resets_previous_validation_errors(self) -> None:
        with TemporaryDirectory() as temp_dir:
            manager = StateManager(state_dir=temp_dir)
            spec_path = manager.get_state_path("spec")
            spec_path.parent.mkdir(parents=True, exist_ok=True)
            spec_path.write_text('{"project_goal": 123}\n', encoding="utf-8")
            _ = manager.load_state("spec")
            self.assertIn("spec", manager.validation_errors)
            states = manager.load_all_states()
            self.assertEqual(states["spec"], StateManager.DEFAULT_STATES["spec"])
            self.assertIn("spec", manager.validation_errors)


if __name__ == "__main__":
    unittest.main()
