from __future__ import annotations

import tempfile
import unittest

from tui.app import ForgeShellApp
from tui.commands import ALLOWED_COMMANDS, parse_command


class TUICommandTests(unittest.TestCase):
    def test_allowed_commands_do_not_include_control_surface_operations(self) -> None:
        self.assertNotIn("/rollback", ALLOWED_COMMANDS)
        self.assertNotIn("/retry", ALLOWED_COMMANDS)
        self.assertNotIn("/switch", ALLOWED_COMMANDS)
        self.assertNotIn("/lock", ALLOWED_COMMANDS)

    def test_parse_open_commands(self) -> None:
        parsed = parse_command("/open spec")
        self.assertEqual(parsed.command, "/open")
        self.assertEqual(parsed.argument, "spec")


class TUIAppFlowTests(unittest.TestCase):
    def test_tui_wraps_orchestrator_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = ForgeShellApp(state_dir=tmp_dir)
            self.assertTrue(app.handle_line("build a todo app"))
            self.assertTrue(app.handle_line("/run"))
            self.assertTrue(app.handle_line("/status"))
            self.assertTrue(app.handle_line("/open spec"))
            self.assertFalse(app.handle_line("/quit"))
