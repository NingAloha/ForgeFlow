from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass

from tui.app import ForgeShellApp
from tui.commands import ALLOWED_COMMANDS, parse_command


class TUICommandTests(unittest.TestCase):
    def test_allowed_commands_do_not_include_control_surface_operations(self) -> None:
        self.assertNotIn("/rollback", ALLOWED_COMMANDS)
        self.assertNotIn("/retry", ALLOWED_COMMANDS)
        self.assertNotIn("/switch", ALLOWED_COMMANDS)
        self.assertNotIn("/lock", ALLOWED_COMMANDS)
        self.assertNotIn("/execute", ALLOWED_COMMANDS)
        self.assertNotIn("/apply", ALLOWED_COMMANDS)

    def test_parse_open_commands(self) -> None:
        parsed = parse_command("/open spec")
        self.assertEqual(parsed.command, "/open")
        self.assertEqual(parsed.argument, "spec")


class TUIAppFlowTests(unittest.TestCase):
    @dataclass
    class _Decision:
        final_stage: str = "IMPLEMENTATION"
        wait_for_user_input: bool = False

    @dataclass
    class _Result:
        decision: "TUIAppFlowTests._Decision"
        summary: str
        diagnostic: dict

    class _OrchestratorStub:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []

        def orchestrate(
            self, prompt: str, original_request: str = ""
        ) -> "TUIAppFlowTests._Result":
            self.calls.append(("orchestrate", prompt))
            return TUIAppFlowTests._Result(
                decision=TUIAppFlowTests._Decision(),
                summary="stub run complete",
                diagnostic={"decision_type": "FORWARD"},
            )

        def get_status_snapshot(self) -> dict:
            self.calls.append(("get_status_snapshot", ""))
            return {
                "question_state": {"status": "idle"},
                "implementation_status": {
                    "implementation_status": "blocked",
                    "notes": "BEGIN_EXECUTION_CONTRACT\n...\nEND_EXECUTION_CONTRACT",
                    "approval_artifact": {"approval_status": "pending"},
                    "apply_plan": {"apply_plan_status": "blocked"},
                },
            }

        def get_artifact_for_display(self, name: str) -> dict:
            self.calls.append(("get_artifact_for_display", name))
            if name == "spec":
                return {"project_goal": "demo"}
            if name == "solution":
                return {"selected_stack": {}}
            if name == "system_design":
                return {"project_structure": {}}
            return {}

    def test_tui_wraps_orchestrator_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = ForgeShellApp(state_dir=tmp_dir)
            self.assertTrue(app.handle_line("build a todo app"))
            self.assertTrue(app.handle_line("/run"))
            self.assertTrue(app.handle_line("/status"))
            self.assertTrue(app.handle_line("/open spec"))
            self.assertFalse(app.handle_line("/quit"))

    def test_tui_uses_orchestrator_read_only_api_for_status_and_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = ForgeShellApp(state_dir=tmp_dir)
            stub = self._OrchestratorStub()
            app.orchestrator = stub

            self.assertFalse(hasattr(app, "state_manager"))
            self.assertTrue(app.handle_line("/status"))
            self.assertTrue(app.handle_line("/open spec"))
            self.assertTrue(app.handle_line("/open solution"))
            self.assertTrue(app.handle_line("/open design"))

            self.assertIn(("get_status_snapshot", ""), stub.calls)
            self.assertIn(("get_artifact_for_display", "spec"), stub.calls)
            self.assertIn(("get_artifact_for_display", "solution"), stub.calls)
            self.assertIn(("get_artifact_for_display", "system_design"), stub.calls)
            self.assertNotIn(("orchestrate", ""), stub.calls)

    def test_tui_run_invokes_orchestrator_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = ForgeShellApp(state_dir=tmp_dir)
            stub = self._OrchestratorStub()
            app.orchestrator = stub

            self.assertTrue(app.handle_line("summarize markdown"))
            self.assertTrue(app.handle_line("/run"))
            self.assertIn(("orchestrate", "summarize markdown"), stub.calls)

    def test_status_displays_execution_governance_presence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = ForgeShellApp(state_dir=tmp_dir)
            stub = self._OrchestratorStub()
            app.orchestrator = stub

            self.assertTrue(app.handle_line("/status"))
            status_events = [event for event in app.events.tail(20) if event.kind == "status"]
            self.assertTrue(status_events)
            status_message = status_events[-1].message
            self.assertIn("implementation_mode=execute", status_message)
            self.assertIn("approval_artifact=yes", status_message)
            self.assertIn("apply_plan=yes", status_message)
            self.assertIn("mutation_enabled=no", status_message)

    def test_unsupported_control_commands_stay_unsupported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = ForgeShellApp(state_dir=tmp_dir)
            self.assertTrue(app.handle_line("/rollback"))
            self.assertTrue(app.handle_line("/retry"))
            self.assertTrue(app.handle_line("/switch"))
            self.assertTrue(app.handle_line("/lock"))
            self.assertTrue(app.handle_line("/execute"))
            self.assertTrue(app.handle_line("/apply"))
