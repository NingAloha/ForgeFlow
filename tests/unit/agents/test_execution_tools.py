from __future__ import annotations

import tempfile
import unittest

from agents.common.execution_tools import WorkspaceExecutor


class ExecutionToolsTests(unittest.TestCase):
    def test_write_file_rejects_escape_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = WorkspaceExecutor(temp_dir)
            with self.assertRaises(ValueError):
                executor.write_file("../escape.txt", "x")

    def test_run_command_rejects_non_allowlisted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = WorkspaceExecutor(temp_dir)
            with self.assertRaises(PermissionError):
                executor.run_command(["bash", "-lc", "echo hi"])


if __name__ == "__main__":
    unittest.main()
