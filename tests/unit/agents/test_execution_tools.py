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

    def test_run_command_rejects_pytest_even_when_prefixed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = WorkspaceExecutor(temp_dir)
            with self.assertRaises(PermissionError):
                executor.run_command(["pytest", "-q"])

    def test_run_command_allows_fixed_unittest_discover_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = WorkspaceExecutor(temp_dir)
            tests_dir = executor.workspace_root / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            (tests_dir / "test_smoke.py").write_text(
                "import unittest\n\n"
                "class Smoke(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            result = executor.run_command(
                [
                    "python3",
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    "tests",
                    "-p",
                    "test_*.py",
                    "-v",
                ]
            )
            self.assertEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
